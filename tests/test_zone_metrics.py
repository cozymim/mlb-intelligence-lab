import pandas as pd
import pytest

from src.features.plate_discipline import (
    chase_rate,
    contact_rate,
    discipline_profile,
    zone_contact_rate,
    zone_swing_rate,
)


def pitches(rows):
    """rows: list of (description, plate_x, plate_z)."""
    return pd.DataFrame({
        "description": [r[0] for r in rows],
        "plate_x": [r[1] for r in rows],
        "plate_z": [r[2] for r in rows],
        "sz_top": [3.4] * len(rows),
        "sz_bot": [1.6] * len(rows),
    })


IN = (0.0, 2.5)      # middle of the zone
OUT = (2.0, 2.5)     # well outside


def test_chase_rate_counts_only_out_of_zone_pitches():
    df = pitches([
        ("foul", *OUT),            # chase
        ("ball", *OUT),            # no chase
        ("swinging_strike", *IN),  # in zone, irrelevant to chase
        ("called_strike", *IN),
    ])
    assert chase_rate(df) == pytest.approx(0.5)   # 1 of 2 out-of-zone


def test_zone_swing_rate_counts_only_in_zone_pitches():
    df = pitches([
        ("foul", *IN),
        ("called_strike", *IN),
        ("swinging_strike", *OUT),
    ])
    assert zone_swing_rate(df) == pytest.approx(0.5)   # 1 of 2 in-zone


def test_contact_and_zone_contact_differ():
    """A hitter who whiffs only on chases has perfect zone contact."""
    df = pitches([
        ("hit_into_play", *IN),
        ("foul", *IN),
        ("swinging_strike", *OUT),
    ])
    assert contact_rate(df) == pytest.approx(2 / 3)
    assert zone_contact_rate(df) == pytest.approx(1.0)


def test_foul_tip_counts_as_contact():
    """Consistent with the Day 4 decision: the bat touched the ball."""
    df = pitches([("foul_tip", *IN)])
    assert contact_rate(df) == pytest.approx(1.0)


def test_rates_are_nan_without_denominator():
    only_in_zone = pitches([("ball", *IN)])
    assert pd.isna(chase_rate(only_in_zone))

    only_out = pitches([("ball", *OUT)])
    assert pd.isna(zone_swing_rate(only_out))


def test_profile_reports_sample_sizes():
    df = pitches([
        ("foul", *IN), ("ball", *OUT),
        ("swinging_strike", *OUT), ("called_strike", *IN),
    ])
    p = discipline_profile(df)

    assert p["pitches"] == 4
    assert p["n_in_zone"] == 2
    assert p["n_out_of_zone"] == 2
    assert p["n_swings"] == 2
    assert p["n_zone_swings"] == 1


def test_profile_flags_insufficient_sample():
    df = pitches([("foul", *IN)])
    p = discipline_profile(df, min_pitches=100)
    assert p["insufficient_sample"] is True
    assert "chase_pct" not in p
