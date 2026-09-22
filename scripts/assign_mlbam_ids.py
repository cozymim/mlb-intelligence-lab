"""Assign MLBAM ids to the 81 KBO foreign hitters with verified MLB records.

The Day 43 automated matcher required the MLB career to END near the KBO
debut. That excluded Eric Thames, Darin Ruf and Christian Bethancourt —
players who went to KBO and then RETURNED to MLB. Those are the most
valuable observations in the study: the same player measured in both
leagues, in both directions.

Every name here was verified by hand as having MLB service
(kbo_mlb_status.csv). So the question is no longer "did he play in MLB"
but "which namesake is he". Rule: the MLB career must fall within ten
years either side of his KBO seasons.
"""

from __future__ import annotations

import sys
import unicodedata

import pandas as pd

sys.path.insert(0, ".")

WINDOW_YEARS = 10


def deaccent(s) -> str:
    if not isinstance(s, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def main() -> None:
    status = pd.read_csv("data/external/kbo_mlb_status.csv")
    status = status[status["mlb_record"] == "yes"]

    kbo = pd.read_csv("data/external/kbo_batting.csv")
    span = kbo.groupby("player_en")["season"].agg(["min", "max"])

    from pybaseball import chadwick_register
    reg = chadwick_register()
    reg = reg[reg["mlb_played_last"].notna()].copy()
    reg["k_first"] = reg["name_first"].map(deaccent)
    reg["k_last"] = reg["name_last"].map(deaccent)

    rows = []
    for name in status["name_en"]:
        clean = name.replace(" Jr.", "").replace(" Sr.", "")
        # Everything after the first token is the surname. Taking only the
        # final token broke multi-word surnames: "Scott Van Slyke" was
        # searched as last name "Slyke" and found nothing.
        parts = clean.split()
        first, last = deaccent(parts[0]), deaccent(" ".join(parts[1:]))

        cand = reg[(reg["k_first"] == first) & (reg["k_last"] == last)].copy()

        if name in span.index:
            lo, hi = span.loc[name, "min"], span.loc[name, "max"]
            cand = cand[(cand["mlb_played_last"] >= lo - WINDOW_YEARS)
                        & (cand["mlb_played_first"] <= hi + WINDOW_YEARS)]

        rows.append({
            "player_en": name,
            "n_candidates": len(cand),
            "key_mlbam": int(cand.iloc[0]["key_mlbam"]) if len(cand) == 1 else None,
            "mlb_first": cand.iloc[0]["mlb_played_first"] if len(cand) == 1 else None,
            "mlb_last": cand.iloc[0]["mlb_played_last"] if len(cand) == 1 else None,
            "kbo_first": span.loc[name, "min"] if name in span.index else None,
            "kbo_last": span.loc[name, "max"] if name in span.index else None,
            "candidates": "; ".join(
                f"{int(r.key_mlbam)} ({r.mlb_played_first:.0f}-{r.mlb_played_last:.0f})"
                for r in cand.itertuples()),
        })

    out = pd.DataFrame(rows)
    out.to_csv("data/external/kbo_mlbam_ids.csv", index=False)

    ok = out[out["n_candidates"] == 1]
    none = out[out["n_candidates"] == 0]
    many = out[out["n_candidates"] > 1]

    print(f"resolved uniquely: {len(ok)} / {len(out)}")
    print()
    if len(none):
        print(f"NO CANDIDATE ({len(none)}) — check spelling against the register:")
        for _, r in none.iterrows():
            print(f"  {r['player_en']}  (KBO {r['kbo_first']:.0f}-{r['kbo_last']:.0f})")
        print()
    if len(many):
        print(f"AMBIGUOUS ({len(many)}) — pick the right one by hand:")
        for _, r in many.iterrows():
            print(f"  {r['player_en']}  (KBO {r['kbo_first']:.0f}-{r['kbo_last']:.0f})")
            print(f"    {r['candidates']}")
        print()

    back = ok[ok["mlb_last"] > ok["kbo_last"]]
    print(f"returned to MLB after KBO: {len(back)}")
    for _, r in back.iterrows():
        print(f"  {r['player_en']}: KBO {r['kbo_first']:.0f}-{r['kbo_last']:.0f}, "
              f"MLB {r['mlb_first']:.0f}-{r['mlb_last']:.0f}")


if __name__ == "__main__":
    main()
