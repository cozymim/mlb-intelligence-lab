"""Validate manually entered KBO pitching lines.

Mirrors the batting validator with pitcher identities. The key quantity
is bf (batters faced): K% = SO / BF, not K/9. Day 31 chose per-batter
rates precisely because they mean the same thing for a starter and a
reliever, so the same translation model covers both.
"""

from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, ".")

REQUIRED = ["bf", "so", "bb"]
OPTIONAL = ["g", "gs", "ip", "h", "hr", "ibb", "hbp", "er"]


def main() -> None:
    df = pd.read_csv("data/external/kbo_pitching.csv")
    filled = df[df["bf"].notna() & (df["bf"] != "")]

    print(f"{len(df)} rows, {len(filled)} filled "
          f"({filled['player_en'].nunique()} pitchers)")
    if len(filled) == 0:
        print("\nnothing to validate yet")
        return

    for c in REQUIRED + OPTIONAL:
        filled[c] = pd.to_numeric(filled[c], errors="coerce")

    problems = []

    missing = filled[filled[REQUIRED].isna().any(axis=1)]
    if len(missing):
        problems.append(
            f"rows missing a required field: "
            f"{missing[['player_en', 'season']].to_dict('records')}")

    checks = [
        ("so > bf", filled["so"] > filled["bf"]),
        ("bb > bf", filled["bb"] > filled["bf"]),
        ("h > bf", filled["h"] > filled["bf"]),
        ("hr > h", filled["hr"] > filled["h"]),
        ("ibb > bb", filled["ibb"] > filled["bb"]),
        ("gs > g", filled["gs"] > filled["g"]),
        # A batter faced ends in a hit, walk, HBP, or an out. SO+BB+H+HBP
        # cannot exceed BF.
        ("SO+BB+H+HBP > BF",
         filled[["so", "bb", "h", "hbp"]].sum(axis=1) > filled["bf"]),
    ]
    for label, mask in checks:
        m = mask.fillna(False)
        if m.any():
            problems.append(
                f"{label}: {filled[m][['player_en', 'season']].to_dict('records')}")

    # BF should be roughly 4.3 per inning; far outside that is a typo
    if filled["ip"].notna().any():
        ipf = filled[filled["ip"].notna() & (filled["ip"] > 0)]
        ratio = ipf["bf"] / ipf["ip"]
        odd = ipf[(ratio < 3.5) | (ratio > 5.5)]
        if len(odd):
            problems.append(
                f"BF/IP outside 3.5-5.5 (typical is ~4.3): "
                f"{odd[['player_en', 'season']].to_dict('records')}")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("all checks passed")

    print()
    career = filled.groupby("player_en")[["bf", "so", "bb"]].sum()
    career["k_pct"] = career["so"] / career["bf"]
    career["bb_pct"] = career["bb"] / career["bf"]
    print("career KBO rates:")
    print(career.sort_values("k_pct", ascending=False).round(3).to_string())

    if filled["gs"].notna().any():
        print()
        role = filled.groupby("player_en")[["g", "gs"]].sum()
        role["starter_pct"] = role["gs"] / role["g"]
        n_start = (role["starter_pct"] > 0.5).sum()
        print(f"predominantly starters: {n_start} / {len(role)}")


if __name__ == "__main__":
    main()
