# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "akshare>=1.12",
#     "yfinance>=0.2.40",
#     "mplfinance>=0.12.10b0",
#     "pandas>=2.0",
#     "matplotlib>=3.7",
# ]
# ///
"""Fetch accurate stock price and generate 3-year K-line PNG charts.

Primary data source: akshare (best for A-share / HK / some US).
Fallback: yfinance (reliable for US, HK).

Usage:
    uv run --script fetch_stock_data.py \
        --ticker AAPL --market US \
        --output-dir /abs/path/to/BASE_DIR/01_basic_data

Outputs (written to --output-dir):
    - assets/{TICKER}_3year_daily.png
    - assets/{TICKER}_3year_weekly.png
    - Prints JSON summary to stdout.
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


MARKET_CURRENCY = {"US": "USD", "HK": "HKD", "A": "CNY"}


def normalize_market(market: str) -> str:
    m = market.upper().strip()
    if m in ("US", "NYSE", "NASDAQ", "USA"):
        return "US"
    if m in ("HK", "HKEX"):
        return "HK"
    if m in ("A", "SSE", "SZSE", "SS", "SZ", "CN"):
        return "A"
    raise ValueError(f"Unknown market: {market!r}. Use US | HK | A.")


def clean_ticker(ticker: str, market: str) -> str:
    t = ticker.upper().strip()
    if market == "HK":
        t = t.replace(".HK", "").lstrip("0")
        return t.zfill(5)
    if market == "A":
        return t.replace(".SS", "").replace(".SZ", "")
    return t


def fetch_with_akshare(ticker: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    import akshare as ak

    cleaned = clean_ticker(ticker, market)

    if market == "US":
        df = ak.stock_us_daily(symbol=cleaned, adjust="")
        date_col = "date"
        rename = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    elif market == "HK":
        df = ak.stock_hk_daily(symbol=cleaned, adjust="")
        date_col = "date"
        rename = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
    else:  # A
        df = ak.stock_zh_a_hist(
            symbol=cleaned,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )
        date_col = "日期"
        rename = {"开盘": "Open", "最高": "High", "最低": "Low", "收盘": "Close", "成交量": "Volume"}

    if df is None or df.empty:
        raise RuntimeError("akshare returned empty dataframe")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    df = df.rename(columns=rename)
    df = df.loc[(df.index >= start_date) & (df.index <= end_date), ["Open", "High", "Low", "Close", "Volume"]]
    return df.astype(float)


def fetch_with_yfinance(ticker: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    import yfinance as yf

    yf_ticker = ticker.upper().strip()
    if market == "HK":
        base = yf_ticker.replace(".HK", "").lstrip("0")
        yf_ticker = f"{base.zfill(4)}.HK"
    elif market == "A":
        base = yf_ticker.replace(".SS", "").replace(".SZ", "")
        if base.startswith(("6", "9")):
            yf_ticker = f"{base}.SS"
        else:
            yf_ticker = f"{base}.SZ"

    df = yf.download(yf_ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError(f"yfinance returned empty dataframe for {yf_ticker}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float)


def fetch_daily(ticker: str, market: str, start_date: str, end_date: str) -> tuple[pd.DataFrame, str]:
    errors: list[str] = []
    for fetcher, name in [(fetch_with_akshare, "akshare"), (fetch_with_yfinance, "yfinance")]:
        try:
            df = fetcher(ticker, market, start_date, end_date)
            if not df.empty:
                return df, name
        except Exception as exc:
            errors.append(f"{name}: {exc.__class__.__name__}: {exc}")
    raise RuntimeError("all data sources failed — " + "; ".join(errors))


def resample_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    weekly = (
        daily.resample("W-FRI")
        .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
        .dropna()
    )
    return weekly


def render_chart(df: pd.DataFrame, title: str, output_path: Path, mav: tuple[int, ...]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mpf.plot(
        df,
        type="candle",
        style="yahoo",
        title=title,
        volume=True,
        figratio=(16, 9),
        figscale=1.4,
        mav=mav,
        warn_too_much_data=len(df) + 10,
        savefig=dict(fname=str(output_path), dpi=150, bbox_inches="tight"),
    )


def build_trend_description(df: pd.DataFrame, label: str, currency: str) -> str:
    start_close = float(df.iloc[0]["Close"])
    end_close = float(df.iloc[-1]["Close"])
    change_pct = (end_close - start_close) / start_close * 100
    high = float(df["High"].max())
    low = float(df["Low"].min())
    high_date = df["High"].idxmax().strftime("%Y-%m-%d")
    low_date = df["Low"].idxmin().strftime("%Y-%m-%d")
    return (
        f"{label} {df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}: "
        f"start close {start_close:.2f} {currency}, latest close {end_close:.2f} {currency} "
        f"({change_pct:+.1f}%). Period high {high:.2f} {currency} on {high_date}; "
        f"period low {low:.2f} {currency} on {low_date}."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True, help="Ticker symbol (e.g. AAPL, 00700, 600519)")
    parser.add_argument("--market", required=True, help="Market: US | HK | A")
    parser.add_argument("--output-dir", required=True, help="Absolute path to {BASE_DIR}/01_basic_data")
    args = parser.parse_args()

    try:
        market = normalize_market(args.market)
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2

    output_dir = Path(args.output_dir).resolve()
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=3 * 365 + 14)
    end_str = end_date.strftime("%Y-%m-%d")
    start_str = start_date.strftime("%Y-%m-%d")

    try:
        daily, source = fetch_daily(args.ticker, market, start_str, end_str)
    except Exception as exc:
        print(
            json.dumps(
                {"error": f"Failed to fetch data: {exc}", "trace": traceback.format_exc()},
                ensure_ascii=False,
            )
        )
        return 3

    weekly = resample_weekly(daily)

    ticker_safe = args.ticker.upper().replace(".", "_")
    daily_png = assets_dir / f"{ticker_safe}_3year_daily.png"
    weekly_png = assets_dir / f"{ticker_safe}_3year_weekly.png"

    currency = MARKET_CURRENCY[market]
    render_chart(daily, f"{args.ticker.upper()} - 3-Year Daily (MA20 / MA60)", daily_png, mav=(20, 60))
    render_chart(weekly, f"{args.ticker.upper()} - 3-Year Weekly (MA13 / MA52)", weekly_png, mav=(13, 52))

    latest = daily.iloc[-1]
    summary = {
        "ticker": args.ticker.upper(),
        "market": market,
        "currency": currency,
        "data_source": source,
        "current_price": float(latest["Close"]),
        "as_of_date": daily.index[-1].strftime("%Y-%m-%d"),
        "period_start": daily.index[0].strftime("%Y-%m-%d"),
        "period_end": daily.index[-1].strftime("%Y-%m-%d"),
        "period_high": float(daily["High"].max()),
        "period_low": float(daily["Low"].min()),
        "daily_chart_relpath": f"assets/{daily_png.name}",
        "weekly_chart_relpath": f"assets/{weekly_png.name}",
        "daily_chart_abspath": str(daily_png),
        "weekly_chart_abspath": str(weekly_png),
        "daily_trend_description": build_trend_description(daily, "日K", currency),
        "weekly_trend_description": build_trend_description(weekly, "周K", currency),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
