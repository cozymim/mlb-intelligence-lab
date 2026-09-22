"""Precompute small artifacts for the dashboard.

Streamlit Cloud cannot host 470 MB of Parquet, and an app that reads raw
pitch data would be unusably slow anyway. This script runs locally,
writes aggregated tables to data/app/, and those are what deploy.

Rule: the dashboard reads ONLY from data/app/. If a page needs something
new, it is added here, not computed in the app.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")

from src.data.player_ids import display_name, load_player_ids
from src.features.batted_ball import add_quality_flags, batted_ball_events
from src.features.plate_discipline import add_discipline_flags
from src.models.batter_score import build_profiles, fit as fit_batter_score, qualified
from src.models.pitcher_score import build_profiles as build_pitcher_profiles
from src.models.pitcher_score import fit as fit_pitcher_score
from src.models.pitcher_score import qualified as qualified_pitchers
from src.utils.pipeline import load_all_snapshots

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("build_app_data")

SEASON = 2024
OUT = Path("data/app")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    logger.info("loading %d", SEASON)
    df = load_all_snapshots(seasons=[SEASON])

    # --- batters
    logger.info("batter profiles")
    prof = build_profiles(df)
    q = qualified(prof)
    score = fit_batter_score(prof)
    q["score"] = score.score(q)

    ids = load_player_ids(q.index.tolist())
    q = q.join(display_name(ids))
    q.to_parquet(OUT / "batters.parquet")
    logger.info("  %d batters", len(q))

    # --- pitchers
    logger.info("pitcher profiles")
    pprof = build_pitcher_profiles(df)
    pq = qualified_pitchers(pprof)
    pscore = fit_pitcher_score(pprof)
    pq["score"] = pscore.score(pq)

    pids = load_player_ids(pq.index.tolist())
    pq = pq.join(display_name(pids))
    pq.to_parquet(OUT / "pitchers.parquet")
    logger.info("  %d pitchers", len(pq))

    # --- scouting splits
    logger.info("scouting splits")
    from src.scouting.batter_report import (
        damage_splits, pitch_type_splits, zone_splits,
    )
    from src.scouting.pitcher_report import pitch_outcomes, usage_by_count

    f = add_discipline_flags(df)
    bbe = add_quality_flags(batted_ball_events(df))

    bsplits, bleague = pitch_type_splits(f)
    zsplits, zleague = zone_splits(f)
    dsplits, dleague = damage_splits(bbe)
    psplits, pleague = pitch_outcomes(f)
    usplits, uleague = usage_by_count(f)

    for name, obj in [
        ("batter_pitch_splits", bsplits), ("batter_pitch_league", bleague),
        ("batter_zone_splits", zsplits), ("batter_zone_league", zleague.to_frame("lg_whiff")),
        ("batter_damage_splits", dsplits), ("batter_damage_league", dleague),
        ("pitcher_outcomes", psplits), ("pitcher_outcome_league", pleague),
        ("pitcher_usage", usplits), ("pitcher_usage_league", uleague.to_frame("lg_pct")),
    ]:
        obj.to_parquet(OUT / f"{name}.parquet")

    # --- KBO translation
    logger.info("kbo translation")
    from src.models.kbo_translation import build_pairs

    kbo = pd.read_csv("data/external/kbo_batting.csv")
    mlb_lines = pd.read_csv("data/external/kbo_players_mlb_lines.csv")
    pairs = build_pairs(kbo, mlb_lines).reset_index()
    pairs.to_parquet(OUT / "kbo_pairs.parquet", index=False)
    kbo.to_parquet(OUT / "kbo_seasons.parquet", index=False)

    prospects = pd.read_csv("data/external/kbo_prospects.csv")
    prospects.to_parquet(OUT / "kbo_prospects.parquet", index=False)
    logger.info("  %d pairs, %d prospect seasons (%d players)",
                len(pairs), len(prospects), prospects["player_en"].nunique())

    total = sum(p.stat().st_size for p in OUT.glob("*.parquet"))
    logger.info("done. %d files, %.1f MB", len(list(OUT.glob("*.parquet"))), total / 1e6)


if __name__ == "__main__":
    main()
