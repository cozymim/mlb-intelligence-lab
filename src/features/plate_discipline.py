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
