"""Validation stage (Report §4.4, Table 4.1).

Rules DQ-01 … DQ-07. A row failing any rule is rejected with the
first failing rule recorded in ``rejection_reason`` — never silently
corrected and never silently replaced with an invented value.

Duplicates (DQ-06) are NOT rejected here: a repeated (symbol,
trade_date) that is otherwise valid passes validation and is handled
at load time by the UPSERT policy in ``load.py`` (skipped / updated),
so the pipeline can report duplicates separately from rejections.
"""
from __future__ import annotations

import pandas as pd

RULES = {
    "DQ-01": "Stock symbol must be present.",
    "DQ-02": "Trading date must be valid.",
    "DQ-03": "Numeric fields must be convertible.",
    "DQ-04": "High price should not be lower than low price.",
    "DQ-05": "Trading volume should not be negative.",
    "DQ-06": "Duplicate symbol-date combinations must be handled.",
    "DQ-07": "Required fields must satisfy the database schema.",
}

REQUIRED_NUMERIC = ["open_price", "high_price", "low_price", "close_price"]


def _first_failure(row):
    """Return the first failing rule id for one row, or None."""
    symbol = row.get("symbol")
    if symbol is None or (isinstance(symbol, float) and pd.isna(symbol)) \
            or str(symbol).strip() == "":
        return "DQ-01"
    trade_date = row.get("trade_date")
    if trade_date is None or (isinstance(trade_date, float) and pd.isna(trade_date)) \
            or pd.isna(trade_date):
        return "DQ-02"
    for col in REQUIRED_NUMERIC:
        value = row.get(col)
        if value is None or pd.isna(value):
            return "DQ-03"  # also covers DQ-07 for a missing close price
    high, low = row.get("high_price"), row.get("low_price")
    if pd.notna(high) and pd.notna(low) and high < low:
        return "DQ-04"
    volume = row.get("volume")
    if pd.notna(volume) and volume < 0:
        return "DQ-05"
    return None


def validate_stock_data(df):
    """Split a transformed DataFrame into (valid, rejected).

    ``rejected`` carries a ``rejection_reason`` column with the rule id
    and a ``rejection_detail`` column with the human-readable rule.
    """
    if df.empty:
        return df.copy(), df.copy()
    df = df.copy()
    failures = df.apply(_first_failure, axis=1)
    rejected = df[failures.notna()].copy()
    rejected["rejection_reason"] = failures[failures.notna()]
    rejected["rejection_detail"] = rejected["rejection_reason"].map(RULES)
    valid = df[failures.isna()].copy()
    return valid, rejected


def find_duplicates(df):
    """Rows whose (symbol, trade_date) already appeared earlier in ``df``.

    Used for reporting (DQ-06); the load step is the authority on
    what is actually a duplicate against the database.
    """
    if df.empty:
        return df.copy()
    return df[df.duplicated(subset=["symbol", "trade_date"], keep="first")].copy()
