# End-to-End Stock Market Data Engineering

A Python-based ETL pipeline for stock market data extraction, processing,
storage, and analytics — BCS-752 Mini Project / Internship Assessment,
B.Tech Final Year, Semester VII, AKGEC Ghaziabad (Session 2026–2027).

Submitted by **Aftab Alam** (Roll No. 2300270100011, CSE / CSE-1),
under the guidance of **Mr Sandeep Yadav**.

> **Honest scope note — read this first.** The figures in this repo come
> from a **controlled test dataset**, not a live market API feed
> (Report §5.1). The sample file holds synthetic prices for AAPL and
> MSFT over 30 business days, 1 Sep – 12 Oct 2026, with deliberate
> duplicates and faults so the validation, duplicate-handling and
> UPSERT logic can be tested and proved. No live API was exercised for
> the report's Chapter 5 figures, and nothing here claims real market
> prices, returns, or performance at scale.

## What it does

```
Stock Market API / CSV  →  Extract  →  Transform (Pandas)
                        →  Validate (DQ-01 … DQ-07)
                        →  Load (PostgreSQL, UPSERT)
                        →  SQL Analytics (LAG returns, 5-day moving average)
```

- **Extract** (`src/extract.py`) — CSV file (default) or Alpha Vantage
  `TIME_SERIES_DAILY` API (optional, needs `STOCK_API_KEY`).
- **Transform** (`src/transform.py`) — standardises column names,
  coerces numerics/dates instead of crashing on bad values.
- **Validate** (`src/validate.py`) — DQ-01 symbol present, DQ-02 valid
  date, DQ-03 numeric convertible, DQ-04 high ≥ low, DQ-05 volume ≥ 0,
  DQ-06 duplicates handled at load, DQ-07 schema requirements.
  Rejected rows are kept with their rule id, never silently fixed.
- **Load** (`src/load.py`) — `INSERT … ON CONFLICT (symbol, trade_date)
  DO UPDATE` (UPSERT). Re-running the pipeline updates rows, never
  duplicates them.
- **Analytics** (`sql/analytics.sql`) — historical prices, daily price
  change, daily % return, 5-observation moving average.

## Project structure

```
stock-market-data-engineering/
├── data/raw/sample_stock_data.csv   # controlled test dataset (68 rows)
├── src/
│   ├── extract.py  transform.py  validate.py
│   ├── load.py     database.py   pipeline.py  visualize.py
├── sql/schema.sql                   # stock_prices table (Report §3.6)
├── sql/analytics.sql                # Listings 4.7–4.10, 5.1
├── scripts/generate_sample_data.py  # regenerates the test CSV (seed 42)
├── tests/                           # pytest: TC-01 … TC-08 + DQ rules
├── docs/test-run.md                 # verified run output (26 Nov 2026)
├── .env.example  .gitignore  requirements.txt  README.md
```

## Quick start (no database server needed)

```bash
pip install -r requirements.txt
python -m src.pipeline --rerun-upsert
python -m pytest tests/ -v
python -m src.visualize   # outputs/closing_prices.png
```

The default run uses SQLite, which implements the same schema
(same primary key, same CHECK constraints) and the same
`ON CONFLICT` UPSERT as PostgreSQL, so the logic is verifiable
without a server. Timings from this run are local test-run timings,
not PostgreSQL production timings.

## Verified test run — 26 Nov 2026

```
Source:            Controlled test dataset (sample_stock_data.csv) — not a live API feed
Symbols:           AAPL, MSFT
Date range:        2026-09-01 to 2026-10-12
Records retrieved: 68
Records validated: 62
Records loaded:    60
Rejected records:  6 {'DQ-03': 2, 'DQ-04': 1, 'DQ-05': 1, 'DQ-01': 1, 'DQ-02': 1}
Duplicates:        2
UPSERT re-run:     60 updated, total still 60
Pipeline status:   Completed (test run)
```

Reconciliation: **60 loaded + 6 rejected + 2 duplicates = 68 retrieved.**
Per symbol: AAPL 30 rows, MSFT 30 rows. Daily returns: 58 non-null
(the first row of each symbol has no previous close). Tests:
**13 passed** (`pytest tests/ -v`). Full output: `docs/test-run.md`.

The 6 rejections are one of each: high < low, negative volume,
non-numeric close (`N/A`), missing symbol, malformed date
(`2026-13-40`), missing close. The 2 duplicates are exact repeats
of AAPL 2026-09-01 and MSFT 2026-09-02.

## PostgreSQL setup (the project's real database)

```bash
createdb stock_market_db
psql -d stock_market_db -f sql/schema.sql
cp .env.example .env   # fill in DB_USER / DB_PASSWORD, never commit .env
python -m src.pipeline --db postgres --rerun-upsert
psql -d stock_market_db -f sql/analytics.sql
```

For a live feed instead of the test CSV, set `STOCK_API_KEY`
(Alpha Vantage, free tier) and run:

```bash
python -m src.pipeline --source api --symbols AAPL MSFT --db postgres
```

## Tech stack

Python, Pandas, Requests, PostgreSQL (psycopg2), SQL, Pytest,
Matplotlib, Git / GitHub. Scheduling (Airflow) and dashboards
(Power BI / Streamlit) are listed as future scope in the report
(Chapter 6) and are **not** implemented here.

## Report

The full BCS-752 report — *End-to-End Stock Market Data Engineering* —
is in the companion report PDF (32 pages, AKGEC blueprint format).
Chapter 5 of the report is built on exactly the test run above.
