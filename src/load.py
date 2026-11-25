"""Loading stage (Report §4.6, §4.7).

Writes validated rows to ``stock_prices`` with an UPSERT:
``INSERT ... ON CONFLICT (symbol, trade_date) DO UPDATE``.
A row whose (symbol, trade_date) already exists is counted as a
duplicate — updated on a re-run, never inserted twice — so the table
total stays at the number of distinct valid observations.

Both PostgreSQL (psycopg2, ``%s`` placeholders) and SQLite
(``?`` placeholders) use the same ON CONFLICT statement; only the
placeholder style differs.
"""
from __future__ import annotations

import pandas as pd

UPSERT_SQL = """
INSERT INTO stock_prices
    (symbol, trade_date, open_price, high_price, low_price, close_price, volume)
VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
ON CONFLICT (symbol, trade_date) DO UPDATE SET
    open_price  = EXCLUDED.open_price,
    high_price  = EXCLUDED.high_price,
    low_price   = EXCLUDED.low_price,
    close_price = EXCLUDED.close_price,
    volume      = EXCLUDED.volume
"""


def _existing_keys(conn, dialect):
    cur = conn.cursor()
    cur.execute("SELECT symbol, trade_date FROM stock_prices")
    keys = set()
    for symbol, trade_date in cur.fetchall():
        keys.add((symbol, str(trade_date)))
    return keys


def load_dataframe(df, conn, dialect="postgres"):
    """Load validated rows. Returns a counts dict.

    ``inserted`` — new (symbol, trade_date) rows.
    ``updated`` — rows that already existed and were overwritten
        by the UPSERT (0 on a first load, N on a re-run).
    ``duplicates_skipped`` — repeats of a (symbol, trade_date)
        already seen in this same batch (DQ-06). On the 68-row test
        file this is 2, matching the report's Table 5.2.
    """
    if df.empty:
        return {"inserted": 0, "updated": 0, "duplicates_skipped": 0}

    before = _existing_keys(conn, dialect)
    ph = "%s" if dialect == "postgres" else "?"
    sql = UPSERT_SQL.format(ph=ph)
    cur = conn.cursor()
    inserted = updated = duplicates_skipped = 0
    seen_in_batch = set()
    for row in df.itertuples(index=False):
        key = (row.symbol, str(row.trade_date))
        if key in seen_in_batch:
            # Repeat inside this same batch (DQ-06): count it once
            # as a duplicate, do not execute the UPSERT again.
            duplicates_skipped += 1
            continue
        seen_in_batch.add(key)
        values = (
            row.symbol, str(row.trade_date),
            None if pd.isna(row.open_price) else float(row.open_price),
            None if pd.isna(row.high_price) else float(row.high_price),
            None if pd.isna(row.low_price) else float(row.low_price),
            None if pd.isna(row.close_price) else float(row.close_price),
            None if pd.isna(row.volume) else int(row.volume),
        )
        cur.execute(sql, values)
        if key in before:
            updated += 1
        else:
            inserted += 1
            before.add(key)
    conn.commit()
    return {
        "inserted": inserted,
        "updated": updated,
        "duplicates_skipped": duplicates_skipped,
    }


def count_by_symbol(conn):
    """Report Listing 5.1 — rows per symbol with date range."""
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, COUNT(*) AS total_records, "
        "MIN(trade_date) AS first_trading_date, "
        "MAX(trade_date) AS latest_trading_date "
        "FROM stock_prices GROUP BY symbol ORDER BY symbol"
    )
    return cur.fetchall()
