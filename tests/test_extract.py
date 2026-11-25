"""Report Table 5.1: TC-01, TC-02."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import extract

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_stock_data.csv"


def test_load_csv_returns_all_68_rows():
    """TC-01 — valid stock data is retrieved: 68 rows in the test file."""
    df = extract.load_csv(RAW)
    assert len(df) == 68
    assert set(df["symbol"].unique()) <= {"AAPL", "MSFT", ""}


def test_empty_response_is_handled_safely(tmp_path):
    """TC-02 — a source returning no records: 0 rows, no crash."""
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text(
        "symbol,trade_date,open_price,high_price,low_price,close_price,volume\n")
    df = extract.load_csv(empty_csv)
    assert df.empty
    assert len(df) == 0
    from src import transform
    assert transform.transform_stock_data(df).empty
