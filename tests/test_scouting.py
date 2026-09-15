import numpy as np
import pandas as pd
import pytest

from src.scouting.batter_report import (
    AVOID_GAP,
    INSUFFICIENT,
    MIN_SWINGS_PER_PITCH,
    NOTABLE_GAP,
    add_zone_band,
    pitching_approach,
)


def splits(rows):
    """rows: (batter, pitch_type, swings, whiff_pct)."""
    idx = pd.MultiIndex.from_tuples([(r[0], r[1]) for r in rows],
                                    names=["batter", "pitch_type"])
    return pd.DataFrame({"swings": [r[2] for r in rows],
                         "whiff_pct": [r[3] for r in rows]}, index=idx)


def league(rates):
    return pd.DataFrame({"lg_whiff": pd.Series(rates)})


EMPTY_ZONE = pd.DataFrame(
    {"swings": [], "whiff_pct": []},
    index=pd.MultiIndex.from_tuples([], names=["batter", "zone_band"]))
EMPTY_ZONE_LG = pd.Series(dtype=float)


def test_unknown_batter_is_insufficient():
    out = pitching_approach(999, splits([(1, "SL", 100, 0.4)]),
                            league({"SL": 0.32}), EMPTY_ZONE, EMPTY_ZONE_LG)
    assert out == [INSUFFICIENT]


def test_below_swing_threshold_is_insufficient():
    out = pitching_approach(1, splits([(1, "SL", MIN_SWINGS_PER_PITCH - 1, 0.9)]),
                            league({"SL": 0.32}), EMPTY_ZONE, EMPTY_ZONE_LG)
    assert out == [INSUFFICIENT]


def test_no_weakness_is_stated_plainly_not_invented():
    """Juan Soto's 2024 report contains no pitch to attack. A system that
    always names a weakness would misdirect the pitching plan."""
    out = pitching_approach(1, splits([(1, "SL", 200, 0.33), (1, "FF", 200, 0.19)]),
                            league({"SL": 0.32, "FF": 0.19}),
                            EMPTY_ZONE, EMPTY_ZONE_LG)
    assert len(out) == 1
    assert "No significant deviations" in out[0]
    assert not any("Attack" in line for line in out)


def test_attack_requires_clearing_the_gap_threshold():
    just_under = splits([(1, "SL", 200, 0.32 + NOTABLE_GAP - 0.001)])
    just_over = splits([(1, "SL", 200, 0.32 + NOTABLE_GAP + 0.001)])
    lg = league({"SL": 0.32})

    assert not any("Attack" in s for s in
                   pitching_approach(1, just_under, lg, EMPTY_ZONE, EMPTY_ZONE_LG))
    assert any("Attack" in s for s in
               pitching_approach(1, just_over, lg, EMPTY_ZONE, EMPTY_ZONE_LG))


def test_every_recommendation_carries_its_sample_size():
    out = pitching_approach(1, splits([(1, "CH", 118, 0.458)]),
                            league({"CH": 0.293}), EMPTY_ZONE, EMPTY_ZONE_LG)
    assert "118 swings" in out[0]
    assert "+16.5%" in out[0]


def test_zone_bands_are_relative_to_each_batter():
    """Day 13: zone tops vary by 36 cm across hitters, so a fixed height
    band is not comparable between them."""
    df = pd.DataFrame({
        "plate_z": [2.5, 2.5],
        "sz_bot": [1.6, 2.0],
        "sz_top": [3.4, 4.0],
    })
    out = add_zone_band(df)
    assert out["z_rel"].iloc[0] == pytest.approx(0.5)
    assert out["z_rel"].iloc[1] == pytest.approx(0.25)
    assert out["zone_band"].iloc[0] == "middle"
    assert out["zone_band"].iloc[1] == "low"
