"""End-to-end pipeline runner (Report §3.5, §4.1).

    python -m src.pipeline --source csv --db sqlite
    python -m src.pipeline --source csv --db postgres   # needs .env
    python -m src.pipeline --source api --symbols AAPL MSFT --db postgres

Default (no flags) runs the controlled test dataset on SQLite and
writes a run summary to ``logs/run_summary.json`` plus the validated
rows to ``data/processed/stock_prices.csv`` — the exact figures the
report's Chapter 5 is built on. Nothing here invents live market
numbers: with ``--source csv`` every figure comes from
``data/raw/sample_stock_data.csv``.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import database, extract, load, transform, validate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "raw" / "sample_stock_data.csv"


def run(source="csv", input_path=None, symbols=("AAPL", "MSFT"),
        db="sqlite", db_path=None, rerun_upsert=False):
    """Run Extract -> Transform -> Validate -> Load. Returns summary dict."""
    t0 = time.perf_counter()
    timings = {}

    # Extract
    t = time.perf_counter()
    if source == "csv":
        raw = extract.load_csv(input_path or DEFAULT_CSV)
        source_label = f"Controlled test dataset ({Path(input_path or DEFAULT_CSV).name}) — not a live API feed"
    elif source == "api":
        raw = extract.fetch_stock_data_for_symbols(list(symbols))
        source_label = "Alpha Vantage API (TIME_SERIES_DAILY)"
    else:
        raise ValueError(f"unknown --source {source!r} (csv or api)")
    timings["extraction"] = round(time.perf_counter() - t, 6)
    retrieved = len(raw)

    # Transform
    t = time.perf_counter()
    transformed = transform.transform_stock_data(raw)
    timings["transformation"] = round(time.perf_counter() - t, 6)

    # Validate (DQ-01 … DQ-07)
    t = time.perf_counter()
    valid, rejected = validate.validate_stock_data(transformed)
    timings["validation"] = round(time.perf_counter() - t, 6)

    # Load
    t = time.perf_counter()
    if db == "sqlite":
        conn = database.get_sqlite_connection(str(db_path or ":memory:"))
        database.create_tables(conn, dialect="sqlite")
    elif db == "postgres":
        conn = database.get_connection()
        database.create_tables(conn, dialect="postgres")
    else:
        raise ValueError(f"unknown --db {db!r} (sqlite or postgres)")
    counts = load.load_dataframe(valid, conn, dialect=db)
    if rerun_upsert:
        # Second load of the same valid rows: proves the UPSERT —
        # 60 updated, total still 60 (Report TC-06).
        counts_rerun = load.load_dataframe(valid, conn, dialect=db)
    else:
        counts_rerun = None
    timings["loading"] = round(time.perf_counter() - t, 6)
    total_time = round(time.perf_counter() - t0, 6)

    by_symbol = [
        {"symbol": s, "total_records": n, "first_trading_date": str(a), "latest_trading_date": str(b)}
        for s, n, a, b in load.count_by_symbol(conn)
    ]
    total_loaded = sum(r["total_records"] for r in by_symbol)
    conn.close()

    summary = {
        "source": source_label,
        "symbols": sorted(valid["symbol"].unique().tolist()) if not valid.empty else [],
        "date_range": (
            f"{min(valid['trade_date'])} to {max(valid['trade_date'])}"
            if not valid.empty else None
        ),
        "retrieved": retrieved,
        "valid": len(valid),
        "rejected": len(rejected),
        "rejected_by_rule": rejected["rejection_reason"].value_counts().to_dict()
        if not rejected.empty else {},
        "duplicates": counts["duplicates_skipped"],
        "inserted": counts["inserted"],
        "updated_first_load": counts["updated"],
        "updated_on_rerun": counts_rerun["updated"] if counts_rerun else None,
        "total_in_table": total_loaded,
        "by_symbol": by_symbol,
        "timings_seconds": {**timings, "total": total_time},
        "throughput_records_per_second": (
            round(retrieved / total_time, 1) if total_time else None
        ),
        "status": "Completed (test run)" if source == "csv" else "Completed",
    }
    return summary, valid, rejected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["csv", "api"], default="csv")
    parser.add_argument("--input", default=None, help="CSV path for --source csv")
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT"])
    parser.add_argument("--db", choices=["sqlite", "postgres"], default="sqlite")
    parser.add_argument("--db-path", default="data/processed/stock_market.db")
    parser.add_argument("--rerun-upsert", action="store_true",
                        help="Load the valid rows a second time to prove UPSERT (TC-06)")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not write processed CSV / summary files")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary, valid, rejected = run(
        source=args.source, input_path=args.input, symbols=args.symbols,
        db=args.db,
        db_path=(ROOT / args.db_path) if args.db == "sqlite" and args.db_path != ":memory:" else ":memory:",
        rerun_upsert=args.rerun_upsert,
    )

    print(f"Source:            {summary['source']}")
    print(f"Symbols:           {', '.join(summary['symbols'])}")
    print(f"Date range:        {summary['date_range']}")
    print(f"Records retrieved: {summary['retrieved']}")
    print(f"Records validated: {summary['valid']}")
    print(f"Records loaded:    {summary['inserted']}")
    print(f"Rejected records:  {summary['rejected']} {summary['rejected_by_rule']}")
    print(f"Duplicates:        {summary['duplicates']}")
    if summary["updated_on_rerun"] is not None:
        print(f"UPSERT re-run:     {summary['updated_on_rerun']} updated, "
              f"total still {summary['total_in_table']}")
    print(f"Execution time:    {summary['timings_seconds']['total']}s "
          f"(extract {summary['timings_seconds']['extraction']}s, "
          f"transform {summary['timings_seconds']['transformation']}s, "
          f"load {summary['timings_seconds']['loading']}s)")
    print(f"Pipeline status:   {summary['status']}")

    if not args.no_save:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "data" / "processed").mkdir(exist_ok=True)
        with open(ROOT / "logs" / "run_summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        valid.to_csv(ROOT / "data" / "processed" / "stock_prices.csv", index=False)
        if not rejected.empty:
            rejected.to_csv(ROOT / "data" / "processed" / "rejected_records.csv", index=False)
        print("Saved: logs/run_summary.json, data/processed/stock_prices.csv")
    return summary


if __name__ == "__main__":
    main()
