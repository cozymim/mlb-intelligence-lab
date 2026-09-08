import numpy as np
import pandas as pd
import pytest

from src.models.pitcher_score import (
    PITCHER_SKILLS,
    QUALIFICATION,
    fit,
    qualified,
)


def profiles(n=300, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "k_pct": rng.normal(0.22, 0.06, n),
        "bb_pct": rng.normal(0.08, 0.03, n),
        "chase_pct": rng.normal(0.28, 0.05, n),
        "gb_pct": rng.normal(0.44, 0.09, n),
        "barrel_pct": rng.normal(0.08, 0.03, n),
        "hard_hit_pct": rng.normal(0.39, 0.06, n),
        "n_swings": 400, "bbe": 200, "pa": 400,
    })
    signal = (-0.60 * df["k_pct"] + 0.30 * df["bb_pct"]
              + 0.35 * df["barrel_pct"])
    df["woba_against"] = 0.32 + (signal - signal.mean()) + rng.normal(0, 0.005, n)
    df.index.name = "pitcher"
    return df


def test_qualification_excludes_tiny_samples():
    """Without thresholds, pitchers with two career pitches show up with
    bb_pct 0.667 and zone_pct 1.000."""
    p = profiles(50)
    p.loc[p.index[:10], "bbe"] = QUALIFICATION["bbe"] - 1
    assert len(qualified(p)) == 40


def test_strikeouts_lower_woba_allowed_and_walks_raise_it():
    w = fit(profiles()).weights
    assert w["k_pct"] < 0
    assert w["bb_pct"] > 0
    assert w["barrel_pct"] > 0


def test_strikeouts_outweigh_barrel_suppression():
    """Measured on 2024: -0.0196 vs +0.0106, roughly 2x."""
    w = fit(profiles()).weights
    assert abs(w["k_pct"]) > abs(w["barrel_pct"])


def test_whiff_rate_is_not_a_feature():
    """Dropped: r = 0.82 with k_pct, and biased against sinker-heavy
    pitchers (Day 22)."""
    assert "whiff_pct" not in PITCHER_SKILLS
    assert "zone_pct" not in PITCHER_SKILLS


def test_lower_score_is_better():
    p = profiles()
    s = fit(p)
    q = qualified(p)
    scores = s.score(q)
    assert scores.corr(q["woba_against"]) > 0.8


def test_scores_are_in_woba_units():
    p = profiles()
    s = fit(p)
    assert s.score(qualified(p)).between(0.20, 0.50).all()
