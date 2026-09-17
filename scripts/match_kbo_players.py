"""Match KBO foreign hitters to their MLB records.

Three failure modes found and fixed:

1. Accents. The register stores Sócrates, Hernán, Héctor. ASCII search
   returns nothing. Both sides are de-accented before comparison.

2. Namesakes picked by recency. Taking the match with the latest MLB
   season gave Jose Miguel Fernandez a 2026-2026 career (he played in
   KBO from 2019) and Jacob Wilson 2024-2026 (KBO 2019). A player who
   moved to KBO in year Y must have been in MLB shortly BEFORE Y, not
   years after.

3. Multi-generation families. "Mel Rojas" matches the father, a 1990s
   pitcher, as well as the son.

The rule used: among namesakes, pick the one whose MLB career ends
closest to, and not long after, the player's first KBO season.
"""

from __future__ import annotations

import sys
import unicodedata

import pandas as pd

sys.path.insert(0, ".")

HELD_SEASONS = [2021, 2022, 2023, 2024]
# A KBO signing implies recent MLB or AAA service; allow a small overlap
# for players who returned to MLB after their KBO stint.
MAX_YEARS_AFTER_KBO_DEBUT = 4


def deaccent(s) -> str:
    if not isinstance(s, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def load_kbo_debut() -> pd.Series:
    """First KBO season per player, from the roster list."""
    rows = []
    for line in open("data/external/kbo_foreign_hitters_raw.txt", encoding="utf-8"):
        parts = line.strip().split(maxsplit=2)
        if len(parts) == 3:
            rows.append({"season": int(parts[0]), "kbo_name_ko": parts[2]})
    roster = pd.DataFrame(rows)
    return roster.groupby("kbo_name_ko")["season"].min()


def main() -> None:
    names = pd.read_csv("data/external/kbo_name_map.csv")
    debut = load_kbo_debut()
    names["kbo_debut"] = names["kbo_name_ko"].map(debut)
    missing = names["kbo_debut"].isna().sum()
    if missing:
        print(f"WARNING: {missing} names in the map are not in the roster file")

    from pybaseball import chadwick_register

    reg = chadwick_register()
    reg = reg[reg["mlb_played_last"].notna()].copy()
    reg["k_first"] = reg["name_first"].map(deaccent)
    reg["k_last"] = reg["name_last"].map(deaccent)
    print(f"{len(reg):,} players with MLB service in the register")

    rows = []
    for _, r in names.iterrows():
        en = r["name_en"]
        clean = en.replace(" Jr.", "").replace(" Sr.", "")
        parts = clean.split()
        first, last = deaccent(parts[0]), deaccent(parts[-1])
        kbo_year = r["kbo_debut"]

        hit = reg[(reg["k_first"] == first) & (reg["k_last"] == last)].copy()

        if len(hit) and pd.notna(kbo_year):
            # MLB career must end at or before the KBO debut, allowing a
            # few years for players who went back to MLB afterwards.
            hit = hit[hit["mlb_played_last"] <= kbo_year + MAX_YEARS_AFTER_KBO_DEBUT]
            # Closest preceding career wins.
            hit = hit.assign(gap=(kbo_year - hit["mlb_played_last"]).abs())
            hit = hit.sort_values("gap")

        if len(hit) == 0:
            rows.append({"name_en": en, "kbo_debut": kbo_year, "found": False,
                         "key_mlbam": None, "mlb_first": None, "mlb_last": None,
                         "n_matches": 0})
            continue

        best = hit.iloc[0]
        rows.append({
            "name_en": en, "kbo_debut": kbo_year, "found": True,
            "key_mlbam": int(best["key_mlbam"]),
            "mlb_first": best["mlb_played_first"],
            "mlb_last": best["mlb_played_last"],
            "n_matches": len(hit),
        })

    out = pd.DataFrame(rows)
    out["has_held_seasons"] = out["found"] & out["mlb_last"].ge(min(HELD_SEASONS))
    out.to_csv("data/external/kbo_mlb_match.csv", index=False)

    found = out[out["found"]]
    print()
    print(f"found:          {len(found)} / {len(out)}")
    print(f"overlaps 2021+: {out['has_held_seasons'].sum()}")
    print()
    print("NOT FOUND:")
    for _, r in out[~out["found"]].iterrows():
        print(f"  {r['name_en']} (KBO debut {r['kbo_debut']:.0f})")
    print()
    print("still ambiguous:")
    for _, r in found[found["n_matches"] > 1].iterrows():
        print(f"  {r['name_en']}: {r['n_matches']} matches, picked "
              f"{r['mlb_first']:.0f}-{r['mlb_last']:.0f}, KBO {r['kbo_debut']:.0f}")
    print()
    print("MLB last-season distribution of matched players:")
    print(found["mlb_last"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
