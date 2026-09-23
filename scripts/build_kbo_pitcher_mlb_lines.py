"""MLB season lines for the KBO transition pitchers.

Batters faced, not innings: K% = SO / BF means the same thing for a
starter and a reliever, which is why Day 31 chose per-batter rates for
both sides of the translation.

One batter faced is one plate appearance against that pitcher, so the
existing plate_appearances() logic applies unchanged — only the grouping
key changes from batter to pitcher.
"""

from __future__ import annotations

import logging
import sys

import pandas as pd

sys.path.insert(0, ".")

from src.data.validation import plate_appearances
from src.utils.pipeline import load_all_snapshots

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("kbo_pitcher_mlb")

SEASONS = list(range(2014, 2025))


def season_lines(pa: pd.DataFrame) -> pd.DataFrame:
    g = pa.groupby("pitcher")["events"]
    return pd.DataFrame({
        "bf": g.size(),
        "so": g.apply(lambda s: s.isin({"strikeout", "strikeout_double_play"}).sum()),
        "bb": g.apply(lambda s: s.isin({"walk", "intent_walk"}).sum()),
        "ibb": g.apply(lambda s: (s == "intent_walk").sum()),
        "h": g.apply(lambda s: s.isin({"single", "double", "triple", "home_run"}).sum()),
        "hr": g.apply(lambda s: (s == "home_run").sum()),
        "hbp": g.apply(lambda s: (s == "hit_by_pitch").sum()),
    })


def main() -> None:
    kbo = pd.read_csv("data/external/kbo_pitching.csv")
    ids = pd.read_csv("data/external/kbo_pitchers_match.csv")
    ids = ids[ids["key_mlbam"].notna()]

    wanted_names = set(kbo["player_en"])
    sub = ids[ids["player_en"].isin(wanted_names)]
    id_to_name = dict(zip(sub["key_mlbam"].astype(int), sub["player_en"]))
    logger.info("%d of %d KBO pitchers have an MLBAM id",
                len(id_to_name), len(wanted_names))

    frames = []
    for season in SEASONS:
        df = load_all_snapshots(seasons=[season])
        df = df[df["pitcher"].isin(id_to_name)]
        if len(df) == 0:
            continue
        pa = plate_appearances(df)
        lines = season_lines(pa).reset_index()
        lines["season"] = season
        frames.append(lines)
        logger.info("%d: %d pitchers, %d BF", season, len(lines), lines["bf"].sum())

    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "player_en", out["pitcher"].map(id_to_name))
    out = out.rename(columns={"pitcher": "key_mlbam"})
    out.to_csv("data/external/kbo_pitchers_mlb_lines.csv", index=False)

    logger.info("done: %d pitcher-seasons, %d of %d pitchers have MLB BF",
                len(out), out["player_en"].nunique(), len(wanted_names))
    missing = sorted(wanted_names - set(out["player_en"]))
    if missing:
        logger.info("no MLB appearances in 2014-2024: %s", missing)


if __name__ == "__main__":
    main()
