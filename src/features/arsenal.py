"""Pitcher arsenal: pitch mix, movement, and separation.

Statcast movement (pfx_x) is measured from the CATCHER's perspective, so
a right-hander's sinker and a left-hander's sinker carry opposite signs.
Verified on 2024: CH is +1.18 for LHP and -1.18 for RHP; SI is +1.26 vs
-1.24; ST is -1.16 vs +1.16. Vertical movement (pfx_z) is unaffected —
FF is +1.31 for both hands.

Pooling handedness without normalising would treat a lefty's slider and
a righty's slider as different pitches. `arm_side_movement` flips the
sign for left-handers so that negative means arm-side and positive means
glove-side for every pitcher.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FASTBALLS: tuple[str, ...] = ("FF", "SI", "FC")


def arm_side_movement(df: pd.DataFrame) -> pd.Series:
    """pfx_x expressed from the pitcher's perspective.

    Negative = arm-side, positive = glove-side, for both handedness.
    """
    for col in ("pfx_x", "p_throws"):
        if col not in df.columns:
            raise KeyError(f"expected a '{col}' column")

    pfx = pd.to_numeric(df["pfx_x"], errors="coerce").astype("float64")
    flipped = np.where(df["p_throws"] == "L", -pfx, pfx)
    return pd.Series(flipped, index=df.index, dtype="float64")


def build_arsenal(df: pd.DataFrame, min_pitches: int = 50) -> pd.DataFrame:
    """One row per (pitcher, pitch_type) with usage and shape.

    Pitch types below `min_pitches` are dropped: shape estimates on a
    handful of pitches are noise, and usage% for a pitch thrown twice is
    meaningless.
    """
    work = df[df["pitch_type"].notna()].copy()
    work["pfx_x_arm"] = arm_side_movement(work)

    grouped = (
        work.groupby(["pitcher", "pitch_type"])
        .agg(
            n=("release_speed", "size"),
            velo=("release_speed", "mean"),
            pfx_x=("pfx_x_arm", "mean"),
            pfx_z=("pfx_z", "mean"),
            spin=("release_spin_rate", "mean"),
            extension=("release_extension", "mean"),
        )
    )
    grouped = grouped[grouped["n"] >= min_pitches]

    totals = work.groupby("pitcher").size().rename("total")
    grouped = grouped.join(totals, on="pitcher")
    grouped["usage"] = grouped["n"] / grouped["total"]
    return grouped


def primary_fastball(arsenal: pd.DataFrame, pitcher_id) -> str | None:
    """The pitcher's most-used fastball, or None if they throw none."""
    if pitcher_id not in arsenal.index.get_level_values(0):
        return None
    a = arsenal.loc[pitcher_id]
    present = [p for p in FASTBALLS if p in a.index]
    if not present:
        return None
    return a.loc[present, "usage"].idxmax()


def separation(arsenal: pd.DataFrame, pitcher_id) -> pd.DataFrame | None:
    """Velocity and movement gaps from the primary fastball.

    velo_gap  : fastball mph minus secondary mph
    move_gap  : Euclidean distance in (pfx_x_arm, pfx_z) space

    These are DIFFERENT dimensions and do not move together. Verified on
    2024: Cole Ragans' changeup separates 10.6 mph but only 0.51 in
    movement (a tunnelling pitch), while Dylan Cease's slider separates
    9.2 mph and 1.43 in movement.
    """
    base_type = primary_fastball(arsenal, pitcher_id)
    if base_type is None:
        return None

    a = arsenal.loc[pitcher_id]
    base = a.loc[base_type]

    rows = []
    for pitch_type, r in a.iterrows():
        if pitch_type == base_type:
            continue
        rows.append({
            "fastball": base_type,
            "pitch": pitch_type,
            "usage": r["usage"],
            "velo_gap": base["velo"] - r["velo"],
            "move_gap": float(np.hypot(base["pfx_x"] - r["pfx_x"],
                                       base["pfx_z"] - r["pfx_z"])),
        })
    return pd.DataFrame(rows)


def arsenal_depth(arsenal: pd.DataFrame, min_total: int = 500) -> pd.DataFrame:
    """Number of distinct pitch types per pitcher."""
    depth = arsenal.groupby("pitcher").agg(
        n_pitch_types=("usage", "size"),
        total=("total", "first"),
    )
    return depth[depth["total"] >= min_total]
