"""P(Whiff | Swing) — data preparation, baselines, and the logistic model.

Rebuilt three times across three notebooks before being moved here. That
is the CLAUDE.md rule in action: once logic is reused, it belongs in
src/. A notebook's kernel state is volatile; a module is not.

Every design decision below traces to a documented finding:
  - swing/whiff definitions          docs/data_dictionary.md (Day 4)
  - strike zone                      docs/data_dictionary.md (Day 13)
  - plate_z sign reversal by pitch   docs/model_whiff_baseline.md (Day 25)
  - rare pitch type bucketing        docs/model_whiff_logistic.md (Day 26)
  - isotonic calibration             docs/model_whiff_calibration.md (Day 27)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.features.plate_discipline import add_discipline_flags
from src.features.strike_zone import in_strike_zone
from src.utils.leakage import banned_for_pitch_outcome, check_features
from src.utils.pipeline import load_all_snapshots
from src.utils.temporal import TemporalSplit, split_by_date

TRAIN_END = "2024-07-14"
VALIDATION_END = "2024-08-31"

NUMERIC_FEATURES = [
    "plate_x_bat", "plate_z_rel", "release_speed", "pfx_x", "pfx_z",
    "release_spin_rate", "release_extension", "balls", "strikes",
]
CATEGORICAL_FEATURES = ["pitch_type_b", "stand", "p_throws"]

MIN_PITCH_TYPE_COUNT = 500
LOOKUP_KEYS = ["pitch_type", "balls", "strikes", "in_zone_flag"]
LOOKUP_PRIOR_STRENGTH = 50.0
RANDOM_SEED = 42

# The model was built and validated on 2024 only.
SEASONS = [2024]

# Never emit a probability of exactly 0 or 1: log loss would be infinite.
PROBABILITY_FLOOR = 1e-6


def prepare_swings(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """All swings with the target and derived location features."""
    if df is None:
        # Season MUST be explicit. Loading every snapshot on disk pooled
        # 2021, 2022 and 2024 during a concurrent backfill on 2026-09-08
        # and silently changed every result — Aaron Judge's chase rate
        # moved 0.179 to 0.209 between runs of identical code.
        df = load_all_snapshots(seasons=SEASONS)

    f = add_discipline_flags(df)
    s = f[f["is_swing"]].copy()
    s["target"] = s["is_whiff"].astype(int)
    s["in_zone_flag"] = in_strike_zone(s)

    # plate_x is signed from the catcher's view, so its meaning inverts
    # with batter handedness (same issue as pfx_x on Day 19).
    px = pd.to_numeric(s["plate_x"], errors="coerce").astype("float64")
    s["plate_x_bat"] = np.where(s["stand"] == "L", -px, px)

    # Height relative to the batter's own zone. Day 13 measured a 36 cm
    # spread in zone tops across batters, so absolute height is not
    # comparable between hitters.
    pz = pd.to_numeric(s["plate_z"], errors="coerce").astype("float64")
    top = pd.to_numeric(s["sz_top"], errors="coerce").astype("float64")
    bot = pd.to_numeric(s["sz_bot"], errors="coerce").astype("float64")
    s["plate_z_rel"] = (pz - bot) / (top - bot)

    return s


def make_split(swings: pd.DataFrame) -> TemporalSplit:
    """Chronological split. The train/validation gap is the All-Star break."""
    return split_by_date(swings, train_end=TRAIN_END, validation_end=VALIDATION_END)


def bucket_pitch_types(split: TemporalSplit) -> set[str]:
    """Pitch types with enough training swings to estimate a coefficient.

    Fitted on TRAIN only. Model C gave a six-swing pitch type the same
    coefficient magnitude as one with 10,705 swings.
    """
    counts = split.train["pitch_type"].value_counts()
    return set(counts[counts >= MIN_PITCH_TYPE_COUNT].index)


def build_features(part: pd.DataFrame, keep_types: set[str],
                   columns: pd.Index | None = None) -> pd.DataFrame:
    """Feature matrix with pitch_type x plate_z_rel interactions.

    The interaction is not decoration: plate_z correlates +0.21 with
    whiff for four-seams and -0.50 for knuckle curves. A single linear
    coefficient cannot represent both, and the linear model loses to the
    lookup baseline without it.
    """
    p = part.copy()
    pt = p["pitch_type"].astype(str)
    p["pitch_type_b"] = pt.where(pt.isin(keep_types), "OTHER")

    num = p[NUMERIC_FEATURES].apply(pd.to_numeric, errors="coerce").astype("float64")
    cat = pd.get_dummies(p[CATEGORICAL_FEATURES].astype(str), drop_first=True)
    X = pd.concat([num, cat], axis=1)

    pz = pd.to_numeric(p["plate_z_rel"], errors="coerce").astype("float64")
    for col in [c for c in X.columns if c.startswith("pitch_type_b_")]:
        X[f"{col}_x_pz"] = X[col].astype(float) * pz.to_numpy()

    if columns is not None:
        X = X.reindex(columns=columns, fill_value=0)
    return X


def fit_lookup_baseline(train: pd.DataFrame) -> tuple[pd.Series, float]:
    """Grouped means with shrinkage. Unshrunk 0/1 cells give infinite log loss."""
    global_rate = train["target"].mean()
    tbl = train.groupby(LOOKUP_KEYS)["target"].agg(["sum", "size"])
    rate = ((tbl["sum"] + global_rate * LOOKUP_PRIOR_STRENGTH)
            / (tbl["size"] + LOOKUP_PRIOR_STRENGTH))

    # Shrinkage alone does not guarantee an interior probability: if the
    # global rate is itself 0 or 1 (a filtered subset, a different
    # target), every cell shrinks to that value and log loss becomes
    # infinite. Clip as a floor. On full-season data the league rate is
    # 0.23 and this never binds.
    rate = rate.clip(PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR)
    return rate, float(np.clip(global_rate, PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR))


def predict_lookup(part: pd.DataFrame, table: pd.Series, fallback: float) -> np.ndarray:
    idx = pd.MultiIndex.from_frame(part[LOOKUP_KEYS])
    return table.reindex(idx).fillna(fallback).to_numpy()


def fit_logistic(X: pd.DataFrame, y: np.ndarray, seed: int = RANDOM_SEED) -> Pipeline:
    """Imputation and scaling live inside the pipeline so they are fit on
    training data only."""
    check_features(X.columns, banned_for_pitch_outcome(), context="whiff logistic")
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=seed)),
    ]).fit(X, y)


def fit_boosting(X: pd.DataFrame, y: np.ndarray, seed: int = RANDOM_SEED):
    """Gradient boosting. Beats the logistic model by 0.030 log loss.

    Justification for the complexity (CLAUDE.md requires one): the sign
    of the height effect inverts by pitch type, and its strength varies
    from -0.50 (knuckle curve) to +0.01 (sinker). A fixed interaction
    term must be applied to every pitch type whether or not it helps —
    on cutters and sinkers, where there is no height effect, it added
    pure noise and the logistic model LOST to the lookup baseline there.
    Trees split only where a split helps.

    NOT calibrated. Unlike the logistic model, boosting is already well
    calibrated (ECE 0.0058); isotonic regression made it worse (0.0067)
    by discretising away resolution. Calibration is diagnosed, not
    applied by default.

    Hyperparameters barely matter here: max_leaf_nodes 15/31/63 and
    learning rate 0.03/0.06 span only 0.0012 in log loss, 4% of the
    margin over the logistic model.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier

    check_features(X.columns, banned_for_pitch_outcome(), context="whiff boosting")
    return HistGradientBoostingClassifier(
        max_iter=500,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=seed,
    ).fit(X, y)


def calibrate(model: Pipeline, X_cal: pd.DataFrame, y_cal: np.ndarray):
    """Isotonic calibration on data the model did not train on.

    Isotonic, not sigmoid: the output of a logistic regression is already
    a sigmoid, so Platt scaling has no shape left to correct and made ECE
    worse (0.0278 to 0.0300). Isotonic cut it by 68%.
    """
    try:
        from sklearn.frozen import FrozenEstimator
        base = FrozenEstimator(model)
        return CalibratedClassifierCV(base, method="isotonic").fit(X_cal, y_cal)
    except ImportError:  # older sklearn
        return CalibratedClassifierCV(model, method="isotonic",
                                      cv="prefit").fit(X_cal, y_cal)


@dataclass
class WhiffModel:
    """Everything needed to reproduce or inspect the fitted model."""
    split: TemporalSplit
    keep_types: set[str]
    X_train: pd.DataFrame
    X_validation: pd.DataFrame
    y_train: np.ndarray
    y_validation: np.ndarray
    model: Pipeline
    calibrated: object
    lookup_table: pd.Series
    lookup_fallback: float
    n_calibration: int

    def predict(self, part: pd.DataFrame, calibrated: bool = True) -> np.ndarray:
        X = build_features(part, self.keep_types, columns=self.X_train.columns)
        est = self.calibrated if calibrated else self.model
        return est.predict_proba(X)[:, 1]

    def predict_baseline(self, part: pd.DataFrame) -> np.ndarray:
        return predict_lookup(part, self.lookup_table, self.lookup_fallback)


def build(df: pd.DataFrame | None = None) -> WhiffModel:
    """Full pipeline: load, split, fit baseline and model, calibrate.

    The calibration set is the FIRST half of validation and evaluation
    should use the second half — calibrating and evaluating on the same
    rows is a form of leakage.
    """
    swings = prepare_swings(df)
    split = make_split(swings)
    keep = bucket_pitch_types(split)

    X_train = build_features(split.train, keep)
    X_val = build_features(split.validation, keep, columns=X_train.columns)
    y_train = split.train["target"].to_numpy()
    y_val = split.validation["target"].to_numpy()

    model = fit_logistic(X_train, y_train)

    n_cal = len(X_val) // 2
    calibrated = calibrate(model, X_val.iloc[:n_cal], y_val[:n_cal])

    table, fallback = fit_lookup_baseline(split.train)

    return WhiffModel(
        split=split, keep_types=keep,
        X_train=X_train, X_validation=X_val,
        y_train=y_train, y_validation=y_val,
        model=model, calibrated=calibrated,
        lookup_table=table, lookup_fallback=fallback,
        n_calibration=n_cal,
    )
