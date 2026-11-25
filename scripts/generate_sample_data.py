"""Generate the controlled test dataset (Report §5.1).

Writes ``data/raw/sample_stock_data.csv``: 30 business days,
1 Sep – 12 Oct 2026, for AAPL and MSFT — 60 clean rows — plus
2 deliberate duplicates and 6 deliberate faults, 68 rows total:

  fault 1  AAPL 2026-09-15  high price below low price        (DQ-04)
  fault 2  MSFT 2026-09-16  negative volume                  (DQ-05)
  fault 3  AAPL 2026-09-17  non-numeric closing price "N/A"  (DQ-03)
  fault 4  (no symbol) 2026-09-18  missing symbol            (DQ-01)
  fault 5  MSFT 2026-13-40  malformed date                   (DQ-02)
  fault 6  AAPL 2026-09-21  missing closing price            (DQ-03/DQ-07)

Duplicates: exact repeats of AAPL 2026-09-01 and MSFT 2026-09-02 (DQ-06).

Prices are a deterministic random walk (seed 42) — synthetic test
data, NOT real market prices. Do not present them as live market data.
Run:  python scripts/generate_sample_data.py
"""
from __future__ import annotations

import datetime
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "sample_stock_data.csv"

STARTS = {"AAPL": 232.0, "MSFT": 512.0}


def business_days(start, end):
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += datetime.timedelta(days=1)
    return days


def main():
    rng = random.Random(42)
    days = business_days(datetime.date(2026, 9, 1), datetime.date(2026, 10, 12))
    assert len(days) == 30, len(days)
    rows = []
    for symbol in ("AAPL", "MSFT"):
        price = STARTS[symbol]
        for day in days:
            open_p = round(price, 2)
            close_p = round(price * (1 + rng.uniform(-0.012, 0.014)), 2)
            high_p = round(max(open_p, close_p) * (1 + rng.uniform(0.001, 0.006)), 2)
            low_p = round(min(open_p, close_p) * (1 - rng.uniform(0.001, 0.006)), 2)
            volume = rng.randint(18_000_000, 42_000_000) if symbol == "AAPL" \
                else rng.randint(12_000_000, 28_000_000)
            rows.append([symbol, day.isoformat(), f"{open_p:.2f}", f"{high_p:.2f}",
                         f"{low_p:.2f}", f"{close_p:.2f}", volume])
            price = close_p

    by_key = {(r[0], r[1]): r for r in rows}

    def clone(key, **over):
        r = list(by_key[key])
        cols = ["symbol", "trade_date", "open_price", "high_price",
                "low_price", "close_price", "volume"]
        for k, v in over.items():
            r[cols.index(k)] = v
        return r

    # 2 deliberate duplicates (exact repeats)
    dups = [list(by_key[("AAPL", "2026-09-01")]),
            list(by_key[("MSFT", "2026-09-02")])]
    # 6 deliberate faults — each breaks exactly one rule
    faults = [
        clone(("AAPL", "2026-09-15"), high_price="180.00", low_price="230.00"),
        clone(("MSFT", "2026-09-16"), volume="-100"),
        clone(("AAPL", "2026-09-17"), close_price="N/A"),
        clone(("AAPL", "2026-09-18"), symbol=""),
        clone(("MSFT", "2026-09-18"), trade_date="2026-13-40"),
        clone(("AAPL", "2026-09-21"), close_price=""),
    ]
    all_rows = rows + dups + faults
    assert len(all_rows) == 68, len(all_rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        f.write("symbol,trade_date,open_price,high_price,low_price,close_price,volume\n")
        for r in all_rows:
            f.write(",".join(str(x) for x in r) + "\n")
    print(f"Wrote {OUT} — {len(all_rows)} rows "
          f"(60 clean + 2 duplicates + 6 faults)")


if __name__ == "__main__":
    main()
