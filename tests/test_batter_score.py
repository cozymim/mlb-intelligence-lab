import numpy as np
import pandas as pd
import pytest

from src.models.batter_score import (
    QUALIFICATION,
    SKILL_METRICS,
    BatterScore,
    fit,
    qualified,
)


def profiles(n=200, seed=0):
    """Synthetic batters where wOBA is a known function of skills."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "chase_pct": rng.normal(0.28, 0.06, n),
        "zone_swing_pct": rng.normal(0.68, 0.06, n),
        "zone_contact_pct": rng.normal(0.85, 0.05, n),
        "barrel_pct": rng.normal(0.08, 0.03, n),
        "n_out_of_zone": 500,
        "n_zone_swings": 500,
        "bbe": 300,
    })
    # Known relationship: barrel matters most, chase is negative. The
    # intercept is set so the mean lands near a realistic league wOBA
    # (~0.31) rather than wherever the coefficients happen to put it.
    signal = (1.2 * df["barrel_pct"] + 0.15 * df["zone_contact_pct"]
              - 0.10 * df["chase_pct"])
    df["woba"] = 0.31 + (signal - signal.mean()) + rng.normal(0, 0.005, n)
    df.index.name = "batter"
    return df


def test_qualification_uses_measured_thresholds():
    p = profiles(50)
    p.loc[p.index[:10], "bbe"] = QUALIFICATION["bbe"] - 1
    assert len(qualified(p)) == 40


def test_missing_woba_disqualifies():
    p = profiles(50)
    p.loc[p.index[:5], "woba"] = np.nan
    assert len(qualified(p)) == 45


def test_learned_signs_match_the_generating_process():
    s = fit(profiles(300))
    w = s.weights
    assert w["barrel_pct"] > 0
    assert w["zone_contact_pct"] > 0
    assert w["chase_pct"] < 0


def test_barrel_outweighs_chase():
    """Measured on 2024: 0.0289 vs -0.0075, roughly 4x."""
    w = fit(profiles(300)).weights
    assert abs(w["barrel_pct"]) > abs(w["chase_pct"])


def test_scores_are_in_woba_units():
    p = profiles(200)
    s = fit(p)
    scores = s.score(qualified(p))
    assert scores.between(0.20, 0.55).all()


def test_standardisation_uses_training_distribution():
    """Scoring a new sample against its own mean would make the score
    relative to that sample rather than the reference population."""
    train = profiles(200, seed=1)
    s = fit(train)

    shifted = profiles(200, seed=2)
    shifted["barrel_pct"] += 0.05        # a much better cohort

    assert s.score(qualified(shifted)).mean() > s.score(qualified(train)).mean()


def test_sensitivity_passes_on_learned_weights():
    """The arbitrary-weight version scored 0.053 on this measure."""
    from src.models.batter_score import sensitivity

    result = sensitivity(profiles(300))
    assert result["min_rank_correlation"] > 0.9
    assert result["ordering_stable"]
