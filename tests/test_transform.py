"""Report Table 5.1: TC-03, TC-04 (via transform + validate)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import extract, transform, validate

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_stock_data.csv"


def _validated():
    raw = extract.load_csv(RAW)
    transformed = transform.transform_stock_data(raw)
    return validate.validate_stock_data(transformed)


def test_transform_standardises_columns_and_types():
    raw = extract.load_csv(RAW)
    df = transform.transform_stock_data(raw)
    assert list(df.columns) == ["symbol", "trade_date", "open_price", "high_price",
                                "low_price", "close_price", "volume"]
    assert pd.api.types.is_numeric_dtype(df["close_price"])


def test_invalid_numeric_text_is_rejected():
    """TC-03 — 'N/A' closing price is identified and rejected (DQ-03)."""
    _, rejected = _validated()
    assert "DQ-03" in rejected["rejection_reason"].values


def test_malformed_date_is_rejected():
    """TC-04 — 2026-13-40 is identified and rejected (DQ-02)."""
    _, rejected = _validated()
    assert "DQ-02" in rejected["rejection_reason"].values


def test_validation_counts_match_report():
    """Report Table 5.2: 68 retrieved = 62 passed validation + 6 rejected.

    (62 = 60 unique clean rows + 2 duplicates, which pass validation
    and are handled at load time under DQ-06.)
    """
    valid, rejected = _validated()
    assert len(valid) == 62
    assert len(rejected) == 6
    assert rejected["rejection_reason"].value_counts().to_dict() == {
        "DQ-01": 1, "DQ-02": 1, "DQ-03": 2, "DQ-04": 1, "DQ-05": 1,
    }
