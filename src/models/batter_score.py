"""Batter evaluation score with weights learned from production.

An earlier version used equal weights across three axes and FAILED a
sensitivity test: power-heavy and contact-heavy rankings correlated at
Spearman 0.053, sharing two names in their top tens. The score measured
the weighting choice, not the batter. See docs/model_batter_score.md.

Weights here are regression coefficients from predicting observed wOBA
from four skill rates. This is not circular — the inputs are skills
(chase, swing, contact, barrel rates) and the target is production.

Learned weights (2024, 343 qualified batters, wOBA per 1 sd):

    barrel_pct         +0.0289
    zone_contact_pct   +0.0184
    chase_pct          -0.0075
    zone_swing_pct     +0.0067

Power carries roughly four times the weight of plate discipline —
nothing like the equal weighting originally assumed.

Sensitivity: across 5-fold resampling, rank correlations run 0.990 to
0.999 and coefficient ordering never changes. Contrast the 0.053 of the
arbitrary version.

R-squared is 0.50. The unexplained half includes speed, batted-ball
direction, opposing pitcher quality, and luck. Giancarlo Stanton is the
clearest miss: barrel rate 20.9% but wOBA 0.341, predicted 0.381 — he is
slow, and the model has no speed input.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.features.batted_ball import quality_profile
from src.features.plate_discipline import discipline_profile
from src.features.sample_size import STABILIZATION

SKILL_METRICS = ["chase_pct", "zone_swing_pct", "zone_contact_pct", "barrel_pct"]

MIN_PITCHES = 500

# Each skill must clear its own measured stabilization threshold.
QUALIFICATION = {
    "n_out_of_zone": STABILIZATION["chase_pct"][1],
    "n_zone_swings": STABILIZATION["zone_contact_pct"][1],
    "bbe": STABILIZATION["barrel_pct"][1],
}


def build_profiles(df: pd.DataFrame, min_pitches: int = MIN_PITCHES) -> pd.DataFrame:
    """Skill rates plus observed wOBA, one row per batter."""
    from src.data.validation import plate_appearances

    pa = plate_appearances(df)
    woba = pa.groupby("batter").agg(
        woba_num=("woba_value", "sum"), woba_den=("woba_denom", "sum"))
    woba["woba"] = (pd.to_numeric(woba["woba_num"], errors="coerce")
                    / pd.to_numeric(woba["woba_den"], errors="coerce"))

    rows = []
    for bid, g in df.groupby("batter"):
        if len(g) < min_pitches:
            continue
        p = discipline_profile(g)
        p.update(quality_profile(g))
        p["batter"] = bid
        rows.append(p)

    return pd.DataFrame(rows).set_index("batter").join(woba[["woba"]])


def qualified(profiles: pd.DataFrame) -> pd.DataFrame:
    """Batters clearing every stabilization threshold, with wOBA present."""
    mask = profiles["woba"].notna()
    for col, minimum in QUALIFICATION.items():
        mask &= profiles[col] >= minimum
    return profiles[mask].copy()


@dataclass
class BatterScore:
    model: LinearRegression
    means: pd.Series
    stds: pd.Series
    r_squared: float

    @property
    def weights(self) -> pd.Series:
        """Standardised coefficients: wOBA change per 1 sd of each skill."""
        return pd.Series(self.model.coef_, index=SKILL_METRICS)

    def standardise(self, profiles: pd.DataFrame) -> pd.DataFrame:
        """Z-score using the TRAINING distribution, not the input's own.

        Scoring a new season against its own mean would make the score
        relative to that season rather than to the reference population.
        """
        return (profiles[SKILL_METRICS] - self.means) / self.stds

    def score(self, profiles: pd.DataFrame) -> pd.Series:
        """Predicted wOBA from skills. Interpretable in wOBA units."""
        return pd.Series(self.model.predict(self.standardise(profiles)),
                         index=profiles.index, name="score")


def fit(profiles: pd.DataFrame) -> BatterScore:
    """Learn weights by regressing wOBA on standardised skill rates."""
    q = qualified(profiles)
    means = q[SKILL_METRICS].mean()
    stds = q[SKILL_METRICS].std()

    X = (q[SKILL_METRICS] - means) / stds
    y = q["woba"].astype("float64")

    model = LinearRegression().fit(X, y)
    return BatterScore(model=model, means=means, stds=stds,
                       r_squared=float(model.score(X, y)))


def sensitivity(profiles: pd.DataFrame, n_splits: int = 5,
                seed: int = 42) -> dict:
    """Do the weights and the ranking survive resampling?

    The arbitrary-weight version scored 0.053 here. Anything below ~0.9
    means the score reflects the fitting sample rather than the players.
    """
    from sklearn.model_selection import KFold

    q = qualified(profiles)
    means, stds = q[SKILL_METRICS].mean(), q[SKILL_METRICS].std()
    X = (q[SKILL_METRICS] - means) / stds
    y = q["woba"].astype("float64")

    coefs, ranks = [], []
    for train_idx, _ in KFold(n_splits=n_splits, shuffle=True,
                              random_state=seed).split(X):
        m = LinearRegression().fit(X.iloc[train_idx], y.iloc[train_idx])
        coefs.append(m.coef_)
        ranks.append(pd.Series(m.predict(X), index=q.index).rank(ascending=False))

    coef_df = pd.DataFrame(coefs, columns=SKILL_METRICS)
    rank_corr = pd.DataFrame(ranks).T.corr(method="spearman")

    return {
        "coefficient_mean": coef_df.mean(),
        "coefficient_std": coef_df.std(),
        "min_rank_correlation": float(rank_corr.to_numpy()[
            ~np.eye(n_splits, dtype=bool)].min()),
        "ordering_stable": bool(
            coef_df.abs().rank(axis=1).nunique().eq(1).all()),
    }
