"""Validate manually entered KBO batting lines.

Hand transcription is more accurate than scraping at this sample size
(Day 31), but it is not error-free. These checks encode baseball
identities that must hold, so a typo becomes a loud failure rather than
a silently wrong rate.
"""

from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, ".")

COUNT_COLS = ["pa", "ab", "h", "double", "triple", "hr",
              "bb", "ibb", "so", "hbp", "sf"]


def main() -> None:
    df = pd.read_csv("data/external/kbo_batting.csv")
    status = pd.read_csv("data/external/kbo_mlb_status.csv")
    print(f"{len(df)} player-seasons, {df['player_en'].nunique()} players")

    problems = []

    # --- structural
    for c in COUNT_COLS:
        if c not in df.columns:
            problems.append(f"missing column: {c}")
            continue
        neg = df[df[c] < 0]
        if len(neg):
            problems.append(f"{c}: {len(neg)} negative values")

    # --- baseball identities that cannot be violated
    checks = [
        ("ab > pa", df["ab"] > df["pa"]),
        ("h > ab", df["h"] > df["ab"]),
        ("so > pa", df["so"] > df["pa"]),
        ("bb > pa", df["bb"] > df["pa"]),
        ("ibb > bb", df["ibb"] > df["bb"]),
        ("2B+3B+HR > H", df["double"] + df["triple"] + df["hr"] > df["h"]),
        # PA = AB + BB + HBP + SF + SH + interference. We lack SH, so AB +
        # BB + HBP + SF must not EXCEED PA.
        ("AB+BB+HBP+SF > PA",
         df["ab"] + df["bb"] + df["hbp"] + df["sf"] > df["pa"]),
    ]
    for label, mask in checks:
        if mask.any():
            rows = df[mask][["player_en", "season"]].to_dict("records")
            problems.append(f"{label}: {len(rows)} rows — {rows[:5]}")

    # --- names must match the verified status file
    known = set(status["player_en"]) if "player_en" in status.columns \
        else set(status.iloc[:, 0])
    unknown = sorted(set(df["player_en"]) - known)
    if unknown:
        problems.append(f"names not in kbo_mlb_status.csv: {unknown}")

    # --- duplicates
    dup = df[df.duplicated(["player_en", "season"], keep=False)]
    if len(dup):
        problems.append(f"duplicate player-seasons: "
                        f"{dup[['player_en', 'season']].to_dict('records')}")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("all checks passed")

    # --- plausibility, not errors
    print()
    rates = pd.DataFrame({
        "k_pct": df["so"] / df["pa"],
        "bb_pct": df["bb"] / df["pa"],
        "avg": df["h"] / df["ab"],
        "iso": ((df["h"] + df["double"] + 2 * df["triple"] + 3 * df["hr"])
                / df["ab"]) - (df["h"] / df["ab"]),
    })
    print("derived rates:")
    print(rates.describe().round(3).to_string())

    print()
    print("league totals by season (weighted):")
    by_season = df.groupby("season")[["pa", "so", "bb", "h", "ab"]].sum()
    by_season["k_pct"] = by_season["so"] / by_season["pa"]
    by_season["bb_pct"] = by_season["bb"] / by_season["pa"]
    by_season["avg"] = by_season["h"] / by_season["ab"]
    print(by_season[["pa", "k_pct", "bb_pct", "avg"]].round(3).to_string())


if __name__ == "__main__":
    main()
