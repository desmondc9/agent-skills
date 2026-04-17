# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "requests>=2.31",
#     "mplfinance>=0.12.10b0",
#     "pandas>=2.0",
#     "matplotlib>=3.7",
# ]
# ///
"""Fetch accurate crypto price and generate 3-year K-line PNG charts.

Primary data source: CoinGecko public API (no API key required).
Fallback: Binance public REST API.

Usage:
    uv run --script fetch_crypto_data.py \
        --asset-class crypto \
        --coin-id bitcoin --symbol BTC \
        --output-dir /abs/path/to/BASE_DIR/01_basic_data

Outputs (written to --output-dir):
    - assets/{SYMBOL}_3year_daily.png
    - assets/{SYMBOL}_3year_weekly.png
    - Prints JSON summary to stdout (same shape as fetch_stock_data.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import mplfinance as mpf
import pandas as pd
import requests


COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BINANCE_BASE = "https://api.binance.com/api/v3"
REQUEST_TIMEOUT = 30
USER_AGENT = "analyze-asset-with-agents-team/1.0 (+https://github.com/desmondc9/agent-skills)"


def _get(url: str, params: dict[str, Any] | None = None) -> Any:
    resp = requests.get(
        url,
        params=params,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_with_coingecko(coin_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Fetch daily OHLC from CoinGecko.

    CoinGecko's /coins/{id}/ohlc endpoint returns up to 180 days per call when
    `days` <= 180, and daily candles when `days >= 90`. For a 3-year window we
    use the market_chart endpoint which always returns daily data for ranges
    longer than 90 days and reconstruct synthetic OHLC from the price series.
    """
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart/range"
    params = {
        "vs_currency": "usd",
        "from": int(start.timestamp()),
        "to": int(end.timestamp()),
    }
    payload = _get(url, params=params)
    prices = payload.get("prices") or []
    volumes = payload.get("total_volumes") or []
    if not prices:
        raise RuntimeError("CoinGecko returned empty price series")

    price_df = pd.DataFrame(prices, columns=["ts_ms", "price"])
    price_df["date"] = pd.to_datetime(price_df["ts_ms"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
    vol_df = pd.DataFrame(volumes, columns=["ts_ms", "volume"])
    vol_df["date"] = pd.to_datetime(vol_df["ts_ms"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()

    agg = (
        price_df.groupby("date")["price"]
        .agg(Open="first", High="max", Low="min", Close="last")
        .reset_index()
    )
    volume_daily = vol_df.groupby("date")["volume"].sum().reset_index()
    merged = agg.merge(volume_daily, on="date", how="left").set_index("date").sort_index()
    merged = merged.rename(columns={"volume": "Volume"})
    merged["Volume"] = merged["Volume"].fillna(0.0)
    return merged[["Open", "High", "Low", "Close", "Volume"]].astype(float)


def fetch_with_binance(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Fetch daily klines from Binance, paginated in 1000-candle chunks."""
    pair = f"{symbol.upper()}USDT"
    url = f"{BINANCE_BASE}/klines"
    chunks: list[list[Any]] = []
    cursor_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    one_day_ms = 24 * 60 * 60 * 1000
    while cursor_ms < end_ms:
        params = {
            "symbol": pair,
            "interval": "1d",
            "startTime": cursor_ms,
            "endTime": end_ms,
            "limit": 1000,
        }
        batch = _get(url, params=params)
        if not batch:
            break
        chunks.extend(batch)
        last_open_ms = batch[-1][0]
        cursor_ms = last_open_ms + one_day_ms
        if len(batch) < 1000:
            break
        time.sleep(0.25)
    if not chunks:
        raise RuntimeError(f"Binance returned no klines for {pair}")
    df = pd.DataFrame(
        chunks,
        columns=[
            "open_time", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
        ],
    )
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["Open", "High", "Low", "Close", "Volume"]].astype(float)


def fetch_daily(coin_id: str, symbol: str, start: datetime, end: datetime) -> tuple[pd.DataFrame, str]:
    errors: list[str] = []
    try:
        df = fetch_with_coingecko(coin_id, start, end)
        if not df.empty:
            return df, "coingecko"
    except Exception as exc:
        errors.append(f"coingecko: {exc.__class__.__name__}: {exc}")
    try:
        df = fetch_with_binance(symbol, start, end)
        if not df.empty:
            return df, "binance"
    except Exception as exc:
        errors.append(f"binance: {exc.__class__.__name__}: {exc}")
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
    parser.add_argument("--asset-class", default="crypto", help="Asset class tag (default: crypto)")
    parser.add_argument("--coin-id", required=True, help="CoinGecko id (e.g. bitcoin, ethereum, solana)")
    parser.add_argument("--symbol", required=True, help="Ticker symbol for Binance fallback (e.g. BTC, ETH)")
    parser.add_argument("--output-dir", required=True, help="Absolute path to {BASE_DIR}/01_basic_data")
    parser.add_argument("--currency", default="USD", help="Reporting currency (default: USD)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    end = datetime.now(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(days=3 * 365 + 14)

    try:
        daily, source = fetch_daily(args.coin_id, args.symbol, start, end)
    except Exception as exc:
        print(
            json.dumps(
                {"error": f"Failed to fetch data: {exc}", "trace": traceback.format_exc()},
                ensure_ascii=False,
            )
        )
        return 3

    weekly = resample_weekly(daily)

    symbol_safe = args.symbol.upper().replace("/", "_").replace(".", "_")
    daily_png = assets_dir / f"{symbol_safe}_3year_daily.png"
    weekly_png = assets_dir / f"{symbol_safe}_3year_weekly.png"

    render_chart(daily, f"{args.symbol.upper()} - 3-Year Daily (MA20 / MA60)", daily_png, mav=(20, 60))
    render_chart(weekly, f"{args.symbol.upper()} - 3-Year Weekly (MA13 / MA52)", weekly_png, mav=(13, 52))

    latest = daily.iloc[-1]
    summary = {
        "asset_class": "crypto",
        "coin_id": args.coin_id,
        "symbol": args.symbol.upper(),
        "currency": args.currency.upper(),
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
        "daily_trend_description": build_trend_description(daily, "日K", args.currency.upper()),
        "weekly_trend_description": build_trend_description(weekly, "周K", args.currency.upper()),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
