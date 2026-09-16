"""Pitcher scouting from the hitter's perspective.

Mirror of the batter report with one structural difference: **a pitcher
chooses what to throw.** A hitter reacts. So usage and count tendency
matter as much as pitch quality — knowing a pitch is weak is useless if
it appears 4% of the time.

Every statement carries its sample size, and pitches below threshold are
reported as NOT MEASURED rather than omitted (Day 39: silence about an
unmeasured risk reads as an absence of risk).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_PITCHES_PER_TYPE = 100
MIN_SWINGS_PER_TYPE = 40
MIN_TWO_STRIKE_PITCHES = 20

NOTABLE_WHIFF_GAP = 0.05
NOTABLE_USAGE_GAP = 0.05
FASTBALL_TELL = 0.55          # fastball share when behind that is exploitable

FASTBALLS = ("FF", "SI", "FC")
INSUFFICIENT = "INSUFFICIENT SAMPLE"
NOT_MEASURED = "NOT MEASURED"


def count_bucket(balls: int, strikes: int) -> str:
    """Tactical count states. Two strikes overrides everything else."""
    if strikes == 2:
        return "two_strike"
    if balls > strikes:
        return "behind"
    if strikes > balls:
        return "ahead"
    return "even"


def add_count_bucket(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    b = pd.to_numeric(out["balls"], errors="coerce").fillna(0).astype(int)
    s = pd.to_numeric(out["strikes"], errors="coerce").fillna(0).astype(int)
    out["count_bucket"] = [count_bucket(x, y) for x, y in zip(b, s)]
    return out


def usage_by_count(flagged: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Pitch mix per (pitcher, count state), and the league reference."""
    f = add_count_bucket(flagged[flagged["pitch_type"].notna()])

    counts = (f.groupby(["pitcher", "count_bucket", "pitch_type"]).size()
              .rename("n").reset_index())
    totals = f.groupby(["pitcher", "count_bucket"]).size().rename("total")
    counts = counts.join(totals, on=["pitcher", "count_bucket"])
    counts["pct"] = counts["n"] / counts["total"]

    league = (f.groupby(["count_bucket", "pitch_type"]).size()
              / f.groupby("count_bucket").size()).rename("lg_pct")
    return counts, league


def pitch_outcomes(flagged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per (pitcher, pitch_type) results, and the league reference."""
    f = flagged[flagged["pitch_type"].notna()]
    sw = f[f["is_swing"]]
    oz = f[~f["in_zone"]]

    out = pd.DataFrame({
        "pitches": f.groupby(["pitcher", "pitch_type"]).size(),
        "swings": sw.groupby(["pitcher", "pitch_type"]).size(),
        "whiffs": sw.groupby(["pitcher", "pitch_type"])["is_whiff"].sum(),
        "zone_pct": f.groupby(["pitcher", "pitch_type"])["in_zone"].mean(),
        "velo": f.groupby(["pitcher", "pitch_type"])["release_speed"]
                 .apply(lambda s: pd.to_numeric(s, errors="coerce").mean()),
    }).fillna(0)
    out["whiff_pct"] = out["whiffs"] / out["swings"].replace(0, np.nan)

    league = pd.DataFrame({
        "lg_whiff": sw.groupby("pitch_type")["is_whiff"].mean(),
        "lg_zone": f.groupby("pitch_type")["in_zone"].mean(),
        "lg_velo": f.groupby("pitch_type")["release_speed"]
                    .apply(lambda s: pd.to_numeric(s, errors="coerce").mean()),
    })
    return out, league


def hitting_approach(
    pitcher_id,
    outcomes: pd.DataFrame,
    outcome_league: pd.DataFrame,
    usage: pd.DataFrame,
    usage_league: pd.Series,
) -> list[str]:
    """What a hitter should do against this pitcher."""
    if pitcher_id not in outcomes.index.get_level_values(0):
        return [INSUFFICIENT]

    o = outcomes.loc[pitcher_id]
    o = o[o["pitches"] >= MIN_PITCHES_PER_TYPE].join(outcome_league)
    if len(o) == 0:
        return [INSUFFICIENT]

    o = o.assign(usage=o["pitches"] / o["pitches"].sum(),
                 wgap=o["whiff_pct"] - o["lg_whiff"])
    recs: list[str] = []

    # Out pitch: most over-used with two strikes relative to league
    ts = usage[(usage["pitcher"] == pitcher_id)
               & (usage["count_bucket"] == "two_strike")
               & (usage["n"] >= MIN_TWO_STRIKE_PITCHES)].copy()
    if len(ts) > 0:
        ts["lg"] = [usage_league.get(("two_strike", pt), np.nan)
                    for pt in ts["pitch_type"]]
        ts["over"] = ts["pct"] - ts["lg"]
        top = ts.nlargest(1, "over").iloc[0]
        if top["over"] > NOTABLE_USAGE_GAP:
            pt = top["pitch_type"]
            wg = o.loc[pt, "wgap"] if pt in o.index else np.nan
            detail = f", whiffs {wg:+.1%} vs league" if pd.notna(wg) else ""
            recs.append(f"OUT PITCH {pt}: {top['pct']:.1%} with two strikes "
                        f"vs league {top['lg']:.1%}{detail} "
                        f"({int(top['n'])} pitches)")

    # Weak offerings — usage is reported because a weak pitch thrown 4%
    # of the time is not actionable.
    weak = o[(o["wgap"] < -NOTABLE_WHIFF_GAP) & (o["swings"] >= MIN_SWINGS_PER_TYPE)]
    for pt, r in weak.sort_values("wgap").iterrows():
        recs.append(f"Hunt {pt}: whiffs {r['wgap']:+.1%} below league, "
                    f"{r['usage']:.1%} usage ({int(r['swings'])} swings)")

    for pt, r in o[o["swings"] < MIN_SWINGS_PER_TYPE].iterrows():
        recs.append(f"{pt}: {NOT_MEASURED} ({int(r['swings'])} swings, "
                    f"need {MIN_SWINGS_PER_TYPE}) — {r['usage']:.1%} usage")

    behind = usage[(usage["pitcher"] == pitcher_id)
                   & (usage["count_bucket"] == "behind")]
    if len(behind) > 0:
        fb = behind[behind["pitch_type"].isin(FASTBALLS)]["pct"].sum()
        if fb > FASTBALL_TELL:
            recs.append(f"Behind in the count: {fb:.1%} fastballs — sit on it")

    return recs or ["No exploitable tendencies at these sample sizes"]
