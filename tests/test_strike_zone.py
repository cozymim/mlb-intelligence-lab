import pandas as pd

from src.features.strike_zone import (
    BALL_RADIUS_FT,
    HALF_PLATE_FT,
    add_zone_flag,
    in_strike_zone,
)


def frame(plate_x, plate_z, sz_top=3.4, sz_bot=1.6):
    return pd.DataFrame({
        "plate_x": [plate_x], "plate_z": [plate_z],
        "sz_top": [sz_top], "sz_bot": [sz_bot],
    })


def test_middle_of_the_zone_is_in():
    assert in_strike_zone(frame(0.0, 2.5)).iloc[0]


def test_well_outside_is_out():
    assert not in_strike_zone(frame(2.0, 2.5)).iloc[0]
    assert not in_strike_zone(frame(0.0, 6.0)).iloc[0]


def test_ball_touching_the_top_edge_is_in():
    """Any part of the ball in the zone is a strike."""
    assert in_strike_zone(frame(0.0, 3.4 + BALL_RADIUS_FT - 0.001)).iloc[0]


def test_ball_clearly_above_the_top_edge_is_out():
    assert not in_strike_zone(frame(0.0, 3.4 + BALL_RADIUS_FT + 0.05)).iloc[0]


def test_vertical_bounds_follow_the_batter():
    """Same location, different batters, different verdict."""
    tall = frame(0.0, 3.9, sz_top=4.0, sz_bot=1.9)
    short = frame(0.0, 3.9, sz_top=3.0, sz_bot=1.4)
    assert in_strike_zone(tall).iloc[0]
    assert not in_strike_zone(short).iloc[0]


def test_horizontal_edge_uses_half_plate():
    assert in_strike_zone(frame(HALF_PLATE_FT - 0.01, 2.5)).iloc[0]
    assert not in_strike_zone(frame(HALF_PLATE_FT + 0.01, 2.5)).iloc[0]


def test_missing_coordinates_are_not_in_zone():
    df = pd.DataFrame({
        "plate_x": [None], "plate_z": [None],
        "sz_top": [None], "sz_bot": [None],
    })
    assert not in_strike_zone(df).iloc[0]


def test_add_zone_flag_does_not_mutate_input():
    df = frame(0.0, 2.5)
    before = list(df.columns)
    add_zone_flag(df)
    assert list(df.columns) == before


def test_object_dtype_input_does_not_crash():
    """Callers may pass a frame that never went through the loader.

    A raw single-day Parquet, or a hand-built frame, can carry object
    dtype. Without defensive coercion this failed with an opaque
    "bad operand type for abs()" error.
    """
    df = pd.DataFrame({
        "plate_x": ["0.0"], "plate_z": ["2.5"],
        "sz_top": ["3.4"], "sz_bot": ["1.6"],
    })
    assert in_strike_zone(df).iloc[0]


def test_unparseable_values_are_not_in_zone():
    df = pd.DataFrame({
        "plate_x": ["garbage"], "plate_z": [2.5],
        "sz_top": [3.4], "sz_bot": [1.6],
    })
    assert not in_strike_zone(df).iloc[0]
