import pandas as pd

from src.features.batted_ball import (
    add_quality_flags,
    batted_ball_events,
    quality_profile,
)


def rows(specs):
    """specs: list of (description, launch_speed, launch_angle, lsa)."""
    return pd.DataFrame({
        "description": [s[0] for s in specs],
        "launch_speed": [s[1] for s in specs],
        "launch_angle": [s[2] for s in specs],
        "launch_speed_angle": [s[3] for s in specs],
    })


def test_fouls_are_excluded_from_batted_ball_events():
    """Fouls carry a launch_speed but are not BBE. Including them
    collapsed league HardHit% from 39.0% to 23.8%."""
    df = rows([
        ("hit_into_play", 100.0, 25.0, 6),
        ("foul", 70.0, -5.0, None),
        ("swinging_strike", None, None, None),
    ])
    assert len(batted_ball_events(df)) == 1


def test_hard_hit_threshold_is_95():
    df = rows([
        ("hit_into_play", 95.0, 20.0, 5),
        ("hit_into_play", 94.9, 20.0, 4),
    ])
    flags = add_quality_flags(batted_ball_events(df))
    assert flags["is_hard_hit"].tolist() == [True, False]


def test_sweet_spot_is_8_to_32_degrees():
    df = rows([
        ("hit_into_play", 90.0, 8.0, 4),
        ("hit_into_play", 90.0, 32.0, 4),
        ("hit_into_play", 90.0, 7.9, 4),
        ("hit_into_play", 90.0, 32.1, 4),
    ])
    flags = add_quality_flags(batted_ball_events(df))
    assert flags["is_sweet_spot"].tolist() == [True, True, False, False]


def test_barrel_comes_from_statcast_not_our_arithmetic():
    """We do not reimplement the barrel band; code 6 is authoritative."""
    df = rows([
        ("hit_into_play", 104.0, 35.0, 6),
        ("hit_into_play", 104.0, 35.0, 5),
    ])
    flags = add_quality_flags(batted_ball_events(df))
    assert flags["is_barrel"].tolist() == [True, False]


def test_barrels_are_not_a_subset_of_sweet_spot():
    """Verified on 2024 data: 1,306 of 9,698 barrels (13.5%) fall outside
    8-32 degrees, because the qualifying band widens with exit velocity."""
    df = rows([("hit_into_play", 110.0, 40.0, 6)])
    flags = add_quality_flags(batted_ball_events(df))
    assert flags["is_barrel"].iloc[0]
    assert not flags["is_sweet_spot"].iloc[0]


def test_profile_reports_sample_size_and_flags_small_samples():
    df = rows([("hit_into_play", 100.0, 25.0, 6)])
    assert quality_profile(df)["bbe"] == 1
    assert quality_profile(df, min_bbe=50)["insufficient_sample"] is True


def test_empty_input_does_not_crash():
    df = rows([("swinging_strike", None, None, None)])
    assert quality_profile(df)["insufficient_sample"] is True
