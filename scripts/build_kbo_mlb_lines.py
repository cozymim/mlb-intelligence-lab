"""MLB season lines for the 81 KBO foreign hitters, in the KBO file's schema.

Loads one season at a time and filters to the 81 ids immediately. The
full 2014-2024 holdings are over a gigabyte; loading them together is
unnecessary when only 81 batters matter.

Definitions are matched to the KBO box-score convention, because a
translation factor between two differently-defined quantities is
meaningless:
  - bb INCLUDES intentional walks (the KBO file satisfies ibb <= bb);
    ibb is recorded separately so BB% can exclude it on both sides
  - ab excludes walks, HBP, sacrifices, interference, truncated PAs
"""

from __future__ import annotations

import logging
import sys

import pandas as pd

sys.path.insert(0, ".")

from src.data.validation import plate_appearances
from src.utils.pipeline import load_all_snapshots

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("kbo_mlb_lines")

SEASONS = list(range(2014, 2025))

HITS = {"single", "double", "triple", "home_run"}
SAC_FLY = {"sac_fly", "sac_fly_double_play"}
NON_AB = {"walk", "intent_walk", "hit_by_pitch", "catcher_interf",
          "truncated_pa", "sac_bunt", "sac_bunt_double_play"} | SAC_FLY


def season_lines(pa: pd.DataFrame) -> pd.DataFrame:
    g = pa.groupby("batter")["events"]
    return pd.DataFrame({
        "pa": g.size(),
        "ab": g.apply(lambda s: (~s.isin(NON_AB)).sum()),
        "h": g.apply(lambda s: s.isin(HITS).sum()),
        "double": g.apply(lambda s: (s == "double").sum()),
        "triple": g.apply(lambda s: (s == "triple").sum()),
        "hr": g.apply(lambda s: (s == "home_run").sum()),
        "bb": g.apply(lambda s: s.isin({"walk", "intent_walk"}).sum()),
        "ibb": g.apply(lambda s: (s == "intent_walk").sum()),
        "so": g.apply(lambda s: s.isin({"strikeout", "strikeout_double_play"}).sum()),
        "hbp": g.apply(lambda s: (s == "hit_by_pitch").sum()),
        "sf": g.apply(lambda s: s.isin(SAC_FLY).sum()),
    })


def main() -> None:
    ids = pd.read_csv("data/external/kbo_mlbam_ids.csv")
    id_to_name = dict(zip(ids["key_mlbam"].astype(int), ids["player_en"]))
    wanted = set(id_to_name)

    frames = []
    for season in SEASONS:
        df = load_all_snapshots(seasons=[season])
        df = df[df["batter"].isin(wanted)]
        if len(df) == 0:
            logger.info("%d: none of the 81 batted", season)
            continue
        pa = plate_appearances(df)
        lines = season_lines(pa).reset_index()
        lines["season"] = season
        frames.append(lines)
        logger.info("%d: %d players, %d PA", season, len(lines), lines["pa"].sum())

    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "player_en", out["batter"].map(id_to_name))
    out = out.rename(columns={"batter": "key_mlbam"})
    out.to_csv("data/external/kbo_players_mlb_lines.csv", index=False)

    covered = out["player_en"].nunique()
    logger.info("done: %d player-seasons, %d of %d players have MLB PA in 2014-2024",
                len(out), covered, len(wanted))
    missing = sorted(set(id_to_name.values()) - set(out["player_en"]))
    if missing:
        logger.info("no MLB PA in held seasons: %s", missing)


if __name__ == "__main__":
    main()
