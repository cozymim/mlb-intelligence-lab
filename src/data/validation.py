"""Invariant checks on Statcast pitch data.

Each function encodes a fact verified in docs/data_dictionary.md.
They exist so that a silent data change becomes a loud failure.
"""

from __future__ import annotations

import pandas as pd

PA_KEYS = ["game_pk", "at_bat_number"]
SORT_KEYS = ["game_pk", "at_bat_number", "pitch_number"]


def sort_chronologically(df: pd.DataFrame) -> pd.DataFrame:
    """Sort into true pitch order. Required before any temporal operation."""
    return df.sort_values(SORT_KEYS).reset_index(drop=True)


def check_first_pitch_counts(df: pd.DataFrame) -> None:
    """Every plate appearance must begin at 0-0.

    Verified on 2024-04-15: 1,111 of 1,111 first pitches were 0-0.
    """
    first = df[df["pitch_number"] == 1]
    bad = first[(first["balls"] != 0) | (first["strikes"] != 0)]
    if len(bad) > 0:
        raise ValueError(
            f"{len(bad)} first pitches do not start at 0-0. "
            f"Either the data is corrupt or pitch_number is not what we think."
        )


def count_incomplete_pas(df: pd.DataFrame) -> int:
    """Number of plate appearances that end without an `events` value."""
    last_idx = df.groupby(PA_KEYS)["pitch_number"].idxmax()
    return int(df.loc[last_idx, "events"].isna().sum())


def plate_appearances(df: pd.DataFrame, drop_incomplete: bool = True) -> pd.DataFrame:
    """One row per completed plate appearance (the final pitch of each).

    Incomplete PAs are dropped by default, but the count is never lost:
    it is attached as an attribute on the result.
    """
    last_idx = df.groupby(PA_KEYS)["pitch_number"].idxmax()
    result = df.loc[last_idx].copy()

    dropped = int(result["events"].isna().sum())
    if drop_incomplete:
        result = result[result["events"].notna()]

    result.attrs["incomplete_pas_dropped"] = dropped
    return result


# wOBA's definition counts only these events in the numerator. Statcast's
# woba_value also credits reaching on error, fielder's choice, catcher's
# interference, intentional walks and some bunts and dropped third strikes.
# Left in, they raised 2023 league wOBA from about .322 to .331 and credited
# hitters for fielders' mistakes, which falls hardest on ground-ball and
# fast hitters.
WOBA_EVENTS = frozenset({"walk", "hit_by_pitch", "single", "double",
                         "triple", "home_run"})

# Events that are not wOBA plate appearances at all. Everything else,
# including reaching on error and fielder's choice, counts as an out.
NOT_IN_WOBA_DENOMINATOR = frozenset({"intent_walk", "sac_bunt",
                                     "catcher_interf", "truncated_pa"})


def clean_woba(pa):
    """Return a copy of plate-appearance rows with woba_value and
    woba_denom recomputed to the standard wOBA definition.

    Event weights are still Statcast's (0.9 for a single and so on),
    which are rounded versions of the season-specific linear weights.
    """
    import pandas as pd

    out = pa.copy()
    events = out["events"]
    value = pd.to_numeric(out["woba_value"], errors="coerce").fillna(0.0)
    out["woba_value"] = value.where(events.isin(WOBA_EVENTS), 0.0)
    out["woba_denom"] = (~events.isin(NOT_IN_WOBA_DENOMINATOR)).astype("float64")
    return out
