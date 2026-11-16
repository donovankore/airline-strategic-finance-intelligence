#!/usr/bin/env python3
"""Create restrained, publication-style figures from the processed dataset."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "carrier_annual_performance.csv"
FIGURES = ROOT / "reports" / "figures"

COLORS = {
    "DAL": "#B3262E",
    "UAL": "#005DAA",
    "AAL": "#4B8BBE",
    "LUV": "#C89211",
}
LABELS = {
    "DAL": "Delta",
    "UAL": "United",
    "AAL": "American",
    "LUV": "Southwest",
}


def setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#334155",
            "text.color": "#172033",
            "axes.edgecolor": "#CBD5E1",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
            "axes.grid": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def finish(fig: plt.Figure, filename: str) -> None:
    fig.text(
        0.01,
        0.01,
        "Sources: U.S. SEC Company Facts API and U.S. DOT/BTS T-100. Analysis as of 2025 fiscal year.",
        fontsize=8,
        color="#64748B",
    )
    fig.savefig(FIGURES / filename, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def peer_comparison(data: pd.DataFrame) -> None:
    latest = data[data["year"] == 2025].sort_values("operating_margin", ascending=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"wspace": 0.38})
    fig.suptitle("2025 financial performance", fontsize=16, fontweight="bold", x=0.01, ha="left")

    for ax, metric, title in [
        (axes[0], "operating_margin", "Operating margin"),
        (axes[1], "cfo_margin", "Operating cash flow margin"),
    ]:
        values = latest[metric]
        bars = ax.barh(
            [LABELS[t] for t in latest["ticker"]],
            values,
            color=[COLORS[t] for t in latest["ticker"]],
            height=0.58,
        )
        ax.set_title(title, loc="left")
        ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
        ax.set_xlim(min(-0.01, values.min() - 0.015), values.max() + 0.03)
        ax.axvline(0, color="#94A3B8", linewidth=0.8)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        for bar, value in zip(bars, values):
            ax.text(
                value + 0.004,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1%}",
                va="center",
                fontsize=10,
                fontweight="bold",
            )
    finish(fig, "2025_financial_performance.png")


def trend_chart(data: pd.DataFrame, metric: str, title: str, filename: str, decimals: int = 0) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    ax.set_title(title, loc="left", fontsize=15, pad=12)
    for ticker in ["DAL", "UAL", "AAL", "LUV"]:
        subset = data[data["ticker"] == ticker].sort_values("year")
        ax.plot(
            subset["year"],
            subset[metric],
            color=COLORS[ticker],
            linewidth=2.3,
            marker="o",
            markersize=4.5,
            label=LABELS[ticker],
        )
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=decimals))
    ax.axhline(0, color="#94A3B8", linewidth=0.8)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.02))
    finish(fig, filename)


def fuel_sensitivity(data: pd.DataFrame) -> None:
    latest = data[data["year"] == 2025].copy()
    latest["actual_margin"] = latest["operating_margin"]
    latest["stressed_margin"] = (
        latest["operating_income_usd"] - 0.15 * latest["fuel_cost_usd"]
    ) / latest["revenue_usd"]
    latest = latest.sort_values("actual_margin", ascending=False)

    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    ax.set_title("Operating margin sensitivity to a 15% increase in fuel cost", loc="left", fontsize=15, pad=14)
    x = range(len(latest))
    width = 0.34
    actual = ax.bar([i - width / 2 for i in x], latest["actual_margin"], width, color="#1F4E78", label="2025 actual")
    stressed = ax.bar([i + width / 2 for i in x], latest["stressed_margin"], width, color="#A8B3C2", label="Fuel sensitivity")
    ax.set_xticks(list(x), [LABELS[t] for t in latest["ticker"]])
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.axhline(0, color="#64748B", linewidth=0.9)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(frameon=False, loc="upper right")
    for collection in [actual, stressed]:
        for bar in collection:
            value = bar.get_height()
            offset = 0.003 if value >= 0 else -0.006
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + offset,
                f"{value:.1%}",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=9,
            )
    fig.text(
        0.01,
        0.055,
        "Sensitivity holds revenue, capacity and non-fuel operating costs constant. It excludes hedging and management actions.",
        fontsize=8.5,
        color="#475569",
    )
    finish(fig, "fuel_cost_sensitivity.png")


def main() -> None:
    setup()
    FIGURES.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(DATA)
    peer_comparison(data)
    trend_chart(data, "operating_margin", "Operating margin, 2019–2025", "operating_margin_trend.png")
    trend_chart(data, "load_factor", "Passenger load factor, 2019–2025", "load_factor_trend.png")
    fuel_sensitivity(data)
    print(f"Created figures in {FIGURES}")


if __name__ == "__main__":
    main()

