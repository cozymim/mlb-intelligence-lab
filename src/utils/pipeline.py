"""Wire the guards together in the one correct order.

Order matters and is not obvious:

    1. load snapshots
    2. sort chronologically      (Statcast is not in pitch order)
    3. split by date             (needs game_date, which the guard drops)
    4. apply feature guards      (per partition, after splitting)

Applying guards before splitting removes `game_date` and makes temporal
splitting impossible. Splitting before sorting is harmless here because
the split is by date rather than position, but sorting first keeps every
downstream shift() and rolling operation honest.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.ingestion.statcast_client import project_root
from src.data.validation import check_first_pitch_counts, sort_chronologically
from src.utils.leakage import check_features, safe_features
from src.utils.temporal import TemporalSplit, split_by_date


# Columns that must be numeric. Skipping empty snapshots removes the
# known cause of object-dtype promotion, but this is the second line of
# defence against causes not yet seen (a partially-null column, an
# upstream schema change).
NUMERIC_COLUMNS = [
    "plate_x", "plate_z", "sz_top", "sz_bot", "zone",
    "release_speed", "release_pos_x", "release_pos_z",
    "release_spin_rate", "release_extension", "effective_speed",
    "pfx_x", "pfx_z", "spin_axis",
    "launch_speed", "launch_angle", "hit_distance_sc",
    "balls", "strikes", "outs_when_up", "inning",
    "at_bat_number", "pitch_number", "game_pk",
    "estimated_ba_using_speedangle",
    "estimated_slg_using_speedangle",
    "estimated_woba_using_speedangle",
    "woba_value", "woba_denom", "babip_value", "iso_value",
    "delta_run_exp", "delta_home_win_exp",
]


def coerce_numeric(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Force known-numeric columns to a numeric dtype.

    errors="coerce" turns unparseable values into NaN rather than
    raising. That is deliberate: the alternative is a silent object
    column that breaks aggregation much later, far from the cause. The
    risk of quiet data loss is covered by a test.
    """
    out = df.copy()
    for col in (columns or NUMERIC_COLUMNS):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def load_all_snapshots(root: Path | None = None,
                       seasons: list[int] | None = None) -> pd.DataFrame:
    """Every raw snapshot, concatenated and sorted into pitch order.

    When a game date has several snapshots (Statcast revises data), the
    most recent ingestion wins.
    """
    root = root or project_root()
    raw = root / "data" / "raw"

    newest_by_date: dict[str, Path] = {}
    for path in sorted(raw.glob("statcast_*.parquet")):
        game_date = path.name.split("_")[1]
        if seasons is not None and int(game_date[:4]) not in seasons:
            continue
        newest_by_date[game_date] = path   # sorted order means later wins

    if not newest_by_date:
        raise FileNotFoundError(f"no snapshots found in {raw}")

    # Empty snapshots (days with no games, e.g. the All-Star break) are
    # stored with object dtype because pandas cannot infer types from
    # zero rows. Concatenating them promotes every numeric column to
    # object across the whole dataset — 4 empty files corrupted 182 good
    # ones before this was caught. Skip them.
    frames = [f for f in (pd.read_parquet(p) for p in newest_by_date.values())
              if len(f) > 0]
    if not frames:
        raise ValueError("all snapshots are empty")
    df = pd.concat(frames, ignore_index=True)
    df = coerce_numeric(df)
    return sort_chronologically(df)


def prepare_split(
    df: pd.DataFrame,
    train_end: str,
    validation_end: str,
    banned: frozenset[str],
    context: str = "model",
) -> tuple[TemporalSplit, dict[str, pd.DataFrame]]:
    """Split chronologically, then strip banned columns from each partition.

    Returns the split (which retains game_date for the model card) and a
    dict of guarded feature matrices ready for fitting.
    """
    check_first_pitch_counts(df)

    split = split_by_date(df, train_end=train_end, validation_end=validation_end)

    features = {}
    for name, part in [("train", split.train),
                       ("validation", split.validation),
                       ("test", split.test)]:
        guarded = safe_features(part, banned, context=f"{context}/{name}")
        check_features(guarded.columns, banned, context=f"{context}/{name}")
        features[name] = guarded

    return split, features
