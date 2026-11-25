"""Data-quality rules DQ-01 … DQ-07 (Report §4.4, Table 4.1)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import validate


def _row(**over):
    base = {"symbol": "AAPL", "trade_date": pd.to_datetime("2026-09-01").date(),
            "open_price": 100.0, "high_price": 105.0, "low_price": 99.0,
            "close_price": 103.0, "volume": 1000}
    base.update(over)
    return pd.DataFrame([base])


def test_each_rule_rejects_its_fault():
    cases = [
        ({"symbol": ""}, "DQ-01"),
        ({"trade_date": pd.NaT}, "DQ-02"),
        ({"close_price": float("nan")}, "DQ-03"),
        ({"high_price": 90.0, "low_price": 99.0}, "DQ-04"),
        ({"volume": -5}, "DQ-05"),
    ]
    for over, rule in cases:
        _, rejected = validate.validate_stock_data(_row(**over))
        assert len(rejected) == 1 and rejected.iloc[0]["rejection_reason"] == rule, rule


def test_clean_row_passes():
    valid, rejected = validate.validate_stock_data(_row())
    assert len(valid) == 1 and rejected.empty


def test_duplicates_are_flagged_not_rejected():
    df = pd.concat([_row(), _row()], ignore_index=True)
    valid, rejected = validate.validate_stock_data(df)
    assert len(valid) == 2 and rejected.empty  # load step handles DQ-06
    assert len(validate.find_duplicates(valid)) == 1
