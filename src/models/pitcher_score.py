"""Pitcher evaluation score, weights learned from wOBA allowed.

Symmetric to src/models/batter_score.py: skills in, production out,
weights from regression rather than judgment.

Target is wOBA allowed rather than whiff rate. Day 22 established that
whiff rate inverts the true outcome ordering — the sinker has the lowest
whiff rate in baseball (11.7%) and a better xwOBA than the four-seam
(0.368 vs 0.392) — and that ranking on it penalises 78 of 445 qualified
pitchers for doing their job.

Two skills were dropped for redundancy, following the Day 16 rule that
r > 0.7 means double-weighting:

    whiff_pct   r = 0.82 with k_pct. k_pct is kept: whiffs are one route
                to a strikeout, not the whole of it, and whiff rate
                carries the pitch-type bias above.
    zone_pct    r = -0.54 with bb_pct. Largely the same information
                about command.

Learned weights (2024, 368 qualified pitchers, wOBA allowed per 1 sd):

    k_pct          -0.0196
    barrel_pct     +0.0106
    bb_pct         +0.0098
    hard_hit_pct   +0.0052
    gb_pct         +0.0018
    chase_pct      -0.0007

Strikeouts carry roughly twice the weight of barrel suppression. A
strikeout is a certain out; a batted ball can become a hit.

Sensitivity: 5-fold minimum rank correlation 0.985, coefficient CVs
3-11%.

R-squared 0.524, close to the batter model's 0.501. K% and BB% enter
directly, which risked explaining outcomes with outcomes, but roughly
70% of plate appearances still end on a batted ball where defence and
luck dominate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

PITCHER_SKILLS = ["k_pct", "bb_pct", "chase_pct",
                  "gb_pct", "barrel_pct", "hard_hit_pct"]

# Minimum opportunities per skill denominator. Without these, pitchers
# with two career pitches appear with zone_pct 1.000 and bb_pct 0.667.
QUALIFICATION = {"n_swings": 200, "bbe": 100, "pa": 200}


def build_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Pitcher skill rates plus wOBA allowed, one row per pitcher."""
    from src.data.validation import plate_appearances
    from src.features.batted_ball import add_quality_flags, batted_ball_events
    from src.features.pitch_outcomes import add_batted_ball_types
    from src.features.plate_discipline import add_discipline_flags

    pa = plate_appearances(df)
    f = add_discipline_flags(df)
    bbe = add_batted_ball_types(add_quality_flags(batted_ball_events(df)))

    sw = f[f["is_swing"]]
    oz = f[~f["in_zone"]]
    ends = pa[pa["events"].notna()]

    out = pd.DataFrame({
        "pitches": f.groupby("pitcher").size(),
        "n_swings": sw.groupby("pitcher").size(),
        "n_oz": oz.groupby("pitcher").size(),
        "bbe": bbe.groupby("pitcher").size(),
        "chase_pct": oz.groupby("pitcher")["is_swing"].mean(),
        "gb_pct": bbe.groupby("pitcher")["is_ground_ball"].mean(),
        "barrel_pct": bbe.groupby("pitcher")["is_barrel"].mean(),
        "hard_hit_pct": bbe.groupby("pitcher")["is_hard_hit"].mean(),
        "k_pct": ends.groupby("pitcher")["events"].apply(
            lambda s: (s == "strikeout").mean()),
        "bb_pct": ends.groupby("pitcher")["events"].apply(
            lambda s: s.isin(["walk", "intent_walk"]).mean()),
    })

    woba = pa.groupby("pitcher").agg(
        woba_num=("woba_value", "sum"),
        woba_den=("woba_denom", "sum"),
        pa=("woba_value", "size"))
    woba["woba_against"] = (pd.to_numeric(woba["woba_num"], errors="coerce")
                            / pd.to_numeric(woba["woba_den"], errors="coerce"))

    return out.join(woba[["woba_against", "pa"]])


def qualified(profiles: pd.DataFrame) -> pd.DataFrame:
    mask = profiles["woba_against"].notna()
    for col, minimum in QUALIFICATION.items():
        mask &= profiles[col] >= minimum
    return profiles[mask].copy()


@dataclass
class PitcherScore:
    model: LinearRegression
    means: pd.Series
    stds: pd.Series
    r_squared: float

    @property
    def weights(self) -> pd.Series:
        return pd.Series(self.model.coef_, index=PITCHER_SKILLS)

    def score(self, profiles: pd.DataFrame) -> pd.Series:
        """Predicted wOBA allowed. LOWER is better, unlike the batter score."""
        X = (profiles[PITCHER_SKILLS] - self.means) / self.stds
        return pd.Series(self.model.predict(X), index=profiles.index, name="score")


def fit(profiles: pd.DataFrame) -> PitcherScore:
    q = qualified(profiles)
    means, stds = q[PITCHER_SKILLS].mean(), q[PITCHER_SKILLS].std()
    X = (q[PITCHER_SKILLS] - means) / stds
    y = q["woba_against"].astype("float64")
    model = LinearRegression().fit(X, y)
    return PitcherScore(model=model, means=means, stds=stds,
                        r_squared=float(model.score(X, y)))
