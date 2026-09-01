"""Feature-level leakage guards.

Temporal splitting (src/utils/temporal.py) prevents learning from the
future. This module prevents learning from the answer.

The core idea is the PREDICTION TIMESTAMP: the moment at which a
prediction must be made. Any column whose value is only knowable after
that moment is banned.

The same column can be legal or illegal depending on the problem.
`launch_speed` is leakage for pitch-outcome prediction (the ball has
already been hit) but a legitimate feature for next-season projection
(it summarises last season's contact quality). Guards are therefore
defined per problem, not globally.
"""

from __future__ import annotations

import pandas as pd

# Everything below is recorded at or after the moment the ball reaches
# the plate. None of it is knowable at release.
POST_PITCH_COLUMNS: frozenset[str] = frozenset({
    # what happened to the pitch
    "description", "type", "events", "des",
    # batted ball measurement
    "launch_speed", "launch_angle", "launch_speed_angle",
    "hit_distance_sc", "hyper_speed", "bb_type",
    "hc_x", "hc_y", "hit_location",
    # MLB's own outcome models, computed from the batted ball
    "estimated_ba_using_speedangle",
    "estimated_slg_using_speedangle",
    "estimated_woba_using_speedangle",
    # linear-weight outcome values
    "woba_value", "woba_denom", "babip_value", "iso_value",
    "delta_run_exp", "delta_home_win_exp",
    # state AFTER the pitch resolved
    "post_away_score", "post_home_score",
    "post_bat_score", "post_fld_score",
})

# Identifiers and bookkeeping. Not leakage, but not features either —
# a model that keys on game_pk has memorised, not learned.
NON_FEATURE_COLUMNS: frozenset[str] = frozenset({
    "game_pk", "at_bat_number", "pitch_number",
    "game_date", "game_year", "game_type",
    "player_name", "sv_id", "spin_dir",
})

# Columns that are empty in every season inspected (verified Day 2).
DEAD_COLUMNS: frozenset[str] = frozenset({
    "spin_rate_deprecated", "break_angle_deprecated",
    "break_length_deprecated", "tfs_deprecated",
    "tfs_zulu_deprecated", "umpire",
})


class LeakageError(ValueError):
    """Raised when a feature matrix contains columns it must not."""


def banned_for_pitch_outcome() -> frozenset[str]:
    """Columns forbidden when predicting the outcome of a pitch.

    Prediction timestamp: the instant of release. Anything measured at
    or after plate crossing is unavailable.
    """
    return POST_PITCH_COLUMNS | NON_FEATURE_COLUMNS | DEAD_COLUMNS


def check_features(
    columns: list[str] | pd.Index,
    banned: frozenset[str],
    context: str = "model",
) -> None:
    """Raise LeakageError if any banned column is present.

    Call this on the feature matrix immediately before fitting. It is
    cheap and it is the last line of defence.
    """
    present = sorted(set(columns) & banned)
    if present:
        raise LeakageError(
            f"{context}: {len(present)} banned column(s) in the feature "
            f"matrix: {present}. These are not knowable at prediction time."
        )


def safe_features(
    df: pd.DataFrame,
    banned: frozenset[str],
    context: str = "model",
) -> pd.DataFrame:
    """Return `df` with banned columns dropped, then verify none remain.

    Convenience wrapper. The verification step is not redundant: it
    catches the case where `banned` is later extended but a cached
    feature matrix is not rebuilt.
    """
    keep = [c for c in df.columns if c not in banned]
    out = df[keep].copy()
    check_features(out.columns, banned, context=context)
    return out


def describe_exclusions(df: pd.DataFrame, banned: frozenset[str]) -> pd.DataFrame:
    """Which columns were excluded and why. Goes into the model card.

    Documenting exclusions is a CLAUDE.md requirement: 'Excluded
    features' is part of every model's record.
    """
    rows = []
    for col in df.columns:
        if col in POST_PITCH_COLUMNS:
            reason = "post-outcome: unknown at prediction time"
        elif col in NON_FEATURE_COLUMNS:
            reason = "identifier or bookkeeping, not a feature"
        elif col in DEAD_COLUMNS:
            reason = "empty in all inspected seasons"
        elif col in banned:
            reason = "banned by this problem's guard"
        else:
            continue
        rows.append({"column": col, "reason": reason})
    return pd.DataFrame(rows).sort_values(["reason", "column"]).reset_index(drop=True)
