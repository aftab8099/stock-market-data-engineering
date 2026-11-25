"""Database layer (Report §4.5, §3.6).

PostgreSQL is the project's database. Credentials come only from
environment variables (Report Listing 4.5) — never from source code.

For the controlled test run (Report §5.1) the same schema and the
same UPSERT semantics are also available on SQLite, so the pipeline
and tests can run and be verified without a PostgreSQL server.
Timings from a SQLite run are local test-run timings, not PostgreSQL
production timings — the report says so explicitly.
"""
from __future__ import annotations

import os
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol      VARCHAR(20)    NOT NULL,
    trade_date  DATE           NOT NULL,
    open_price  NUMERIC(14, 4),
    high_price  NUMERIC(14, 4),
    low_price   NUMERIC(14, 4),
    close_price NUMERIC(14, 4),
    volume      BIGINT,
    created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, trade_date),
    CHECK (high_price IS NULL OR low_price IS NULL OR high_price >= low_price),
    CHECK (volume IS NULL OR volume >= 0)
);
"""

# SQLite accepts the same DDL except TIMESTAMPTZ (stored as TEXT).
SQLITE_SCHEMA_SQL = SCHEMA_SQL.replace("TIMESTAMPTZ", "TEXT")


def get_connection():
    """PostgreSQL connection from env vars (Report Listing 4.5)."""
    import psycopg2

    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "stock_market_db"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def get_sqlite_connection(path=":memory:"):
    """SQLite connection for the local test run / unit tests."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables(conn, dialect="postgres"):
    """Create ``stock_prices``. ``dialect`` is 'postgres' or 'sqlite'."""
    sql = SCHEMA_SQL if dialect == "postgres" else SQLITE_SCHEMA_SQL
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
