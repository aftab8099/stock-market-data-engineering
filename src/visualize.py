"""Visualisation (Report §5.6).

Line chart of closing prices per symbol from the loaded table.
Reads the processed CSV (no database needed) and saves a PNG to
``outputs/``. Matplotlib is optional — the pipeline runs without it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def plot_closing_prices(csv_path=None, out_path=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    csv_path = Path(csv_path or ROOT / "data" / "processed" / "stock_prices.csv")
    out_path = Path(out_path or ROOT / "outputs" / "closing_prices.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path, parse_dates=["trade_date"])
    fig, ax = plt.subplots(figsize=(10, 5))
    for symbol, group in df.sort_values("trade_date").groupby("symbol"):
        ax.plot(group["trade_date"], group["close_price"], marker="o",
                markersize=3, label=symbol)
    ax.set_title("Historical Closing Prices — Controlled Test Dataset (1 Sep – 12 Oct 2026)")
    ax.set_xlabel("Trading date")
    ax.set_ylabel("Closing price")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    # SVG twin: same chart as text, so it can live in git / on GitHub.
    svg_path = out_path.with_suffix(".svg")
    fig.savefig(svg_path)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    print("Saved:", plot_closing_prices())
