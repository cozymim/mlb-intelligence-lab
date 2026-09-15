"""Batter scouting reports generated from measured splits.

Every statement traces to a number that cleared a sample threshold. No
sentence is produced from an unmeasured claim, and when nothing clears
the threshold the report says so.

This matters more than it sounds. Most automated reports always say
something: if a hitter has no weakness, they name the least-bad thing as
one. Juan Soto's 2024 report correctly contains NO pitch to attack —
only pitches to avoid — because nothing exceeded the notability
threshold. Inventing a weakness there would misdirect a pitching plan.

Thresholds:
  50 swings per pitch type, 40 per zone band — below this a whiff rate
  is noise (Day 16 measured whiff-type rates reaching r ~ 0.7 only near
  200 opportunities, so 50 is already generous for a directional read).
  5 percentage points from league before a recommendation is emitted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_SWINGS_PER_PITCH = 50
MIN_SWINGS_PER_ZONE = 40
NOTABLE_GAP = 0.05          # emit an "attack" recommendation above this
AVOID_GAP = -0.03           # emit an "avoid" recommendation below this

ZONE_BANDS = ["below", "low", "middle", "high", "above"]
ZONE_EDGES = [-np.inf, 0.0, 0.33, 0.67, 1.0, np.inf]

INSUFFICIENT = "INSUFFICIENT SAMPLE"


def add_zone_band(df: pd.DataFrame) -> pd.DataFrame:
    """Vertical band relative to each batter's own zone.

    Relative, not absolute: Day 13 measured a 36 cm spread in zone tops
    across hitters, so a fixed height band is not comparable between
    them.
    """
    out = df.copy()
    pz = pd.to_numeric(out["plate_z"], errors="coerce")
    top = pd.to_numeric(out["sz_top"], errors="coerce")
    bot = pd.to_numeric(out["sz_bot"], errors="coerce")
    out["z_rel"] = (pz - bot) / (top - bot)
    out["zone_band"] = pd.cut(out["z_rel"], bins=ZONE_EDGES, labels=ZONE_BANDS)
    return out


def pitch_type_splits(flagged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per (batter, pitch_type) rates, and the league reference."""
    f = flagged[flagged["pitch_type"].notna()]
    sw = f[f["is_swing"]]
    oz = f[~f["in_zone"]]

    splits = pd.DataFrame({
        "pitches": f.groupby(["batter", "pitch_type"]).size(),
        "swings": sw.groupby(["batter", "pitch_type"]).size(),
        "whiffs": sw.groupby(["batter", "pitch_type"])["is_whiff"].sum(),
        "oz_pitches": oz.groupby(["batter", "pitch_type"]).size(),
        "oz_swings": oz.groupby(["batter", "pitch_type"])["is_swing"].sum(),
    }).fillna(0)
    splits["whiff_pct"] = splits["whiffs"] / splits["swings"].replace(0, np.nan)
    splits["chase_pct"] = splits["oz_swings"] / splits["oz_pitches"].replace(0, np.nan)

    league = pd.DataFrame({
        "lg_whiff": sw.groupby("pitch_type")["is_whiff"].mean(),
        "lg_chase": oz.groupby("pitch_type")["is_swing"].mean(),
    })
    return splits, league


def zone_splits(flagged: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Per (batter, zone band) whiff rates, and the league reference."""
    f = add_zone_band(flagged)
    sw = f[f["is_swing"]]

    splits = pd.DataFrame({
        "swings": sw.groupby(["batter", "zone_band"], observed=True).size(),
        "whiffs": sw.groupby(["batter", "zone_band"], observed=True)["is_whiff"].sum(),
    })
    splits["whiff_pct"] = splits["whiffs"] / splits["swings"]
    league = sw.groupby("zone_band", observed=True)["is_whiff"].mean()
    return splits, league


def pitching_approach(
    batter_id,
    pitch_splits: pd.DataFrame,
    pitch_league: pd.DataFrame,
    zone_split: pd.DataFrame,
    zone_league: pd.Series,
) -> list[str]:
    """Recommendations, or INSUFFICIENT SAMPLE, or an explicit 'nothing
    stands out'. Never an invented weakness."""
    recs: list[str] = []

    if batter_id not in pitch_splits.index.get_level_values(0):
        return [INSUFFICIENT]

    bp = pitch_splits.loc[batter_id]
    bp = bp[bp["swings"] >= MIN_SWINGS_PER_PITCH].join(pitch_league)
    if len(bp) == 0:
        return [INSUFFICIENT]

    bp = bp.assign(gap=bp["whiff_pct"] - bp["lg_whiff"])

    for pt, r in bp[bp["gap"] > NOTABLE_GAP].sort_values(
            "gap", ascending=False).head(2).iterrows():
        recs.append(f"Attack with {pt}: whiffs {r['gap']:+.1%} above league "
                    f"({r['whiff_pct']:.1%} on {int(r['swings'])} swings)")

    for pt, r in bp[bp["gap"] < AVOID_GAP].sort_values("gap").head(2).iterrows():
        recs.append(f"Avoid {pt}: whiffs {r['gap']:+.1%} below league "
                    f"({r['whiff_pct']:.1%} on {int(r['swings'])} swings)")

    if batter_id in zone_split.index.get_level_values(0):
        bz = zone_split.loc[batter_id]
        bz = bz[bz["swings"] >= MIN_SWINGS_PER_ZONE]
        if len(bz) > 0:
            gaps = bz["whiff_pct"] - zone_league.reindex(bz.index)
            best = gaps.idxmax()
            if gaps[best] > NOTABLE_GAP:
                recs.append(f"Work {best}: whiffs {gaps[best]:+.1%} above league "
                            f"({int(bz.loc[best, 'swings'])} swings)")

    if not recs:
        recs.append("No significant deviations from league average "
                    "at these sample sizes")
    return recs
