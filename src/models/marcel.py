"""Marcel baseline projection system.

Tom Tango's system, described by him as "the minimum level of competence
you should expect from any forecaster". Verified against published
sources rather than reconstructed from memory:

  - three prior seasons, weights 5/4/3 with the most recent weighted 5
  - regression toward the league rate worth 100 plate appearances
  - an age adjustment: (age - 29) * 0.003 above 29, * 0.006 below

Pitching uses 3/2/1 and 134 outs, not implemented here.

**The age adjustment is deliberately NOT implemented.** Two reasons:

  1. Birth dates are not in the cached Chadwick columns, so age is
     unavailable.
  2. More importantly, Tango's coefficients were fitted for offensive
     PRODUCTION, which declines after 29. Strikeout rate moves the other
     way — it RISES with age. Applying the production coefficients to
     K% would push the projection in the wrong direction.

Documented as a limitation rather than approximated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BATTING_WEIGHTS: tuple[int, int, int] = (5, 4, 3)
BATTING_REGRESSION_PA: int = 100

# Below this spread a series is treated as constant.
CONSTANT_TOLERANCE: float = 1e-12


def season_lines(pa: pd.DataFrame, pitcher_ids: set | None = None) -> pd.DataFrame:
    """One row per (batter, season) with PA, strikeouts and walks.

    `pitcher_ids` excludes pitchers who took plate appearances. This
    matters far more than it sounds: in 2021, before the universal DH,
    534 of 1,047 "batters" were pitchers. Pitchers strike out at roughly
    twice the rate of hitters, so leaving them in corrupts the league
    rate — and the league rate is what Marcel regresses toward.

    Intentional walks are excluded from the walk count: they reflect the
    opposing manager's decision, not the hitter's plate skill.
    """
    work = pa.copy()
    work["season"] = pd.to_datetime(work["game_date"]).dt.year

    lines = (
        work.groupby(["batter", "season"])["events"]
        .agg(
            pa_count="size",
            k=lambda s: (s == "strikeout").sum(),
            bb=lambda s: (s == "walk").sum(),
        )
        .reset_index()
    )

    if pitcher_ids is not None:
        lines = lines[~lines["batter"].isin(pitcher_ids)]

    return lines.reset_index(drop=True)


def project(
    lines: pd.DataFrame,
    target_season: int,
    stat_col: str,
    weights: tuple[int, ...] = BATTING_WEIGHTS,
    regression_pa: int = BATTING_REGRESSION_PA,
) -> pd.DataFrame:
    """Marcel projection for one counting stat and one target season.

    `stat_col` is a COUNT column ("k", "bb"), not a rate.

    The regression amount is scaled by the weight sum, because the
    weighted numerator and denominator are already inflated by that
    factor. Omitting this makes the regression 12x too weak.
    """
    prior = [target_season - i for i in range(1, len(weights) + 1)]

    num = den = None
    for w, season in zip(weights, prior):
        sub = lines[lines["season"] == season].set_index("batter")
        n, d = sub[stat_col] * w, sub["pa_count"] * w
        num = n if num is None else num.add(n, fill_value=0)
        den = d if den is None else den.add(d, fill_value=0)

    if num is None or len(num) == 0:
        raise ValueError(f"no prior seasons found for {prior}")

    league_rate = float(num.sum() / den.sum())
    reg = regression_pa * sum(weights)

    return pd.DataFrame({
        "projection": (num + league_rate * reg) / (den + reg),
        "weighted_pa": den / sum(weights),
        "league_rate": league_rate,
    })


def evaluate(pred: pd.Series, actual: pd.Series) -> dict:
    """MAE, RMSE and correlation. Correlation is NaN for a constant
    prediction, which is correct rather than an error."""
    err = pred - actual
    corr = np.nan
    # A tolerance, not `> 0`: the standard deviation of a constant series
    # is about 1e-16 rather than exactly zero, which slips past a strict
    # comparison and yields a meaningless correlation near 1e-16.
    if pred.std() > CONSTANT_TOLERANCE and actual.std() > CONSTANT_TOLERANCE:
        corr = float(np.corrcoef(pred, actual)[0, 1])
    return {
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt((err ** 2).mean())),
        "corr": corr,
        "n": int(len(pred)),
    }
