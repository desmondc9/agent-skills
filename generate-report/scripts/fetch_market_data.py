# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "yfinance>=0.2.40",
#     "akshare>=1.12",
#     "mplfinance>=0.12.10b0",
#     "pandas>=2.0",
#     "matplotlib>=3.7",
# ]
# ///
"""批量采集研究报告所需的行情、指标与财报数据，并生成周 K 线图与可直接粘贴的指标表。

服务于 `templates/two-country-scoring-investment-map.md` 体裁（公司卡片需要
「近 1.5 年周 K 线图 + 股票指标表 + 近期财报表」三件套）。

数据源：
    - 首选 yfinance（美股、港股 .HK、A 股 .SS/.SZ 均可）
    - 行情缺失时回退 akshare（A 股 stock_zh_a_hist / 港股 stock_hk_hist）
    - 财报缺失（常见于港股小盘股）时输出 N/A，需人工用付费终端（iFinD 等）补齐并在表注写明口径

用法：
    uv run --script fetch_market_data.py \
        --tickers MSFT CRM NOW 0700.HK 002230.SZ \
        --output-dir reports/2026-09-01-ai-us-cn \
        --weeks 78

产出（写入 --output-dir）：
    findata/{ticker}_weekly.csv      周线 OHLCV
    findata/{ticker}_info.csv        指标原始值
    findata/{ticker}_quarterly.csv   最近几期财报原始值
    charts/{ticker}_weekly.png       周 K 线图（图内文字为 ASCII，避免缺字形方块）
    company_metrics.md               每家公司两张 Markdown 表，正文直接引用
    并向 stdout 打印 JSON 摘要（成功/失败清单）。

注意：网络受限时先设置代理环境变量（http_proxy/https_proxy）再运行。
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import mplfinance as mpf


def detect_market(ticker: str) -> str:
    t = ticker.upper()
    if t.endswith(".HK"):
        return "HK"
    if t.endswith((".SS", ".SZ", ".SH")):
        return "A"
    return "US"


def fetch_yf(ticker: str, weeks: int):
    """返回 (weekly_df, info_dict, quarterly_df)；任一项失败则为 None。"""
    import yfinance as yf

    tk = yf.Ticker(ticker)
    start = (datetime.now() - timedelta(weeks=weeks + 2)).strftime("%Y-%m-%d")
    weekly = tk.history(start=start, interval="1wk", auto_adjust=False)
    if weekly is not None and not weekly.empty:
        weekly = weekly.rename(columns=str.title)[["Open", "High", "Low", "Close", "Volume"]]
        weekly = weekly.dropna().tail(weeks)
    else:
        weekly = None

    try:
        info = dict(tk.info or {})
    except Exception:
        info = {}

    try:
        q = tk.quarterly_income_stmt
        quarterly = q if q is not None and not q.empty else None
    except Exception:
        quarterly = None

    return weekly, info, quarterly


def fetch_ak_weekly(ticker: str, market: str, weeks: int):
    """akshare 回退：仅取周线行情。"""
    import akshare as ak

    start = (datetime.now() - timedelta(weeks=weeks + 2)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    code = ticker.upper().split(".")[0]
    if market == "A":
        df = ak.stock_zh_a_hist(symbol=code, period="weekly", start_date=start, end_date=end, adjust="qfq")
    elif market == "HK":
        df = ak.stock_hk_hist(symbol=code.zfill(5), period="weekly", start_date=start, end_date=end, adjust="qfq")
    else:
        return None
    if df is None or df.empty:
        return None
    df = df.rename(columns={"日期": "Date", "开盘": "Open", "最高": "High", "最低": "Low", "收盘": "Close", "成交量": "Volume"})
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]].dropna().tail(weeks)
    return df


def build_style(color_scheme: str):
    """cn = 红涨绿跌（A 股/港股读者习惯）；western = 绿涨红跌。"""
    if color_scheme == "cn":
        mc = mpf.make_marketcolors(up="red", down="green", edge="inherit", wick="inherit", volume="in")
        return mpf.make_mpf_style(base_mpf_style="yahoo", marketcolors=mc)
    return "yahoo"


def render_chart(weekly: pd.DataFrame, ticker: str, path: Path, color_scheme: str) -> None:
    """图内只用 ASCII，避免中文字体缺失导致方块。"""
    mpf.plot(
        weekly,
        type="candle",
        style=build_style(color_scheme),
        title=f"{ticker} weekly ({len(weekly)}w)",
        ylabel="Price",
        volume=True,
        mav=(13, 26),
        figratio=(16, 9),
        figscale=1.2,
        savefig=dict(fname=str(path), dpi=150, bbox_inches="tight"),
    )


def fmt_num(v, unit: str = "", digits: int = 2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    try:
        return f"{float(v):,.{digits}f}{unit}"
    except (TypeError, ValueError):
        return str(v)


def fmt_pct(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "N/A"
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "N/A"


RECOMMENDATION_CN = {
    "strong_buy": "强烈买入", "buy": "买入", "outperform": "跑赢大盘",
    "hold": "持有", "underperform": "跑输大盘", "sell": "卖出", "none": "N/A",
}


def fmt_cap(v, currency: str):
    if not v:
        return "N/A"
    try:
        return f"{float(v) / 1e8:,.0f} 亿{currency}"
    except (TypeError, ValueError):
        return "N/A"


def metrics_table(info: dict, currency: str) -> str:
    rows = [
        ("最新价", fmt_num(info.get("currentPrice") or info.get("regularMarketPrice"), f" {currency}"),
         "市值", fmt_cap(info.get("marketCap"), currency)),
        ("TTM P/E", fmt_num(info.get("trailingPE")), "Forward P/E", fmt_num(info.get("forwardPE"))),
        ("P/S (TTM)", fmt_num(info.get("priceToSalesTrailing12Months")), "毛利率", fmt_pct(info.get("grossMargins"))),
        ("营收增速（TTM）", fmt_pct(info.get("revenueGrowth")), "净利润率", fmt_pct(info.get("profitMargins"))),
        ("分析师评级", RECOMMENDATION_CN.get(info.get("recommendationKey"), info.get("recommendationKey") or "N/A"),
         "目标价均值", fmt_num(info.get("targetMeanPrice"), f" {currency}")),
    ]
    out = ["| 指标 | 数值 | 指标 | 数值 |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    return "\n".join(out)


def earnings_table(quarterly: pd.DataFrame | None, currency: str, periods: int = 2) -> str:
    """港股/A 股常见「季度列大量为空」（半年报口径），故先剔除空列再取最近 N 期。"""
    header = ["| 报告期 | 营收 | 营收同比 | 净利润 | 净利润同比 |", "|---|---|---|---|---|"]
    missing_note = "\n\n> 财报缺失：需用付费终端（iFinD 等）补齐，并在表注写明口径。"
    if quarterly is None or quarterly.empty:
        return "\n".join(header + ["| N/A | N/A | N/A | N/A | N/A |"]) + missing_note

    def pick(names: list[str]):
        for name in names:
            if name in quarterly.index:
                return quarterly.loc[name]
        return None

    rev = pick(["Total Revenue", "Operating Revenue"])
    net = pick(["Net Income", "Net Income Common Stockholders", "Net Income Including Noncontrolling Interests"])

    def has_value(series, col):
        return series is not None and col in series.index and pd.notna(series[col])

    cols = [c for c in quarterly.columns if has_value(rev, c) or has_value(net, c)]
    cols = sorted(cols, key=lambda c: pd.Timestamp(c), reverse=True)
    if not cols:
        return "\n".join(header + ["| N/A | N/A | N/A | N/A | N/A |"]) + missing_note

    def yoy(series, col):
        """同比：在所有列里找与 col 相隔约 365 天（±60 天）且有值的那一期。"""
        if series is None:
            return "N/A"
        target = pd.Timestamp(col) - pd.Timedelta(days=365)
        candidates = [c for c in quarterly.columns
                      if has_value(series, c) and abs((pd.Timestamp(c) - target).days) <= 60]
        if not candidates or not has_value(series, col):
            return "N/A"
        prev_col = min(candidates, key=lambda c: abs((pd.Timestamp(c) - target).days))
        cur, prev = float(series[col]), float(series[prev_col])
        if prev == 0:
            return "N/A"
        return f"{(cur / prev - 1) * 100:+.1f}%"

    lines = []
    for col in cols[:periods]:
        def amount(series):
            if not has_value(series, col):
                return "N/A"
            return f"{float(series[col]) / 1e8:,.1f} 亿{currency}"

        period = pd.Timestamp(col).strftime("%Y-%m-%d")
        lines.append(f"| {period} | {amount(rev)} | {yoy(rev, col)} | {amount(net)} | {yoy(net, col)} |")
    return "\n".join(header + lines)


def process(ticker: str, weeks: int, findata: Path, charts: Path, color_scheme: str) -> dict:
    market = detect_market(ticker)
    weekly, info, quarterly = fetch_yf(ticker, weeks)
    source = "yfinance"
    if weekly is None:
        weekly = fetch_ak_weekly(ticker, market, weeks)
        source = "akshare" if weekly is not None else "none"
    if weekly is None:
        raise RuntimeError("周线行情为空（yfinance 与 akshare 均失败）")

    currency = (info.get("currency") or {"US": "USD", "HK": "HKD", "A": "CNY"}[market]).upper()
    currency_cn = {"USD": "美元", "HKD": "港元", "CNY": "元", "RMB": "元"}.get(currency, currency)

    weekly.to_csv(findata / f"{ticker}_weekly.csv")
    if info:
        pd.Series(info).to_csv(findata / f"{ticker}_info.csv")
    if quarterly is not None:
        quarterly.to_csv(findata / f"{ticker}_quarterly.csv")

    chart_path = charts / f"{ticker}_weekly.png"
    render_chart(weekly, ticker, chart_path, color_scheme)

    last = weekly.iloc[-1]
    first = weekly.iloc[0]
    return {
        "ticker": ticker,
        "market": market,
        "price_source": source,
        "currency": currency,
        "weeks": len(weekly),
        "period": f"{weekly.index[0].date()} ~ {weekly.index[-1].date()}",
        "close": round(float(last["Close"]), 2),
        "period_change_pct": round((float(last["Close"]) / float(first["Close"]) - 1) * 100, 1),
        "chart": str(chart_path),
        "name": info.get("longName") or info.get("shortName") or ticker,
        "metrics_md": metrics_table(info, currency_cn),
        "earnings_md": earnings_table(quarterly, currency_cn),
        "has_info": bool(info),
        "has_quarterly": quarterly is not None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="批量采集周 K 线 + 指标 + 财报，产出报告可直接引用的表格")
    ap.add_argument("--tickers", nargs="+", help="标的代码，如 MSFT 0700.HK 002230.SZ")
    ap.add_argument("--tickers-file", help="每行一个代码的文本文件（与 --tickers 二选一）")
    ap.add_argument("--output-dir", required=True, help="报告工作区目录（findata/ 与 charts/ 会建在其下）")
    ap.add_argument("--weeks", type=int, default=78, help="周线根数，默认 78（约 1.5 年）")
    ap.add_argument("--color-scheme", choices=["cn", "western"], default="cn",
                    help="K 线配色：cn 红涨绿跌（默认，中文读者习惯）/ western 绿涨红跌")
    args = ap.parse_args()

    tickers = list(args.tickers or [])
    if args.tickers_file:
        tickers += [l.strip() for l in Path(args.tickers_file).read_text().splitlines() if l.strip()]
    if not tickers:
        ap.error("必须提供 --tickers 或 --tickers-file")

    out = Path(args.output_dir).expanduser().resolve()
    findata, charts = out / "findata", out / "charts"
    findata.mkdir(parents=True, exist_ok=True)
    charts.mkdir(parents=True, exist_ok=True)

    ok, failed = [], []
    for t in tickers:
        try:
            ok.append(process(t, args.weeks, findata, charts, args.color_scheme))
            print(f"[ok] {t}", file=sys.stderr)
        except Exception as exc:
            failed.append({"ticker": t, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[fail] {t}: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    today = datetime.now().strftime("%Y-%m-%d")
    md = [f"# 上市公司金融数据汇总\n", f"数据源：yfinance / akshare；采集日 {today}；周线约 {args.weeks} 根（≈1.5 年）。",
          "港股小盘股与部分 A 股的季度财报可能缺失，需用付费终端补齐并在表注写明口径。\n"]
    for r in ok:
        md += [
            f"\n## {r['name']}（{r['ticker']}）\n",
            f"![{r['ticker']} 近1.5年周K线](charts/{r['ticker']}_weekly.png)\n",
            r["metrics_md"], "",
            "**最近报告期财务数据：**\n",
            r["earnings_md"], "",
            f"数据来源：{r['price_source']}，行情区间 {r['period']}，区间涨跌 {r['period_change_pct']:+.1f}%，采集日 {today}。",
        ]
    if failed:
        md += ["\n## 采集失败清单\n", "| 标的 | 错误 |", "|---|---|"] + [f"| {f['ticker']} | {f['error']} |" for f in failed]
    (out / "company_metrics.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps({
        "output_dir": str(out),
        "metrics_file": str(out / "company_metrics.md"),
        "succeeded": [{k: v for k, v in r.items() if not k.endswith("_md")} for r in ok],
        "failed": failed,
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
