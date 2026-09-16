import numpy as np
import pandas as pd
import pytest

from src.models.similarity import (
    SIMILARITY_FEATURES,
    build_distance_matrix,
    dimension_dominance,
    nearest,
)


def profiles(rows):
    """rows: (id, chase, zone_contact, barrel, launch_angle)."""
    return pd.DataFrame(
        {"chase_pct": [r[1] for r in rows],
         "zone_contact_pct": [r[2] for r in rows],
         "barrel_pct": [r[3] for r in rows],
         "avg_launch_angle": [r[4] for r in rows]},
        index=[r[0] for r in rows])


def test_redundant_power_metrics_are_excluded():
    """hard_hit and avg_exit_velocity correlate 0.93 and 0.77 with
    barrel. Including all three makes three of four dimensions power."""
    assert "hard_hit_pct" not in SIMILARITY_FEATURES
    assert "avg_exit_velocity" not in SIMILARITY_FEATURES
    assert "whiff_pct" not in SIMILARITY_FEATURES   # -0.92 with zone_contact
    assert len(SIMILARITY_FEATURES) == 4


def test_identical_players_are_distance_zero():
    p = profiles([(1, 0.28, 0.85, 0.08, 13.0),
                  (2, 0.28, 0.85, 0.08, 13.0),
                  (3, 0.40, 0.75, 0.20, 20.0)])
    d = build_distance_matrix(p)
    assert d.loc[1, 2] == pytest.approx(0.0, abs=1e-9)
    assert d.loc[1, 3] > 0


def test_magnitude_matters_not_only_direction():
    """Cosine rated Judge (0.270 barrel) and Conforto (0.118) at 0.962.
    Euclidean must separate them."""
    p = profiles([
        (1, 0.18, 0.80, 0.27, 19.0),    # extreme
        (2, 0.24, 0.85, 0.12, 15.0),    # same shape, much smaller
        (3, 0.26, 0.80, 0.22, 16.0),    # genuinely similar
    ])
    d = build_distance_matrix(p)
    assert d.loc[1, 3] < d.loc[1, 2]


def test_nearest_returns_z_scores_for_interpretation():
    p = profiles([(i, 0.25 + i * 0.01, 0.85, 0.08, 13.0) for i in range(6)])
    out = nearest(0, build_distance_matrix(p), p, n=3)
    for f in SIMILARITY_FEATURES:
        assert f"z_{f}" in out.columns
    assert "distance" in out.columns
    assert len(out) == 3


def test_nearest_excludes_the_player_himself():
    p = profiles([(i, 0.25 + i * 0.01, 0.85, 0.08, 13.0) for i in range(6)])
    out = nearest(2, build_distance_matrix(p), p, n=3)
    assert 2 not in out.index


def test_dominance_detects_a_single_dominant_axis():
    """One extreme dimension can effectively BE the similarity."""
    rng = np.random.default_rng(0)
    rows = [(i, 0.28 + rng.normal(0, 0.01), 0.85 + rng.normal(0, 0.01),
             0.08 + rng.normal(0, 0.005), 13.0 + rng.normal(0, 0.5))
            for i in range(40)]
    rows.append((99, 0.28, 0.85, 0.40, 13.0))     # extreme barrel only
    p = profiles(rows)

    dom = dimension_dominance(99, p)
    assert dom.index[0] == "barrel_pct"
    assert dom.iloc[0] > 0.8


def test_unknown_player_raises():
    p = profiles([(1, 0.28, 0.85, 0.08, 13.0), (2, 0.30, 0.84, 0.09, 14.0)])
    with pytest.raises(KeyError):
        nearest(99, build_distance_matrix(p), p)
