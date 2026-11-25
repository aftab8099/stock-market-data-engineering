"""Transformation stage (Report §4.3).

Standardises column names, maps provider-specific names to the
canonical schema, and converts dates / numerics — coercing bad values
to NaT / NaN instead of crashing, so ``validate.py`` can reject them
with a named rule (DQ-02 / DQ-03) rather than the pipeline dying.
"""
from __future__ import annotations

import pandas as pd

CANONICAL_COLUMNS = [
    "symbol", "trade_date", "open_price", "high_price",
    "low_price", "close_price", "volume",
]

# Provider / file header variants -> canonical names.
COLUMN_ALIASES = {
    "date": "trade_date",
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "adjusted close": "adjusted_close",
    "adjusted_close": "adjusted_close",
    "adj_close": "adjusted_close",
    "vol": "volume",
}

NUMERIC_COLUMNS = ["open_price", "high_price", "low_price", "close_price", "volume"]


def transform_stock_data(df):
    """Standardise one raw DataFrame (Report Listing 4.3, extended).

    - strip / lowercase / underscore column names, apply aliases
    - coerce numerics with ``errors="coerce"`` (bad text -> NaN)
    - parse dates with ``errors="coerce"`` (bad text -> NaT)
    - strip whitespace from symbols; empty stays empty (DQ-01 rejects it)
    - drop the ``adjusted_close`` column — not in the §3.6 schema
    - keep the original row order; do NOT drop bad rows here
    """
    if df.empty:
        return df.copy()
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns=COLUMN_ALIASES)
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    if "trade_date" in df.columns:
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.date
    if "symbol" in df.columns:
        df["symbol"] = df["symbol"].astype(str).str.strip()
        df.loc[df["symbol"].isin({"", "nan", "None"}), "symbol"] = ""
    # Keep only schema columns that exist; preserve any extra column
    # (e.g. adjusted_close) out of the load path.
    keep = [c for c in CANONICAL_COLUMNS if c in df.columns]
    return df[keep]
