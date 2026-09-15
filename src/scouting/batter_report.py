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


# --- Damage assessment -------------------------------------------------
# Whiff rate alone is dangerously incomplete. Aaron Judge's four-seam
# whiffs at +1.1% above league — apparently harmless — but barrels at
# +20.1%. A whiff-only report marks the most expensive pitch in the
# matchup as unremarkable.
#
# Measured on 2024: whiff gap and barrel gap correlate at only 0.318, so
# roughly 90% of the variance is independent information. 109 of 1,661
# (batter, pitch type) pairs with adequate samples are "low whiff, high
# damage" — 6.6%, and the most costly 6.6% available.

MIN_BBE_PER_PITCH = 25
NOTABLE_BARREL_GAP = 0.05

DAMAGE_NOT_MEASURED = "DAMAGE NOT MEASURED"


def damage_splits(bbe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per (batter, pitch_type) contact quality, and the league reference.

    `bbe` must be batted ball events with quality flags applied.
    """
    b = bbe[bbe["pitch_type"].notna()]

    splits = pd.DataFrame({
        "bbe": b.groupby(["batter", "pitch_type"]).size(),
        "barrels": b.groupby(["batter", "pitch_type"])["is_barrel"].sum(),
        "hard_hits": b.groupby(["batter", "pitch_type"])["is_hard_hit"].sum(),
    })
    splits["barrel_pct"] = splits["barrels"] / splits["bbe"]
    splits["hard_hit_pct"] = splits["hard_hits"] / splits["bbe"]

    league = pd.DataFrame({
        "lg_barrel": b.groupby("pitch_type")["is_barrel"].mean(),
        "lg_hard_hit": b.groupby("pitch_type")["is_hard_hit"].mean(),
    })
    return splits, league


def approach_with_damage(
    batter_id,
    pitch_splits: pd.DataFrame,
    pitch_league: pd.DataFrame,
    damage: pd.DataFrame,
    damage_league: pd.DataFrame,
) -> list[str]:
    """Recommendations accounting for both miss rate and damage.

    Four verdicts:
      ATTACK            whiffs above league, damage at or below
      chase pitch ONLY  whiffs above league BUT punishes contact
      AVOID             damage above league without the whiffs
      DAMAGE NOT MEASURED   below the batted-ball threshold

    The last is not the same as safe. Judge's curveball showed the
    largest whiff gap of any pitch he faced and was the only ATTACK
    recommendation in an earlier version — on 17 batted balls it barrels
    at 23.5%, more than three times league. Silence about an unmeasured
    risk reads as an absence of risk.
    """
    if batter_id not in pitch_splits.index.get_level_values(0):
        return [INSUFFICIENT]

    w = pitch_splits.loc[batter_id]
    w = w[w["swings"] >= MIN_SWINGS_PER_PITCH].join(pitch_league)
    if len(w) == 0:
        return [INSUFFICIENT]
    w = w.assign(gap=w["whiff_pct"] - w["lg_whiff"])

    if batter_id in damage.index.get_level_values(0):
        d = damage.loc[batter_id].join(damage_league)
        d = d.assign(bgap=d["barrel_pct"] - d["lg_barrel"])
    else:
        d = pd.DataFrame(columns=["bbe", "bgap"])

    joined = w.join(d[["bbe", "bgap"]], how="left")
    recs: list[str] = []

    for pt, r in joined.sort_values("gap", ascending=False).iterrows():
        bbe_n = r.get("bbe", np.nan)
        bgap = r.get("bgap", np.nan)
        measured = pd.notna(bbe_n) and bbe_n >= MIN_BBE_PER_PITCH

        if not measured:
            if r["gap"] > NOTABLE_GAP:
                n = 0 if pd.isna(bbe_n) else int(bbe_n)
                recs.append(
                    f"{pt}: whiffs {r['gap']:+.1%} above league "
                    f"({int(r['swings'])} sw) — {DAMAGE_NOT_MEASURED} "
                    f"({n} bbe, need {MIN_BBE_PER_PITCH})")
            continue

        stamp = f"({int(r['swings'])} sw / {int(bbe_n)} bbe)"
        if bgap > NOTABLE_BARREL_GAP:
            kind = "chase pitch ONLY" if r["gap"] > NOTABLE_GAP else "AVOID"
            recs.append(f"{pt}: {kind} — whiffs {r['gap']:+.1%}, "
                        f"barrels {bgap:+.1%} {stamp}")
        elif r["gap"] > NOTABLE_GAP:
            recs.append(f"{pt}: ATTACK — whiffs {r['gap']:+.1%}, "
                        f"barrels {bgap:+.1%} {stamp}")

    return recs or ["No significant deviations at these sample sizes"]
