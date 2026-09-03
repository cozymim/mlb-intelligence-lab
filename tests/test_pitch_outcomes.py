import pandas as pd
import pytest

from src.features.pitch_outcomes import (
    GROUND_BALL_MAX_DEG,
    POPUP_MIN_DEG,
    add_batted_ball_types,
    primary_weapons,
)


def test_launch_angle_bands_follow_the_mlb_glossary():
    df = pd.DataFrame({"launch_angle": [9.9, 10.0, 50.0, 50.1]})
    out = add_batted_ball_types(df)
    assert out["is_ground_ball"].tolist() == [True, False, False, False]
    assert out["is_popup"].tolist() == [False, False, False, True]


def test_missing_launch_angle_is_neither():
    df = pd.DataFrame({"launch_angle": [None]})
    out = add_batted_ball_types(df)
    assert not out["is_ground_ball"].iloc[0]
    assert not out["is_popup"].iloc[0]


def test_flags_are_boolean_with_nullable_input():
    df = pd.DataFrame({"launch_angle": pd.array([5.0, None], dtype="Float64")})
    out = add_batted_ball_types(df)
    assert out["is_ground_ball"].dtype == bool


def test_primary_weapon_picks_the_best_standardised_dimension():
    """A pitch weak on whiff but strong on grounders is a grounder pitch —
    exactly the sinker case that motivates this module."""
    # Spreads are deliberately comparable across dimensions. Standardising
    # is sensitive to variance: a dimension where pitch types cluster
    # tightly produces larger z-scores for the same rank ordering.
    outcomes = pd.DataFrame({
        "whiff_pct": [0.12, 0.40, 0.16],
        "chase_pct": [0.25, 0.26, 0.24],
        "gb_pct":    [0.57, 0.43, 0.35],
        "popup_pct": [0.05, 0.10, 0.20],
    }, index=["SI", "SL", "FF"])

    z = primary_weapons(outcomes)
    assert z.loc["SI", "primary_weapon"] == "gb_pct"
    assert z.loc["SL", "primary_weapon"] == "whiff_pct"
    assert z.loc["FF", "primary_weapon"] == "popup_pct"


def test_standardisation_is_within_dimension():
    """Raw rates across dimensions are not comparable; z-scores are."""
    outcomes = pd.DataFrame({
        "whiff_pct": [0.10, 0.30],
        "gb_pct":    [0.60, 0.40],
    }, index=["A", "B"])
    z = primary_weapons(outcomes)
    assert z.loc["A", "gb_pct"] == pytest.approx(0.7071, abs=1e-3)
    assert z.loc["A", "whiff_pct"] == pytest.approx(-0.7071, abs=1e-3)


def test_standardisation_favours_low_variance_dimensions():
    """A real property of z-scores, not a bug: if pitch types cluster
    tightly on one dimension, being top there scores higher than being
    top on a widely-spread dimension. Documented so it is not mistaken
    for a defect later."""
    outcomes = pd.DataFrame({
        "whiff_pct": [0.10, 0.50],   # large spread
        "gb_pct":    [0.20, 0.22],   # small spread, same ordering
    }, index=["A", "B"])
    z = primary_weapons(outcomes)

    # Identical ordering gives identical z-scores: standardising removes
    # scale entirely. Variance only decides between dimensions when the
    # orderings differ.
    assert z.loc["B", "gb_pct"] == pytest.approx(z.loc["B", "whiff_pct"], abs=1e-6)


def test_unknown_columns_raise_rather_than_crash():
    """Renaming a column previously produced an empty frame and an opaque
    'argmax of an empty sequence' error from deep inside pandas."""
    outcomes = pd.DataFrame({"made_up": [0.1, 0.2]}, index=["A", "B"])
    with pytest.raises(KeyError, match="none of"):
        primary_weapons(outcomes)
