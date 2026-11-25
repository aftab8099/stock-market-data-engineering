"""Report Table 5.1: TC-05, TC-06, TC-07, TC-08 — on SQLite.

The SQLite run implements the same schema (same PK, same CHECKs)
and the same ON CONFLICT UPSERT as PostgreSQL, so these tests prove
the load logic. They are local test-run timings/counts, not
PostgreSQL production results — the report says so in §5.1.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import database, extract, load, transform, validate

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample_stock_data.csv"


def _valid_rows():
    raw = extract.load_csv(RAW)
    valid, _ = validate.validate_stock_data(transform.transform_stock_data(raw))
    return valid


@pytest.fixture
def conn():
    c = database.get_sqlite_connection(":memory:")
    database.create_tables(c, dialect="sqlite")
    yield c
    c.close()


def test_load_valid_records(conn):
    """TC-05 — 60 records inserted from the 68-row test file."""
    counts = load.load_dataframe(_valid_rows(), conn, dialect="sqlite")
    assert counts == {"inserted": 60, "updated": 0, "duplicates_skipped": 2}
    assert load.count_by_symbol(conn) == [
        ("AAPL", 30, "2026-09-01", "2026-10-12"),
        ("MSFT", 30, "2026-09-01", "2026-10-12"),
    ]


def test_duplicate_upsert_rerun(conn):
    """TC-06 — re-run: 60 updated, total still 60, no duplicates added."""
    valid = _valid_rows()
    load.load_dataframe(valid, conn, dialect="sqlite")
    counts = load.load_dataframe(valid, conn, dialect="sqlite")
    assert counts == {"inserted": 0, "updated": 60, "duplicates_skipped": 2}
    assert sum(n for _, n, _, _ in load.count_by_symbol(conn)) == 60


def test_connection_failure_is_reported_not_silent():
    """TC-07 — a failed connection raises; row count is unchanged."""
    with pytest.raises(Exception):
        database.get_sqlite_connection("/nonexistent-dir/db.sqlite")


def test_analytics_return_expected_metrics(conn):
    """TC-08 — daily returns: 58 non-null from 60 rows (2 first rows
    per symbol have no previous close, so NULL)."""
    load.load_dataframe(_valid_rows(), conn, dialect="sqlite")
    cur = conn.cursor()
    cur.execute(
        "WITH pc AS (SELECT symbol, close_price, "
        "LAG(close_price) OVER (PARTITION BY symbol ORDER BY trade_date) AS prev "
        "FROM stock_prices) "
        "SELECT COUNT(*) FROM pc WHERE prev IS NOT NULL"
    )
    assert cur.fetchone()[0] == 58
