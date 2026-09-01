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
