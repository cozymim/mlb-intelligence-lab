import numpy as np
import pandas as pd
import pytest

from src.models.projection import SKILL_FEATURES, build_dataset, fit


def lines(rows):
    return pd.DataFrame(rows, columns=["batter", "season", "pa_count", "k", "bb"])


def make_lines(n_players=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for b in range(n_players):
        rate = rng.uniform(0.15, 0.32)
        for s in (2021, 2022, 2023, 2024):
            pa = 500
            rows.append((b, s, pa, int(pa * rate), int(pa * 0.08)))
    return lines(rows)


def make_skills(n_players=40, seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "batter": np.repeat(range(n_players), 4),
        "season": list((2021, 2022, 2023, 2024)) * n_players,
        "chase_pct": rng.uniform(0.18, 0.40, n_players * 4),
        "zone_contact_pct": rng.uniform(0.75, 0.95, n_players * 4),
    })


def test_only_two_skill_features_are_used():
    """Five features scored identically to Marcel under cross-validation
    while looking better in training. whiff_pct correlates -0.91 with
    zone_contact_pct; swing_pct 0.85-0.88 with the swing rates."""
    assert SKILL_FEATURES == ["chase_pct", "zone_contact_pct"]
    assert "whiff_pct" not in SKILL_FEATURES
    assert "swing_pct" not in SKILL_FEATURES


def test_skills_come_from_the_prior_season_only():
    """Using target-season skills is leakage: they are not knowable when
    the projection is made."""
    skills = make_skills()
    skills.loc[skills["season"] == 2024, "chase_pct"] = 99.0   # poison
    data = build_dataset(make_lines(), skills, 2024, min_pa=100, min_weighted_pa=50)
    assert (data["chase_pct"] < 1.0).all()


def test_dataset_requires_prior_history_and_playing_time():
    data = build_dataset(make_lines(), make_skills(), 2024,
                         min_pa=100, min_weighted_pa=50)
    assert (data["pa_count"] >= 100).all()
    assert (data["weighted_pa"] >= 50).all()


def test_marcel_dominates_the_fitted_coefficients():
    """Marcel carries most of the signal; skills are a correction."""
    data = build_dataset(make_lines(200), make_skills(200), 2024,
                         min_pa=100, min_weighted_pa=50)
    m = fit(data, "k")
    coefs = pd.Series(m.coef_, index=["marcel_k"] + SKILL_FEATURES)
    assert abs(coefs["marcel_k"]) > abs(coefs[SKILL_FEATURES]).max()


def test_missing_skills_drop_the_row():
    skills = make_skills()
    skills.loc[skills["batter"] == 0, "chase_pct"] = np.nan
    data = build_dataset(make_lines(), skills, 2024,
                         min_pa=100, min_weighted_pa=50)
    assert 0 not in data.index
