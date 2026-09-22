import numpy as np
import pandas as pd
import pytest

from src.models.kbo_translation import (
    MIN_PA, MU_MEAN, TAU_MEAN,
    build_pairs, expected_kbo_k, invlogit, logit, project_mlb_k,
    projection_summary,
)


def lines(rows, col="player_en"):
    return pd.DataFrame(rows, columns=[col, "pa", "so"])


def test_logit_roundtrip():
    for p in [0.05, 0.25, 0.5, 0.9]:
        assert invlogit(logit(p)) == pytest.approx(p, abs=1e-9)


def test_kbo_strikeout_rate_is_lower_than_mlb():
    """mu is negative: the league is easier to make contact in."""
    assert MU_MEAN < 0
    for mlb_k in [0.15, 0.25, 0.35]:
        assert expected_kbo_k(mlb_k) < mlb_k


def test_the_ratio_is_not_constant():
    """A constant log-odds shift gives 0.69 at 15% and 0.74 at 35%.
    Applying one ratio everywhere understates high-strikeout hitters."""
    low = expected_kbo_k(0.15) / 0.15
    high = expected_kbo_k(0.35) / 0.35
    assert high > low + 0.03


def test_projection_reverses_the_translation():
    """Projecting from a KBO rate should land near the MLB rate that
    produced it."""
    mlb_k = 0.25
    kbo_k = expected_kbo_k(mlb_k)
    proj = project_mlb_k(kbo_k, kbo_pa=5000, n_draws=20000)
    assert proj.mean() == pytest.approx(mlb_k, abs=0.02)


def test_intervals_are_wide_because_tau_dominates():
    """47 transition players is not many. An 80% interval spanning under
    5 points would be false precision."""
    s = projection_summary(0.15, 500)
    assert s["upper"] - s["lower"] > 0.05


def test_smaller_kbo_sample_widens_the_interval():
    wide = projection_summary(0.15, 150)
    narrow = projection_summary(0.15, 500)
    assert (wide["upper"] - wide["lower"]) > (narrow["upper"] - narrow["lower"])


def test_more_kbo_pa_barely_helps():
    """The binding constraint is the number of transition players, not
    one player's sample. Going 150 -> 2000 PA should not collapse the
    interval."""
    small = projection_summary(0.15, 150)
    huge = projection_summary(0.15, 2000)
    assert (huge["upper"] - huge["lower"]) > 0.7 * (small["upper"] - small["lower"])


def test_build_pairs_applies_the_pa_floor():
    kbo = lines([("A", 500, 90), ("B", MIN_PA - 1, 20)])
    mlb = lines([("A", 500, 125), ("B", 500, 125)])
    d = build_pairs(kbo, mlb)
    assert list(d.index) == ["A"]


def test_build_pairs_sums_multiple_seasons():
    kbo = lines([("A", 300, 50), ("A", 300, 60)])
    mlb = lines([("A", 500, 125)])
    d = build_pairs(kbo, mlb)
    assert d.loc["A", "kbo_pa"] == 600
    assert d.loc["A", "kbo_k"] == pytest.approx(110 / 600)
