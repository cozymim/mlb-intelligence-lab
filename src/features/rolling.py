"""As-of-date player aggregates, computed without leakage.

Column-level guards (src/utils/leakage.py) cannot catch this class of
leakage. A feature named `batter_chase_pct` looks harmless, but if it is
computed over the full season then the pitch being predicted is inside
its own average — and every later pitch is too.

Everything here answers one question: what did we know about this player
BEFORE this pitch?

Two design choices worth stating:

  1. Aggregation is by DATE, not by row. A player's numbers as of a
     given game date use strictly earlier dates. Same-day pitches are
     excluded, because in deployment that day's results are not yet
     compiled when the day's first pitch is thrown.

  2. Early-season estimates are shrunk toward the league mean. With 40
     out-of-zone pitches, a raw Chase% is noise (measured r ~ 0.45 at
     n=50). Shrinkage makes small samples degrade gracefully toward the
     league rate instead of producing confident nonsense.
"""

from __future__ import annotations

import pandas as pd


def shrink(observed: pd.Series, n: pd.Series, league_mean: float,
           regression_pa: float) -> pd.Series:
    """Empirical-Bayes style shrinkage toward the league mean.

    result = (observed * n + league_mean * regression_pa) / (n + regression_pa)

    `regression_pa` is the number of league-average opportunities added
    to every player. It should be near the metric's measured
    stabilization threshold: at n == regression_pa the estimate sits
    halfway between the player and the league.
    """
    # Force float64. Statcast columns arrive as pandas nullable types
    # (Float64/Int64), and arithmetic on them propagates a nullable dtype
    # that pandas later treats as object — describe() then reports
    # unique/top/freq instead of mean/std, and sklearn rejects the column.
    # This is the third dtype-propagation bug in this project; coerce at
    # the boundary rather than debugging it downstream again.
    obs = pd.to_numeric(observed, errors="coerce").astype("float64").fillna(0.0)
    cnt = pd.to_numeric(n, errors="coerce").astype("float64").fillna(0.0)

    numerator = obs * cnt + league_mean * regression_pa
    return (numerator / (cnt + regression_pa)).astype("float64")


def as_of_date_rate(
    df: pd.DataFrame,
    player_col: str,
    numerator_col: str,
    denominator_col: str,
    league_mean: float,
    regression_pa: float,
    date_col: str = "game_date",
) -> pd.Series:
    """Each row's player rate computed from STRICTLY EARLIER dates.

    Returns a Series aligned to `df`'s index. Rows on a player's first
    date get the league mean (no prior data, fully shrunk).

    numerator_col and denominator_col must be boolean columns, e.g.
    is_swing and a not-in-zone flag for Chase%.
    """
    work = df[[player_col, date_col, numerator_col, denominator_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col])

    # Collapse to one row per player-date, then shift so a date sees only
    # dates before it. Doing this at the date level (not the row level)
    # is what excludes same-day information.
    daily = (
        work.groupby([player_col, date_col])[[numerator_col, denominator_col]]
        .sum()
        .sort_index()
    )

    grouped = daily.groupby(level=0)
    prior_num = grouped[numerator_col].cumsum() - daily[numerator_col]
    prior_den = grouped[denominator_col].cumsum() - daily[denominator_col]

    prior_rate = shrink(
        (prior_num / prior_den.replace(0, pd.NA)),
        prior_den,
        league_mean,
        regression_pa,
    )
    prior_rate.name = "value"

    merged = work.join(prior_rate, on=[player_col, date_col])
    return merged["value"]


def add_prior_chase_rate(
    df: pd.DataFrame,
    league_mean: float = 0.282,
    regression_pa: float = 200.0,
    column: str = "batter_prior_chase",
) -> pd.DataFrame:
    """Batter Chase% as known before each pitch's game date.

    Defaults: league mean 0.282 and regression_pa 200 match the 2024
    league Chase% and its measured stabilization threshold.

    Requires is_swing and in_zone columns (see add_discipline_flags).
    """
    for col in ("is_swing", "in_zone", "batter", "game_date"):
        if col not in df.columns:
            raise KeyError(f"expected a '{col}' column")

    work = df.copy()
    work["_oz"] = ~work["in_zone"]
    work["_oz_swing"] = work["is_swing"] & work["_oz"]

    work[column] = as_of_date_rate(
        work,
        player_col="batter",
        numerator_col="_oz_swing",
        denominator_col="_oz",
        league_mean=league_mean,
        regression_pa=regression_pa,
    )
    return work.drop(columns=["_oz", "_oz_swing"])
