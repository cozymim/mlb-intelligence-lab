"""Pitch-type outcome profiles with role-appropriate criteria.

Whiff rate is the wrong sole metric for evaluating a pitch. Verified on
2024 (710,632 pitches): the sinker has the LOWEST whiff rate of any
pitch type (11.7%) but the HIGHEST ground-ball rate (57.0%), and a
better xwOBA (0.368) than the four-seam fastball (0.392) which whiffs
1.6x more often.

Ranking pitches by whiff rate inverts the actual outcome ranking.

Four distinct success paths were identified by standardising each
outcome dimension across pitch types:

    ground balls  : SI
    pop-ups       : FF, FC, ST, SV
    swing-and-miss: SL, KC, CU
    chase         : CH, FS

A pitcher throwing 35%+ sinkers (78 of 445 qualified pitchers in 2024)
sits 2 points below league whiff rate but 10 points above in ground-ball
rate. Evaluating them on whiff alone systematically penalises 17.5% of
pitchers for doing their job.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# MLB glossary launch angle bands.
GROUND_BALL_MAX_DEG: float = 10.0
POPUP_MIN_DEG: float = 50.0

OUTCOME_DIMENSIONS = ["whiff_pct", "chase_pct", "gb_pct", "popup_pct"]


def add_batted_ball_types(df: pd.DataFrame) -> pd.DataFrame:
    """Ground ball / pop-up flags from launch angle. Expects BBE rows."""
    out = df.copy()
    la = pd.to_numeric(out["launch_angle"], errors="coerce").astype("float64")
    out["is_ground_ball"] = (la < GROUND_BALL_MAX_DEG).fillna(False)
    out["is_popup"] = (la > POPUP_MIN_DEG).fillna(False)
    return out


def pitch_type_outcomes(
    flagged: pd.DataFrame,
    bbe: pd.DataFrame,
    min_pitches: int = 2000,
    min_bbe: int = 500,
) -> pd.DataFrame:
    """One row per pitch type with plate-discipline and contact outcomes.

    `flagged` needs is_swing / is_whiff / in_zone (add_discipline_flags).
    `bbe` needs is_barrel / is_hard_hit (add_quality_flags on BBE rows).
    """
    f = flagged[flagged["pitch_type"].notna()]

    out = f.groupby("pitch_type").agg(
        pitches=("is_swing", "size"),
        zone_pct=("in_zone", "mean"),
        swing_pct=("is_swing", "mean"),
    )
    out["whiff_pct"] = f[f["is_swing"]].groupby("pitch_type")["is_whiff"].mean()
    out["chase_pct"] = f[~f["in_zone"]].groupby("pitch_type")["is_swing"].mean()

    b = add_batted_ball_types(bbe[bbe["pitch_type"].notna()])
    contact = b.groupby("pitch_type").agg(
        bbe=("is_barrel", "size"),
        gb_pct=("is_ground_ball", "mean"),
        popup_pct=("is_popup", "mean"),
        barrel_pct=("is_barrel", "mean"),
        hard_hit_pct=("is_hard_hit", "mean"),
        avg_ev=("launch_speed", "mean"),
    )

    joined = out.join(contact)
    return joined[(joined["pitches"] >= min_pitches) & (joined["bbe"] >= min_bbe)]


def primary_weapons(outcomes: pd.DataFrame) -> pd.DataFrame:
    """Which outcome dimension each pitch type is best at, standardised.

    Standardising across pitch types is what makes the comparison
    meaningful: raw rates are not comparable across dimensions.
    """
    cols = [c for c in OUTCOME_DIMENSIONS if c in outcomes.columns]
    if not cols:
        raise KeyError(
            f"none of {OUTCOME_DIMENSIONS} are present; got "
            f"{list(outcomes.columns)}. A renamed column would otherwise "
            f"produce an empty frame and an opaque argmax error."
        )

    z = (outcomes[cols] - outcomes[cols].mean()) / outcomes[cols].std()
    z["primary_weapon"] = z.idxmax(axis=1)
    return z
