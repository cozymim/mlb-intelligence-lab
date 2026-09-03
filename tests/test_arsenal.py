import numpy as np
import pandas as pd
import pytest

from src.features.arsenal import (
    arm_side_movement,
    arsenal_depth,
    build_arsenal,
    primary_fastball,
    separation,
)


def pitches(specs):
    """specs: list of (pitcher, p_throws, pitch_type, velo, pfx_x, pfx_z)."""
    return pd.DataFrame({
        "pitcher": [s[0] for s in specs],
        "p_throws": [s[1] for s in specs],
        "pitch_type": [s[2] for s in specs],
        "release_speed": [s[3] for s in specs],
        "pfx_x": [s[4] for s in specs],
        "pfx_z": [s[5] for s in specs],
        "release_spin_rate": [2200] * len(specs),
        "release_extension": [6.5] * len(specs),
    })


def test_left_handers_are_flipped_and_right_handers_are_not():
    """Verified league-wide: LHP changeup +1.18, RHP changeup -1.18."""
    df = pitches([
        (1, "R", "CH", 85.0, -1.18, 0.4),
        (2, "L", "CH", 85.0, 1.18, 0.4),
    ])
    out = arm_side_movement(df)
    assert out.iloc[0] == pytest.approx(-1.18)
    assert out.iloc[1] == pytest.approx(-1.18)


def test_arm_side_movement_returns_float64():
    df = pitches([(1, "R", "CH", 85.0, -1.18, 0.4)])
    df["pfx_x"] = df["pfx_x"].astype("Float64")
    assert arm_side_movement(df).dtype == "float64"


def test_rare_pitch_types_are_dropped():
    specs = [(1, "R", "FF", 95.0, -0.6, 1.3)] * 60 + [(1, "R", "EP", 60.0, 0.0, 0.0)] * 3
    a = build_arsenal(pitches(specs), min_pitches=50)
    assert "FF" in a.loc[1].index
    assert "EP" not in a.loc[1].index


def test_usage_uses_all_pitches_as_the_denominator():
    """Dropping rare types must not inflate the usage of common ones."""
    specs = [(1, "R", "FF", 95.0, -0.6, 1.3)] * 60 + [(1, "R", "EP", 60.0, 0.0, 0.0)] * 40
    a = build_arsenal(pitches(specs), min_pitches=50)
    assert a.loc[(1, "FF"), "usage"] == pytest.approx(0.6)


def test_primary_fastball_is_the_most_used_one():
    specs = (
        [(1, "R", "FF", 95.0, -0.6, 1.3)] * 60
        + [(1, "R", "SI", 93.0, -1.2, 0.6)] * 100
    )
    a = build_arsenal(pitches(specs))
    assert primary_fastball(a, 1) == "SI"


def test_no_fastball_returns_none():
    specs = [(1, "R", "SL", 85.0, 0.4, 0.1)] * 60
    a = build_arsenal(pitches(specs))
    assert primary_fastball(a, 1) is None
    assert separation(a, 1) is None


def test_separation_measures_velocity_and_movement_independently():
    """A pitch can separate a lot in speed and little in shape."""
    specs = (
        [(1, "R", "FF", 95.0, -0.6, 1.3)] * 60
        + [(1, "R", "CH", 84.4, -0.7, 1.0)] * 60   # 10.6 mph, tiny shape gap
    )
    a = build_arsenal(pitches(specs))
    sep = separation(a, 1).set_index("pitch")

    assert sep.loc["CH", "velo_gap"] == pytest.approx(10.6, abs=0.01)
    assert sep.loc["CH", "move_gap"] < 0.35


def test_depth_counts_distinct_pitch_types():
    specs = (
        [(1, "R", "FF", 95.0, -0.6, 1.3)] * 300
        + [(1, "R", "SL", 85.0, 0.4, 0.1)] * 200
        + [(2, "R", "FC", 92.0, 0.2, 0.7)] * 600
    )
    d = arsenal_depth(build_arsenal(pitches(specs)), min_total=500)
    assert d.loc[1, "n_pitch_types"] == 2
    assert d.loc[2, "n_pitch_types"] == 1
