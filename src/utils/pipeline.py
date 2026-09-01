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


def load_all_snapshots(root: Path | None = None) -> pd.DataFrame:
    """Every raw snapshot, concatenated and sorted into pitch order.

    When a game date has several snapshots (Statcast revises data), the
    most recent ingestion wins.
    """
    root = root or project_root()
    raw = root / "data" / "raw"

    newest_by_date: dict[str, Path] = {}
    for path in sorted(raw.glob("statcast_*.parquet")):
        game_date = path.name.split("_")[1]
        newest_by_date[game_date] = path   # sorted order means later wins

    if not newest_by_date:
        raise FileNotFoundError(f"no snapshots found in {raw}")

    frames = [pd.read_parquet(p) for p in newest_by_date.values()]
    df = pd.concat(frames, ignore_index=True)
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
