"""Player similarity from standardised skill profiles.

Euclidean distance, not cosine. Cosine measures direction and ignores
magnitude, which is wrong for baseball: Aaron Judge (27.0% barrel) and
Michael Conforto (11.8%) have nearly the same profile SHAPE and cosine
rates them 0.962 similar. They are not similar hitters.

Verified: predicting a player's wOBA from his five nearest neighbours
gives r = 0.567 by Euclidean and 0.538 by cosine (league-mean baseline
MAE 0.0285, Euclidean 0.0239, cosine 0.0246). The baseball judgment and
the measurement agree.

Four features, one per independent dimension. Nine candidates contained
four pairs above |r| = 0.7:

    zone_contact / whiff          -0.921
    hard_hit / avg_exit_velocity  +0.928
    barrel / hard_hit             +0.810
    barrel / avg_exit_velocity    +0.769

Three power metrics clustered at 0.77-0.93. Including them all would
have made three of four dimensions power, and every neighbour of a
slugger would be another slugger.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.preprocessing import StandardScaler

SIMILARITY_FEATURES = [
    "chase_pct",          # plate discipline
    "zone_contact_pct",   # bat-to-ball
    "barrel_pct",         # power
    "avg_launch_angle",   # batted-ball trajectory
]


def build_distance_matrix(profiles: pd.DataFrame,
                          features: list[str] | None = None) -> pd.DataFrame:
    """Pairwise Euclidean distance on standardised features."""
    features = features or SIMILARITY_FEATURES
    X = StandardScaler().fit_transform(
        profiles[features].apply(pd.to_numeric, errors="coerce"))
    return pd.DataFrame(euclidean_distances(X),
                        index=profiles.index, columns=profiles.index)


def nearest(player_id, distances: pd.DataFrame, profiles: pd.DataFrame,
            n: int = 8, features: list[str] | None = None) -> pd.DataFrame:
    """Closest comparables, with the standardised profile attached.

    The z-scores are returned deliberately. For players who are extreme
    on one axis, that axis dominates the distance, and the user needs to
    see which dimension drove the match.
    """
    features = features or SIMILARITY_FEATURES
    if player_id not in distances.index:
        raise KeyError(f"{player_id} not in the distance matrix")

    picks = distances.loc[player_id].drop(player_id).nsmallest(n)
    out = profiles.loc[picks.index, features].copy()
    out.insert(0, "distance", picks.round(3))

    z = ((profiles[features] - profiles[features].mean())
         / profiles[features].std())
    for f in features:
        out[f"z_{f}"] = z.loc[picks.index, f].round(2)
    return out


def dimension_dominance(player_id, profiles: pd.DataFrame,
                        features: list[str] | None = None) -> pd.Series:
    """Share of squared distance contributed by each feature, on average.

    A value near 1.0 means one dimension effectively IS the similarity.
    Judge's barrel z-score is +4.8 against -1.9, -1.2 and +1.3 elsewhere,
    so barrel contributes 23 of 30 squared units — his comparables are
    really just "other players with extreme barrel rates".
    """
    features = features or SIMILARITY_FEATURES
    z = ((profiles[features] - profiles[features].mean())
         / profiles[features].std())
    diffs = (z - z.loc[player_id]) ** 2
    totals = diffs.sum(axis=1).replace(0, np.nan)
    return (diffs.div(totals, axis=0)).mean().sort_values(ascending=False)
