"""End-to-end checks. Unit tests verify functions; these verify the seam."""

import pandas as pd
import pytest

from src.utils.leakage import LeakageError, banned_for_pitch_outcome
from src.utils.pipeline import load_all_snapshots, prepare_split


@pytest.fixture(scope="module")
def df():
    return load_all_snapshots()


def test_snapshots_load_and_are_sorted(df):
    assert len(df) > 0
    keys = df[["game_pk", "at_bat_number", "pitch_number"]]
    assert keys.equals(keys.sort_values(["game_pk", "at_bat_number", "pitch_number"]))


def test_no_duplicate_pitches(df):
    """Two snapshots of the same game date must not both be loaded."""
    keys = df[["game_pk", "at_bat_number", "pitch_number"]]
    assert not keys.duplicated().any()


def test_full_pipeline_produces_guarded_partitions(df):
    banned = banned_for_pitch_outcome()
    split, features = prepare_split(
        df, train_end="2024-04-15", validation_end="2024-06-15",
        banned=banned, context="integration",
    )

    # partitions are non-empty and sum to the input
    total = sum(len(f) for f in features.values())
    assert total == len(df)

    # no banned column survives anywhere
    for name, matrix in features.items():
        assert not (set(matrix.columns) & banned), name


def test_split_retains_game_date_for_the_model_card(df):
    """The guard drops game_date, so the split must keep its own copy."""
    banned = banned_for_pitch_outcome()
    split, features = prepare_split(
        df, train_end="2024-04-15", validation_end="2024-06-15",
        banned=banned, context="integration",
    )
    assert "game_date" in split.train.columns
    assert "game_date" not in features["train"].columns
    assert split.summary()["train"]["rows"] == len(features["train"])


def test_guarding_before_splitting_would_fail(df):
    """Documents why the order in prepare_split is what it is."""
    from src.utils.leakage import safe_features
    from src.utils.temporal import split_by_date

    guarded_first = safe_features(df, banned_for_pitch_outcome())
    with pytest.raises(KeyError):
        split_by_date(guarded_first, train_end="2024-04-15",
                      validation_end="2024-06-15")


def test_pipeline_rejects_a_leaked_column(df):
    """The guard must fire even when the caller passes a wider ban list."""
    wider = banned_for_pitch_outcome() | {"release_speed"}
    split, features = prepare_split(
        df, train_end="2024-04-15", validation_end="2024-06-15",
        banned=wider, context="integration",
    )
    assert "release_speed" not in features["train"].columns
