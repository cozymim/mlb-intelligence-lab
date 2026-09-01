import pandas as pd
import pytest

from src.utils.leakage import (
    DEAD_COLUMNS,
    NON_FEATURE_COLUMNS,
    POST_PITCH_COLUMNS,
    LeakageError,
    banned_for_pitch_outcome,
    check_features,
    describe_exclusions,
    safe_features,
)


def test_the_obvious_leaks_are_banned():
    banned = banned_for_pitch_outcome()
    for col in ["launch_speed", "events", "description",
                "estimated_woba_using_speedangle", "delta_run_exp"]:
        assert col in banned


def test_legitimate_pre_pitch_features_are_not_banned():
    """These are all knowable at release and must stay available."""
    banned = banned_for_pitch_outcome()
    for col in ["release_speed", "pfx_x", "pfx_z", "plate_x", "plate_z",
                "balls", "strikes", "pitch_type", "stand", "p_throws",
                "outs_when_up", "inning", "release_spin_rate"]:
        assert col not in banned


def test_check_raises_on_a_leaked_column():
    with pytest.raises(LeakageError, match="launch_speed"):
        check_features(["release_speed", "launch_speed"],
                       banned_for_pitch_outcome())


def test_check_passes_on_a_clean_matrix():
    check_features(["release_speed", "plate_x", "balls"],
                   banned_for_pitch_outcome())


def test_error_message_names_every_offender():
    with pytest.raises(LeakageError) as exc:
        check_features(["launch_speed", "events", "release_speed"],
                       banned_for_pitch_outcome())
    assert "launch_speed" in str(exc.value)
    assert "events" in str(exc.value)


def test_safe_features_drops_and_keeps_the_right_columns():
    df = pd.DataFrame({
        "release_speed": [95.0],
        "plate_x": [0.1],
        "launch_speed": [102.0],
        "events": ["single"],
        "game_pk": [1],
    })
    out = safe_features(df, banned_for_pitch_outcome())
    assert list(out.columns) == ["release_speed", "plate_x"]


def test_safe_features_does_not_mutate_the_input():
    df = pd.DataFrame({"release_speed": [95.0], "launch_speed": [102.0]})
    before = list(df.columns)
    safe_features(df, banned_for_pitch_outcome())
    assert list(df.columns) == before


def test_exclusion_reasons_are_distinct():
    df = pd.DataFrame({
        "launch_speed": [1], "game_pk": [1], "umpire": [None],
        "release_speed": [95.0],
    })
    out = describe_exclusions(df, banned_for_pitch_outcome())
    reasons = dict(zip(out["column"], out["reason"]))

    assert "post-outcome" in reasons["launch_speed"]
    assert "identifier" in reasons["game_pk"]
    assert "empty" in reasons["umpire"]
    assert "release_speed" not in reasons   # legal feature, not excluded


def test_the_three_sets_do_not_overlap():
    """Overlap would make exclusion reasons ambiguous."""
    assert POST_PITCH_COLUMNS.isdisjoint(NON_FEATURE_COLUMNS)
    assert POST_PITCH_COLUMNS.isdisjoint(DEAD_COLUMNS)
    assert NON_FEATURE_COLUMNS.isdisjoint(DEAD_COLUMNS)
