"""Hierarchical KBO/MLB strikeout-rate translation.

Only K% is modelled. Day 45 measured cross-league correlations of 0.77
for K%, 0.32 for BB% and 0.28 for ISO: league means shift for all three,
but individual differences survive the move only for strikeouts.
Projecting a KBO hitter's MLB power from his ISO is not supported by
this data.

Structure:

    mu                      league-level shift in log-odds of a strikeout
    delta_i ~ N(mu, tau)    each player's own shift, partially pooled
    K_i ~ Binomial(PA_i, invlogit(mlb_logit_i + delta_i))

Log-odds rather than rates: rates are bounded, log-odds are not, so a
normal hierarchy is appropriate and shrinkage behaves sensibly near 0
and 1.

The binomial carries sample size, so a 117-PA player constrains his own
delta far less than a 2,480-PA one. Measured on 2024 data: Justin Bour
(117 PA) shifted from a raw +0.150 to a posterior -0.135 — the sign
reversed — while Jose Miguel Fernandez (2,480 PA) moved only -0.598 to
-0.582. Correlation between KBO PA and shrinkage: -0.48.

Fitted values (47 players, 100+ PA in both leagues):
    mu  = -0.427  (sd 0.038)
    tau =  0.229  (sd 0.032)

**tau is six times mu's uncertainty.** The league factor is well
determined; an individual's deviation from it is not. Projection
intervals are therefore wide, and that is the honest result rather than
a defect.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_PA = 100

# Posterior summaries from the fit described above. Refitting is in
# notebooks/10_kbo/02_hierarchical.ipynb; these constants let the
# dashboard project without PyMC installed.
MU_MEAN, MU_SD = -0.427, 0.038
TAU_MEAN, TAU_SD = 0.229, 0.032


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def invlogit(x):
    return 1 / (1 + np.exp(-x))


def build_pairs(kbo: pd.DataFrame, mlb: pd.DataFrame,
                min_pa: int = MIN_PA) -> pd.DataFrame:
    """Career totals per player in both leagues, above a PA floor."""
    k = kbo.groupby("player_en")[["pa", "so"]].sum().add_prefix("kbo_")
    m = mlb.groupby("player_en")[["pa", "so"]].sum().add_prefix("mlb_")
    d = k.join(m, how="inner").dropna()
    d = d[(d["kbo_pa"] >= min_pa) & (d["mlb_pa"] >= min_pa)].copy()
    d["kbo_k"] = d["kbo_so"] / d["kbo_pa"]
    d["mlb_k"] = d["mlb_so"] / d["mlb_pa"]
    return d


def expected_kbo_k(mlb_k: float) -> float:
    """KBO strikeout rate implied by an MLB rate, at the posterior mean.

    The ratio is NOT constant: a constant shift in log-odds means 0.69
    at a 15% MLB rate and 0.74 at 35%. Using a single ratio understates
    high-strikeout hitters.
    """
    return float(invlogit(logit(mlb_k) + MU_MEAN))


def project_mlb_k(kbo_k: float, kbo_pa: int, n_draws: int = 8000,
                  seed: int = 42) -> np.ndarray:
    """Posterior draws of MLB K% for a KBO hitter who has never played MLB.

    Three sources of uncertainty, all carried through:
      1. the league factor mu
      2. this player's personal deviation, drawn from N(0, tau)
      3. binomial noise in his observed KBO rate

    The second dominates. At 500 KBO PA the 80% interval spans about 11
    points; at 150 PA it widens only to about 14. **More KBO plate
    appearances barely narrow the projection** — the limit is the number
    of transition players, not the size of any one player's sample.
    """
    rng = np.random.default_rng(seed)
    mu = rng.normal(MU_MEAN, MU_SD, n_draws)
    tau = np.abs(rng.normal(TAU_MEAN, TAU_SD, n_draws))

    obs = rng.binomial(kbo_pa, kbo_k, n_draws) / kbo_pa
    personal = rng.normal(0, tau)
    return invlogit(logit(obs) - mu - personal)


def projection_summary(kbo_k: float, kbo_pa: int,
                       interval: float = 0.80, **kwargs) -> dict:
    draws = project_mlb_k(kbo_k, kbo_pa, **kwargs)
    lo_q = (1 - interval) / 2 * 100
    lo, hi = np.percentile(draws, [lo_q, 100 - lo_q])
    return {
        "kbo_k_pct": kbo_k,
        "kbo_pa": kbo_pa,
        "mlb_k_pct": float(draws.mean()),
        "lower": float(lo),
        "upper": float(hi),
        "interval": interval,
    }
