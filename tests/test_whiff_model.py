import numpy as np
import pandas as pd
import pytest

from src.models.whiff import (
    CATEGORICAL_FEATURES,
    MIN_PITCH_TYPE_COUNT,
    NUMERIC_FEATURES,
    build_features,
    fit_lookup_baseline,
    predict_lookup,
    prepare_swings,
)


def pitches(specs):
    """specs: (description, pitch_type, stand, plate_x, plate_z, sz_bot, sz_top)."""
    n = len(specs)
    return pd.DataFrame({
        "description": [s[0] for s in specs],
        "pitch_type": [s[1] for s in specs],
        "stand": [s[2] for s in specs],
        "plate_x": [s[3] for s in specs],
        "plate_z": [s[4] for s in specs],
        "sz_bot": [s[5] for s in specs],
        "sz_top": [s[6] for s in specs],
        "p_throws": ["R"] * n,
        "release_speed": [93.0] * n,
        "pfx_x": [-0.6] * n, "pfx_z": [1.3] * n,
        "release_spin_rate": [2300] * n, "release_extension": [6.5] * n,
        "balls": [0] * n, "strikes": [1] * n,
    })


def test_target_is_whiff_given_swing():
    df = pitches([
        ("swinging_strike", "SL", "R", 0.0, 2.0, 1.6, 3.4),
        ("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4),
        ("ball", "FF", "R", 1.5, 2.5, 1.6, 3.4),          # not a swing
        ("foul_tip", "SL", "R", 0.0, 2.0, 1.6, 3.4),      # swing, not whiff
    ])
    s = prepare_swings(df)
    assert len(s) == 3
    assert s["target"].tolist() == [1, 0, 0]


def test_plate_x_flips_for_left_handed_batters():
    df = pitches([
        ("foul", "FF", "R", 0.8, 2.5, 1.6, 3.4),
        ("foul", "FF", "L", 0.8, 2.5, 1.6, 3.4),
    ])
    s = prepare_swings(df)
    assert s["plate_x_bat"].tolist() == pytest.approx([0.8, -0.8])


def test_plate_z_rel_is_relative_to_each_batters_zone():
    """A tall and a short hitter at the same absolute height differ."""
    df = pitches([
        ("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4),   # mid zone
        ("foul", "FF", "R", 0.0, 2.5, 2.0, 4.0),   # lower in a taller zone
    ])
    s = prepare_swings(df)
    assert s["plate_z_rel"].iloc[0] == pytest.approx(0.5)
    assert s["plate_z_rel"].iloc[1] == pytest.approx(0.25)


def test_rare_pitch_types_bucket_to_other():
    specs = ([("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4)] * 10
             + [("foul", "SC", "R", 0.0, 2.5, 1.6, 3.4)] * 2)
    s = prepare_swings(pitches(specs))
    X = build_features(s, keep_types={"FF"})
    assert "pitch_type_b_OTHER" in X.columns
    assert "pitch_type_b_SC" not in X.columns


def test_interaction_columns_exist_for_every_pitch_dummy():
    specs = ([("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4)] * 5
             + [("foul", "SL", "R", 0.0, 2.0, 1.6, 3.4)] * 5)
    s = prepare_swings(pitches(specs))
    X = build_features(s, keep_types={"FF", "SL"})
    dummies = [c for c in X.columns if c.startswith("pitch_type_b_") and not c.endswith("_x_pz")]
    for d in dummies:
        assert f"{d}_x_pz" in X.columns


def test_columns_are_aligned_when_a_pitch_type_is_absent():
    """Validation may lack a pitch type seen in training."""
    train = prepare_swings(pitches(
        [("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4)] * 5
        + [("foul", "SL", "R", 0.0, 2.0, 1.6, 3.4)] * 5))
    val = prepare_swings(pitches([("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4)] * 3))

    X_train = build_features(train, {"FF", "SL"})
    X_val = build_features(val, {"FF", "SL"}, columns=X_train.columns)
    assert list(X_val.columns) == list(X_train.columns)


def test_lookup_shrinkage_prevents_certainty():
    """An unshrunk cell of 0.0 or 1.0 gives infinite log loss."""
    df = pitches([("swinging_strike", "SL", "R", 0.0, 2.0, 1.6, 3.4)] * 3)
    s = prepare_swings(df)
    table, fallback = fit_lookup_baseline(s)
    assert (table < 1.0).all()
    assert (table > 0.0).all()


def test_feature_matrix_is_all_numeric():
    s = prepare_swings(pitches([("foul", "FF", "R", 0.0, 2.5, 1.6, 3.4)] * 5))
    X = build_features(s, {"FF"})
    assert all(pd.api.types.is_numeric_dtype(X[c]) or pd.api.types.is_bool_dtype(X[c])
               for c in X.columns)


def test_lookup_survives_a_degenerate_global_rate():
    """Shrinkage pulls toward the global rate, so if that rate is itself
    0 or 1 every cell lands there and log loss becomes infinite. Found by
    a test whose fixture happened to be all-whiff; the floor is the fix."""
    from src.models.whiff import PROBABILITY_FLOOR

    all_whiff = prepare_swings(pitches(
        [("swinging_strike", "SL", "R", 0.0, 2.0, 1.6, 3.4)] * 3))
    table, fallback = fit_lookup_baseline(all_whiff)
    assert table.max() <= 1.0 - PROBABILITY_FLOOR
    assert fallback <= 1.0 - PROBABILITY_FLOOR

    no_whiff = prepare_swings(pitches(
        [("foul", "SL", "R", 0.0, 2.0, 1.6, 3.4)] * 3))
    table2, fallback2 = fit_lookup_baseline(no_whiff)
    assert table2.min() >= PROBABILITY_FLOOR
    assert fallback2 >= PROBABILITY_FLOOR


def test_log_loss_is_finite_on_a_degenerate_fit():
    """The actual failure mode the floor prevents."""
    from sklearn.metrics import log_loss

    all_whiff = prepare_swings(pitches(
        [("swinging_strike", "SL", "R", 0.0, 2.0, 1.6, 3.4)] * 3))
    table, fallback = fit_lookup_baseline(all_whiff)
    preds = predict_lookup(all_whiff, table, fallback)

    loss = log_loss([1, 1, 0], preds, labels=[0, 1])
    assert np.isfinite(loss)
