"""Validate the current-KBO prospect lines.

Same baseball identities as the transition file, minus the MLB name
check — these players have no MLB record, which is the entire point of
projecting them.
"""

from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, ".")

COUNT_COLS = ["pa", "ab", "h", "double", "triple", "hr",
              "bb", "ibb", "so", "hbp", "sf"]


def main() -> None:
    df = pd.read_csv("data/external/kbo_prospects.csv")
    roster = pd.read_csv("data/external/kbo_prospects_roster.txt",
                         names=["player_en", "player_ko", "team"])

    print(f"{len(df)} player-seasons, {df['player_en'].nunique()} players")
    print(f"seasons: {sorted(df['season'].unique())}")

    problems = []

    for c in COUNT_COLS:
        if c not in df.columns:
            problems.append(f"missing column: {c}")
        elif (df[c] < 0).any():
            problems.append(f"{c}: negative values")

    checks = [
        ("ab > pa", df["ab"] > df["pa"]),
        ("h > ab", df["h"] > df["ab"]),
        ("so > pa", df["so"] > df["pa"]),
        ("ibb > bb", df["ibb"] > df["bb"]),
        ("2B+3B+HR > H", df["double"] + df["triple"] + df["hr"] > df["h"]),
        ("AB+BB+HBP+SF > PA",
         df["ab"] + df["bb"] + df["hbp"] + df["sf"] > df["pa"]),
    ]
    for label, mask in checks:
        if mask.any():
            problems.append(f"{label}: {df[mask][['player_en','season']].to_dict('records')}")

    missing = sorted(set(roster["player_en"]) - set(df["player_en"]))
    extra = sorted(set(df["player_en"]) - set(roster["player_en"]))
    if missing:
        problems.append(f"in roster but no lines: {missing}")
    if extra:
        problems.append(f"lines but not in roster: {extra}")

    dup = df[df.duplicated(["player_en", "season"], keep=False)]
    if len(dup):
        problems.append(f"duplicates: {dup[['player_en','season']].to_dict('records')}")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("all checks passed")

    print()
    career = df.groupby("player_en")[["pa", "so"]].sum()
    career["k_pct"] = career["so"] / career["pa"]
    print("career totals (2023-2025):")
    print(career.sort_values("k_pct").round(3).to_string())

    print()
    print(f"seasons per player: {df.groupby('player_en').size().value_counts().to_dict()}")
    low = career[career["pa"] < 300]
    if len(low):
        print(f"\nunder 300 career PA ({len(low)}) — projections will be wide:")
        print("  " + ", ".join(low.index))


if __name__ == "__main__":
    main()
