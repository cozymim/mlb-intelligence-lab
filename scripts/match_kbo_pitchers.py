"""Match KBO foreign pitchers to MLB records.

Reuses the lessons from the batter pass (Day 43-44):

  1. The register stores accented names (José, Héctor). De-accent both
     sides before comparing.
  2. Multi-word surnames exist ("Van Slyke" was searched as "Slyke" and
     found nothing). Treat everything after the first token as surname,
     but ALSO try last-token-only, since some names parse either way.
  3. Namesakes: require the MLB career to overlap a window around the
     KBO seasons.
  4. **Do not require the MLB career to END before KBO.** Merrill Kelly,
     Brooks Raley, Casey Kelly and Josh Lindblom pitched in KBO and then
     returned to MLB. Those are the most informative observations in the
     study — the same pitcher measured in both leagues.
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
    roster = pd.read_csv("data/external/kbo_foreign_pitchers_roster.csv")
    span = roster.groupby("player_en")["season"].agg(["min", "max"])
    print(f"{len(roster)} pitcher-seasons, {len(span)} unique pitchers")

    from pybaseball import chadwick_register
    reg = chadwick_register()
    reg = reg[reg["mlb_played_last"].notna()].copy()
    reg["k_first"] = reg["name_first"].map(deaccent)
    reg["k_last"] = reg["name_last"].map(deaccent)
    print(f"{len(reg):,} players with MLB service in the register")

    rows = []
    for name, (lo, hi) in span.iterrows():
        clean = str(name).replace(" Jr.", "").replace(" Sr.", "")
        parts = clean.split()
        first = deaccent(parts[0])

        # Try full surname first, then last token only.
        cand = pd.DataFrame()
        for last in [deaccent(" ".join(parts[1:])), deaccent(parts[-1])]:
            c = reg[(reg["k_first"] == first) & (reg["k_last"] == last)]
            c = c[(c["mlb_played_last"] >= lo - WINDOW_YEARS)
                  & (c["mlb_played_first"] <= hi + WINDOW_YEARS)]
            if len(c):
                cand = c
                break

        rows.append({
            "player_en": name,
            "kbo_first": lo, "kbo_last": hi,
            "kbo_seasons": int((roster["player_en"] == name).sum()),
            "n_candidates": len(cand),
            "key_mlbam": int(cand.iloc[0]["key_mlbam"]) if len(cand) == 1 else None,
            "mlb_first": cand.iloc[0]["mlb_played_first"] if len(cand) == 1 else None,
            "mlb_last": cand.iloc[0]["mlb_played_last"] if len(cand) == 1 else None,
            "candidates": "; ".join(
                f"{int(r.key_mlbam)} ({r.mlb_played_first:.0f}-{r.mlb_played_last:.0f})"
                for r in cand.itertuples()),
        })

    out = pd.DataFrame(rows)
    out.to_csv("data/external/kbo_pitchers_match.csv", index=False)

    ok = out[out["n_candidates"] == 1]
    none = out[out["n_candidates"] == 0]
    many = out[out["n_candidates"] > 1]

    print()
    print(f"resolved uniquely: {len(ok)} / {len(out)}")
    print(f"no candidate:      {len(none)}")
    print(f"ambiguous:         {len(many)}")
    print()
    if len(none):
        print("NO CANDIDATE — likely never pitched in MLB, or spelling differs:")
        for _, r in none.iterrows():
            print(f"  {r['player_en']}  (KBO {r['kbo_first']}-{r['kbo_last']}, "
                  f"{r['kbo_seasons']} seasons)")
        print()
    if len(many):
        print("AMBIGUOUS — pick by hand:")
        for _, r in many.iterrows():
            print(f"  {r['player_en']}  (KBO {r['kbo_first']}-{r['kbo_last']})")
            print(f"    {r['candidates']}")
        print()

    back = ok[ok["mlb_last"] > ok["kbo_last"]]
    print(f"returned to MLB after KBO: {len(back)}")
    for _, r in back.sort_values("kbo_seasons", ascending=False).iterrows():
        print(f"  {r['player_en']}: KBO {r['kbo_first']}-{r['kbo_last']} "
              f"({r['kbo_seasons']} seasons), MLB {r['mlb_first']:.0f}-{r['mlb_last']:.0f}")


if __name__ == "__main__":
    main()
