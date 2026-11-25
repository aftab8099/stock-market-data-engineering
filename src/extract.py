"""Extraction stage (Report §4.2, §3.3).

Two sources are supported, and the pipeline always records which one ran:

1. CSV file (default) — the controlled test dataset in ``data/raw/``.
   This is what the Chapter 5 test run in the report uses. No network,
   no API key, fully reproducible.
2. Alpha Vantage API (optional) — ``fetch_alpha_vantage()``. Only used
   when the user sets ``STOCK_API_KEY`` and passes ``--source api``.
   No live API was exercised for the figures in the report.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

# Alpha Vantage column names -> canonical names used by transform.py
COLUMN_MAP = {
    "Date": "trade_date",
    "date": "trade_date",
    "Symbol": "symbol",
    "Open": "open_price",
    "High": "high_price",
    "Low": "low_price",
    "Close": "close_price",
    "Adjusted Close": "adjusted_close",
    "Volume": "volume",
}


def fetch_stock_data(url, params=None):
    """Generic HTTP fetch (Report Listing 4.2).

    Returns a DataFrame, or an empty DataFrame when the provider
    returns no records. Raises for HTTP errors — the caller decides
    how to report the failure (TC-07).
    """
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    # Adapt this to the selected API response format.
    records = payload.get("data", [])
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def fetch_alpha_vantage(symbol, api_key=None, outputsize="compact"):
    """Daily prices for one symbol from Alpha Vantage (TIME_SERIES_DAILY).

    Requires an API key (free tier). Returns canonical columns plus
    ``symbol``. Raises ``ValueError`` on an API error message and
    ``requests`` errors on network failure.
    """
    api_key = api_key or os.getenv("STOCK_API_KEY")
    if not api_key:
        raise ValueError(
            "STOCK_API_KEY is not set. Put it in .env (see .env.example); "
            "never commit a real key."
        )
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": outputsize,
        "apikey": api_key,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if "Error Message" in payload or "Note" in payload:
        raise ValueError(payload.get("Error Message") or payload.get("Note"))
    series = payload.get("Time Series (Daily)", {})
    rows = [
        {"trade_date": date, "symbol": symbol, **values}
        for date, values in series.items()
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Alpha Vantage names: "1. open", "2. high", ... -> strip the prefix.
    df.columns = [c.split(". ", 1)[-1].strip() for c in df.columns]
    return df.rename(columns={
        "open": "open_price", "high": "high_price", "low": "low_price",
        "close": "close_price", "volume": "volume",
    })


def load_csv(path):
    """Load the controlled test dataset (or any CSV in canonical form).

    Reads everything as text first so that deliberate faults in the
    test file (``N/A`` close, malformed date, empty symbol) survive
    into transform/validate instead of being silently dropped or
    coerced by the CSV reader. ``keep_default_na=False`` keeps empty
    fields as empty strings; transform/validate then classify them.
    """
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    return df


def fetch_stock_data_for_symbols(symbols, api_key=None):
    """Fetch one DataFrame per symbol from Alpha Vantage and stack them."""
    frames = [fetch_alpha_vantage(s, api_key=api_key) for s in symbols]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
