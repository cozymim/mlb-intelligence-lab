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


# --- damage assessment -------------------------------------------------

def damage_frame(rows):
    """rows: (batter, pitch_type, bbe, barrel_pct)."""
    idx = pd.MultiIndex.from_tuples([(r[0], r[1]) for r in rows],
                                    names=["batter", "pitch_type"])
    return pd.DataFrame({"bbe": [r[2] for r in rows],
                         "barrel_pct": [r[3] for r in rows]}, index=idx)


def damage_league(rates):
    return pd.DataFrame({"lg_barrel": pd.Series(rates)})


def test_low_whiff_high_damage_is_avoid():
    """Judge's four-seam: whiffs +1.1%, barrels +20.1%. A whiff-only
    report calls this unremarkable."""
    from src.scouting.batter_report import approach_with_damage

    out = approach_with_damage(
        1, splits([(1, "FF", 369, 0.201)]), league({"FF": 0.189}),
        damage_frame([(1, "FF", 113, 0.301)]), damage_league({"FF": 0.100}))
    assert "AVOID" in out[0]
    assert "+20.1%" in out[0]


def test_high_whiff_high_damage_is_chase_only():
    from src.scouting.batter_report import approach_with_damage

    out = approach_with_damage(
        1, splits([(1, "CH", 118, 0.458)]), league({"CH": 0.293}),
        damage_frame([(1, "CH", 29, 0.276)]), damage_league({"CH": 0.061}))
    assert "chase pitch ONLY" in out[0]


def test_high_whiff_low_damage_is_attack():
    from src.scouting.batter_report import approach_with_damage

    out = approach_with_damage(
        1, splits([(1, "SL", 200, 0.42)]), league({"SL": 0.32}),
        damage_frame([(1, "SL", 60, 0.06)]), damage_league({"SL": 0.072}))
    assert "ATTACK" in out[0]


def test_unmeasured_damage_is_not_reported_as_safe():
    """Judge's curveball: largest whiff gap he faced, and the only ATTACK
    in an earlier version. On 17 batted balls it barrels at 23.5%, over
    three times league. Silence about unmeasured risk reads as safety."""
    from src.scouting.batter_report import (
        DAMAGE_NOT_MEASURED, approach_with_damage)

    out = approach_with_damage(
        1, splits([(1, "CU", 61, 0.443)]), league({"CU": 0.296}),
        damage_frame([(1, "CU", 17, 0.235)]), damage_league({"CU": 0.072}))
    assert DAMAGE_NOT_MEASURED in out[0]
    assert "ATTACK" not in out[0]
    assert "17 bbe" in out[0]


def test_missing_damage_row_entirely_is_also_not_safe():
    from src.scouting.batter_report import (
        DAMAGE_NOT_MEASURED, approach_with_damage)

    out = approach_with_damage(
        1, splits([(1, "CU", 61, 0.443)]), league({"CU": 0.296}),
        damage_frame([(2, "CU", 60, 0.07)]), damage_league({"CU": 0.072}))
    assert DAMAGE_NOT_MEASURED in out[0]


# --- pitcher reports ---------------------------------------------------

def pitcher_outcomes(rows):
    """rows: (pitcher, pitch_type, pitches, swings, whiff_pct)."""
    idx = pd.MultiIndex.from_tuples([(r[0], r[1]) for r in rows],
                                    names=["pitcher", "pitch_type"])
    return pd.DataFrame({"pitches": [r[2] for r in rows],
                         "swings": [r[3] for r in rows],
                         "whiff_pct": [r[4] for r in rows]}, index=idx)


def usage_frame(rows):
    """rows: (pitcher, count_bucket, pitch_type, n, pct)."""
    return pd.DataFrame(rows, columns=["pitcher", "count_bucket",
                                       "pitch_type", "n", "pct"])


def usage_lg(pairs):
    return pd.Series(pairs)


def test_count_bucket_two_strikes_overrides():
    from src.scouting.pitcher_report import count_bucket
    assert count_bucket(3, 2) == "two_strike"
    assert count_bucket(0, 2) == "two_strike"
    assert count_bucket(3, 1) == "behind"
    assert count_bucket(0, 1) == "ahead"
    assert count_bucket(1, 1) == "even"


def test_out_pitch_requires_over_use_versus_league():
    """Skubal throws changeups 30.3% with two strikes against a league
    11.2% — that is an out pitch. Matching league usage is not."""
    from src.scouting.pitcher_report import hitting_approach

    o = pitcher_outcomes([(1, "CH", 500, 456, 0.439)])
    lg = pd.DataFrame({"lg_whiff": pd.Series({"CH": 0.293})})

    over = usage_frame([(1, "two_strike", "CH", 266, 0.303)])
    match = usage_frame([(1, "two_strike", "CH", 266, 0.115)])
    ulg = usage_lg({("two_strike", "CH"): 0.112})

    assert any("OUT PITCH" in s for s in
               hitting_approach(1, o, lg, over, ulg))
    assert not any("OUT PITCH" in s for s in
                   hitting_approach(1, o, lg, match, ulg))


def test_weak_pitch_recommendation_includes_usage():
    """A pitch that is weak but thrown 4% of the time is not actionable;
    the hitter needs to know how often it appears."""
    from src.scouting.pitcher_report import hitting_approach

    o = pitcher_outcomes([(1, "CU", 100, 40, 0.175), (1, "FF", 900, 500, 0.19)])
    lg = pd.DataFrame({"lg_whiff": pd.Series({"CU": 0.296, "FF": 0.189})})

    out = hitting_approach(1, o, lg, usage_frame([]), usage_lg({}))
    hunt = [s for s in out if "Hunt CU" in s]
    assert len(hunt) == 1
    assert "usage" in hunt[0]
    assert "40 swings" in hunt[0]


def test_low_swing_pitch_is_reported_as_not_measured():
    from src.scouting.pitcher_report import NOT_MEASURED, hitting_approach

    o = pitcher_outcomes([(1, "SV", 120, 15, 0.10)])
    lg = pd.DataFrame({"lg_whiff": pd.Series({"SV": 0.271})})
    out = hitting_approach(1, o, lg, usage_frame([]), usage_lg({}))
    assert any(NOT_MEASURED in s for s in out)


def test_fastball_tell_when_behind():
    """Wheeler throws 79.4% fastballs behind in the count."""
    from src.scouting.pitcher_report import hitting_approach

    o = pitcher_outcomes([(1, "FF", 900, 500, 0.19)])
    lg = pd.DataFrame({"lg_whiff": pd.Series({"FF": 0.189})})
    u = usage_frame([(1, "behind", "FF", 300, 0.794)])
    out = hitting_approach(1, o, lg, u, usage_lg({}))
    assert any("sit on it" in s for s in out)


def test_unknown_pitcher_is_insufficient():
    from src.scouting.pitcher_report import INSUFFICIENT, hitting_approach

    o = pitcher_outcomes([(1, "FF", 900, 500, 0.19)])
    lg = pd.DataFrame({"lg_whiff": pd.Series({"FF": 0.189})})
    assert hitting_approach(99, o, lg, usage_frame([]), usage_lg({})) == [INSUFFICIENT]
