"""Batted ball quality metrics.

Official MLB/Statcast definitions, verified against the glossary:
  Hard Hit  : exit velocity >= 95 mph
  Sweet Spot: launch angle 8-32 degrees
  Barrel    : EV/LA combinations historically yielding >= .500 AVG and
              >= 1.500 SLG. Requires EV >= 98 mph; the qualifying launch
              angle band widens as EV rises (26-30 at 98, 25-31 at 99,
              24-33 at 100, 8-50 at 116).

We do NOT reimplement Barrel. MLB's published description specifies the
band only at 98, 99, 100 and 116 mph; between 100 and 116 it says the
range grows "two to three degrees" per mph without saying which. The
definition is not fully reconstructible from public documentation.

Statcast supplies the classification in `launch_speed_angle`, where 6 is
Barrel. Verified against the glossary bands on 2024 data: 98.3% / 97.8%
/ 98.5% / 100.0% agreement at 98 / 99 / 100 / 116 mph.
"""

from __future__ import annotations

import pandas as pd

HARD_HIT_MPH: float = 95.0
SWEET_SPOT_DEG: tuple[float, float] = (8.0, 32.0)
BARREL_CODE: int = 6


def batted_ball_events(df: pd.DataFrame) -> pd.DataFrame:
    """Rows that are true batted ball events (BBE).

    Fouls are excluded. This matters enormously: fouls carry a measured
    launch_speed (mean 76.2 mph in 2024) but are not BBE. Including them
    dropped league HardHit% from 39.0% to 23.8% and average exit velocity
    from 88.3 to 82.5 mph — both far outside published league values.

    Requires both launch_speed and launch_angle to be present.
    """
    return df[
        (df["description"] == "hit_into_play")
        & df["launch_speed"].notna()
        & df["launch_angle"].notna()
    ].copy()


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add hard-hit / sweet-spot / barrel flags. Expects BBE rows."""
    out = df.copy()
    ev = pd.to_numeric(out["launch_speed"], errors="coerce")
    la = pd.to_numeric(out["launch_angle"], errors="coerce")

    out["is_hard_hit"] = (ev >= HARD_HIT_MPH).fillna(False)
    out["is_sweet_spot"] = la.between(*SWEET_SPOT_DEG).fillna(False)
    out["is_barrel"] = (out["launch_speed_angle"] == BARREL_CODE).fillna(False)
    return out


def quality_profile(df: pd.DataFrame, min_bbe: int = 0) -> dict:
    """Contact quality rates over batted ball events, with sample size.

    Pass raw pitch-level data; BBE filtering happens here so callers
    cannot accidentally include fouls in the denominator.
    """
    bbe = add_quality_flags(batted_ball_events(df))
    n = len(bbe)

    if n < min_bbe:
        return {"bbe": n, "insufficient_sample": True}
    if n == 0:
        return {"bbe": 0, "insufficient_sample": True}

    return {
        "bbe": n,
        "barrel_pct": bbe["is_barrel"].mean(),
        "hard_hit_pct": bbe["is_hard_hit"].mean(),
        "sweet_spot_pct": bbe["is_sweet_spot"].mean(),
        "avg_exit_velocity": pd.to_numeric(bbe["launch_speed"]).mean(),
        "max_exit_velocity": pd.to_numeric(bbe["launch_speed"]).max(),
        "avg_launch_angle": pd.to_numeric(bbe["launch_angle"]).mean(),
    }
