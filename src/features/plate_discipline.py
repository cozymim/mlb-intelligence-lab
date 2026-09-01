"""Plate discipline metrics derived from Statcast `description`.

Definitions and rationale are documented in docs/data_dictionary.md.
These sets are the single source of truth.
"""

from __future__ import annotations

import pandas as pd

SWING_DESCRIPTIONS: frozenset[str] = frozenset({
    "foul",
    "hit_into_play",
    "swinging_strike",
    "swinging_strike_blocked",
    "foul_tip",
})

WHIFF_DESCRIPTIONS: frozenset[str] = frozenset({
    "swinging_strike",
    "swinging_strike_blocked",
})

BUNT_DESCRIPTIONS: frozenset[str] = frozenset({
    "foul_bunt",
    "missed_bunt",
})

NO_PITCH_DESCRIPTIONS: frozenset[str] = frozenset({
    "automatic_ball",
})


def add_swing_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with boolean swing/whiff/bunt columns added."""
    if "description" not in df.columns:
        raise KeyError("expected a 'description' column")

    out = df.copy()
    out["is_swing"] = out["description"].isin(SWING_DESCRIPTIONS)
    out["is_whiff"] = out["description"].isin(WHIFF_DESCRIPTIONS)
    out["is_bunt"] = out["description"].isin(BUNT_DESCRIPTIONS)
    return out


def swing_rate(df: pd.DataFrame) -> float:
    """Swings / total pitches."""
    return add_swing_flags(df)["is_swing"].mean()


def whiff_rate(df: pd.DataFrame) -> float:
    """Whiffs / swings. Returns NaN when there are no swings."""
    flagged = add_swing_flags(df)
    swings = flagged["is_swing"].sum()
    if swings == 0:
        return float("nan")
    return flagged["is_whiff"].sum() / swings


def swinging_strike_rate(df: pd.DataFrame) -> float:
    """Whiffs / total pitches. Different denominator from whiff_rate."""
    return add_swing_flags(df)["is_whiff"].mean()


def _sql_in_list(values: frozenset[str]) -> str:
    """Render a frozenset as a deterministic SQL IN-list.

    Sorted so the generated SQL is stable across runs — unsorted set
    iteration would produce a different string each time, which makes
    query caching and diffs useless.
    """
    quoted = ", ".join(f"'{v}'" for v in sorted(values))
    return f"({quoted})"


def swing_sql(column: str = "description") -> str:
    """SQL boolean expression that is true when a swing occurred."""
    return f"{column} IN {_sql_in_list(SWING_DESCRIPTIONS)}"


def whiff_sql(column: str = "description") -> str:
    """SQL boolean expression that is true when the batter swung and missed."""
    return f"{column} IN {_sql_in_list(WHIFF_DESCRIPTIONS)}"


def swing_count_sql(column: str = "description", alias: str = "swings") -> str:
    """Conditional-count fragment for a SELECT list."""
    return f"SUM(CASE WHEN {swing_sql(column)} THEN 1 ELSE 0 END) AS {alias}"


def whiff_count_sql(column: str = "description", alias: str = "whiffs") -> str:
    """Conditional-count fragment for a SELECT list."""
    return f"SUM(CASE WHEN {whiff_sql(column)} THEN 1 ELSE 0 END) AS {alias}"


# --- Zone-based metrics -------------------------------------------------
# These require the strike zone definition from src/features/strike_zone.py
# and therefore depend on plate_x/plate_z/sz_top/sz_bot being present.

def add_discipline_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add swing/whiff/bunt flags plus the in-zone flag in one pass.

    Convenience wrapper so callers do not import two modules and risk
    applying them in the wrong order.
    """
    from src.features.strike_zone import in_strike_zone

    out = add_swing_flags(df)
    out["in_zone"] = in_strike_zone(df)
    return out


def chase_rate(df: pd.DataFrame) -> float:
    """Swings at pitches outside the zone / pitches outside the zone.

    Low is good: the hitter is not being fooled by balls.
    """
    f = add_discipline_flags(df)
    out_of_zone = ~f["in_zone"]
    n = out_of_zone.sum()
    if n == 0:
        return float("nan")
    return (f["is_swing"] & out_of_zone).sum() / n


def zone_swing_rate(df: pd.DataFrame) -> float:
    """Swings at pitches in the zone / pitches in the zone.

    High is generally good: the hitter attacks hittable pitches.
    """
    f = add_discipline_flags(df)
    n = f["in_zone"].sum()
    if n == 0:
        return float("nan")
    return (f["is_swing"] & f["in_zone"]).sum() / n


def contact_rate(df: pd.DataFrame) -> float:
    """1 - whiff rate. Contact made per swing."""
    f = add_swing_flags(df)
    swings = f["is_swing"].sum()
    if swings == 0:
        return float("nan")
    return 1.0 - (f["is_whiff"].sum() / swings)


def zone_contact_rate(df: pd.DataFrame) -> float:
    """Contact on swings at pitches in the zone.

    Isolates bat-to-ball skill from pitch selection: a hitter who chases
    constantly will have a poor overall contact rate even with good bat
    control, because bad pitches are harder to hit.
    """
    f = add_discipline_flags(df)
    zone_swings = f["is_swing"] & f["in_zone"]
    n = zone_swings.sum()
    if n == 0:
        return float("nan")
    return 1.0 - (f["is_whiff"] & zone_swings).sum() / n


def discipline_profile(df: pd.DataFrame, min_pitches: int = 0) -> dict:
    """All plate discipline rates in one dict, with sample sizes.

    Sample counts are returned alongside every rate — a rate without its
    denominator cannot be interpreted.
    """
    f = add_discipline_flags(df)
    n = len(f)

    if n < min_pitches:
        return {"pitches": n, "insufficient_sample": True}

    in_zone = f["in_zone"]
    swings = f["is_swing"]

    return {
        "pitches": n,
        "zone_pct": in_zone.mean() if n else float("nan"),
        "swing_pct": swings.mean() if n else float("nan"),
        "chase_pct": chase_rate(df),
        "zone_swing_pct": zone_swing_rate(df),
        "contact_pct": contact_rate(df),
        "zone_contact_pct": zone_contact_rate(df),
        "whiff_pct": whiff_rate(df),
        "n_out_of_zone": int((~in_zone).sum()),
        "n_in_zone": int(in_zone.sum()),
        "n_swings": int(swings.sum()),
        "n_zone_swings": int((swings & in_zone).sum()),
    }
