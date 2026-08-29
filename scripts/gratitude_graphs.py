#!/usr/bin/env python3
"""
Generates charts from the gratitude-time summary CSVs produced by gratitude_time.py.

Reads from _gen_data/ and writes PNGs to _gen_images/:
  - bar_by_party.png:        talking time vs. gratitude time, grouped bars, one per party
  - bar_by_politician.png:   same, for the most talkative politicians
  - line_overall_hours.png / line_overall_proportion.png:
        gratitude time / gratitude proportion over time, corpus-wide
  - line_by_party_hours.png / line_by_party_proportion.png:
        one line per party (most talkative parties), over time
  - line_by_politician_hours.png / line_by_politician_proportion.png:
        one line per politician (most talkative politicians), over time

The bar chart height difference between the two bars visually represents the
gratitude proportion; the proportion itself is not plotted as a separate value there.

Usage:
  python3 scripts/gratitude_graphs.py
  python3 scripts/gratitude_graphs.py --top 15   # show fewer parties/politicians/lines
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "_gen_data"
OUTPUT_DIR = REPO_ROOT / "_gen_images"

BY_PARTY_CSV = DATA_DIR / "gratitude_summary_by_party.csv"
BY_POLITICIAN_CSV = DATA_DIR / "gratitude_summary_by_politician.csv"
BY_MONTH_CSV = DATA_DIR / "gratitude_summary_by_month.csv"
BY_PARTY_MONTH_CSV = DATA_DIR / "gratitude_summary_by_party_month.csv"
BY_POLITICIAN_MONTH_CSV = DATA_DIR / "gratitude_summary_by_politician_month.csv"


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def politician_label(row):
    return f"{row['speaker_first']} {row['speaker_last']}".strip()


def plot_grouped_bars(rows, label_fn, title, filename, top_n):
    rows = sorted(rows, key=lambda r: float(r["talking_time_hours"]), reverse=True)[:top_n]
    labels = [label_fn(r) for r in rows]
    talking = [float(r["talking_time_hours"]) for r in rows]
    gratitude = [float(r["gratitude_time_hours"]) for r in rows]

    x = range(len(labels))
    width = 0.4
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.5), 6))
    ax.bar([i - width / 2 for i in x], talking, width, label="Talking time (h)", color="#4C72B0")
    ax.bar([i + width / 2 for i in x], gratitude, width, label="Gratitude time (h)", color="#DD8452")

    # Annotate each pair with the gratitude proportion and absolute hours, e.g. "1.5% (0.65h)".
    top = max(talking + gratitude, default=0)
    for i, (t, g) in enumerate(zip(talking, gratitude)):
        proportion = g / t if t else 0.0
        ax.text(i, max(t, g) + top * 0.015, f"{proportion:.2%} ({g:.2f}h)", ha="center", va="bottom",
                fontsize=7, rotation=90)

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=60, ha="right")
    ax.set_ylabel("Hours")
    ax.set_ylim(top=top * 1.2)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def plot_line_single(rows, y_field, title, ylabel, filename):
    months = [r["month"] for r in rows]
    values = [float(r[y_field]) for r in rows]

    fig, ax = plt.subplots(figsize=(max(8, len(months) * 0.15), 5))
    ax.plot(months, values, color="#4C72B0")
    ax.set_xticks(months[::max(1, len(months) // 24)])
    ax.set_xticklabels(months[::max(1, len(months) // 24)], rotation=60, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def plot_line_multi(month_rows, series_rows, series_key_fields, label_fn, y_field, title, ylabel, filename, top_n):
    months = [r["month"] for r in month_rows]

    totals = defaultdict(float)
    by_series_month = defaultdict(dict)
    labels = {}
    for r in series_rows:
        key = tuple(r[f] for f in series_key_fields)
        totals[key] += float(r["talking_time_hours"])
        by_series_month[key][r["month"]] = float(r[y_field])
        labels[key] = label_fn(r)

    top_keys = sorted(totals, key=totals.get, reverse=True)[:top_n]

    fig, ax = plt.subplots(figsize=(max(8, len(months) * 0.15), 6))
    for key in top_keys:
        values = [by_series_month[key].get(m, 0.0) for m in months]
        ax.plot(months, values, label=labels[key])

    ax.set_xticks(months[::max(1, len(months) // 24)])
    ax.set_xticklabels(months[::max(1, len(months) // 24)], rotation=60, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize="small")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top-bars", type=int, default=20, help="Max parties/politicians shown per bar chart (default 20)")
    parser.add_argument("--top-lines", type=int, default=8, help="Max lines shown per multi-series line chart (default 8)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    party_rows = read_rows(BY_PARTY_CSV)
    politician_rows = read_rows(BY_POLITICIAN_CSV)
    month_rows = read_rows(BY_MONTH_CSV)
    party_month_rows = read_rows(BY_PARTY_MONTH_CSV)
    politician_month_rows = read_rows(BY_POLITICIAN_MONTH_CSV)

    plot_grouped_bars(
        party_rows, lambda r: r["party"],
        "Talking time vs. gratitude time by party", "bar_by_party.png", args.top_bars,
    )
    plot_grouped_bars(
        politician_rows, politician_label,
        "Talking time vs. gratitude time by politician", "bar_by_politician.png", args.top_bars,
    )

    plot_line_single(
        month_rows, "gratitude_time_hours",
        "Gratitude time per month (overall)", "Gratitude time (h)", "line_overall_hours.png",
    )

    # gratitude_proportion is a percent string (e.g. "0.70%"); recompute a plain ratio.
    for r in month_rows:
        r["gratitude_ratio"] = str(float(r["gratitude_time_hours"]) / float(r["talking_time_hours"])) if float(r["talking_time_hours"]) else "0"
    for r in party_month_rows:
        r["gratitude_ratio"] = str(float(r["gratitude_time_hours"]) / float(r["talking_time_hours"])) if float(r["talking_time_hours"]) else "0"
    for r in politician_month_rows:
        r["gratitude_ratio"] = str(float(r["gratitude_time_hours"]) / float(r["talking_time_hours"])) if float(r["talking_time_hours"]) else "0"

    plot_line_single(
        month_rows, "gratitude_ratio",
        "Gratitude proportion per month (overall)", "Gratitude time / talking time", "line_overall_proportion.png",
    )

    plot_line_multi(
        month_rows, party_month_rows, ["party"], lambda r: r["party"],
        "gratitude_time_hours", "Gratitude time per month by party", "Gratitude time (h)",
        "line_by_party_hours.png", args.top_lines,
    )
    plot_line_multi(
        month_rows, party_month_rows, ["party"], lambda r: r["party"],
        "gratitude_ratio", "Gratitude proportion per month by party", "Gratitude time / talking time",
        "line_by_party_proportion.png", args.top_lines,
    )

    plot_line_multi(
        month_rows, politician_month_rows, ["speaker_first", "speaker_last"], politician_label,
        "gratitude_time_hours", "Gratitude time per month by politician", "Gratitude time (h)",
        "line_by_politician_hours.png", args.top_lines,
    )
    plot_line_multi(
        month_rows, politician_month_rows, ["speaker_first", "speaker_last"], politician_label,
        "gratitude_ratio", "Gratitude proportion per month by politician", "Gratitude time / talking time",
        "line_by_politician_proportion.png", args.top_lines,
    )

    print(f"Wrote 8 charts to {OUTPUT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
