"""Chronological splitting for baseball data.

Baseball data is a time series. Random train/test splits let the model
learn from the future, which inflates validation scores and produces a
model that cannot work in deployment.

Every function here enforces one rule:
    no training row may be dated on or after any test row.

Splits are by DATE, never by row index. A plate appearance never spans
two dates, so date-based splitting also prevents a single PA from
landing in both train and test.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

DATE_COL = "game_date"


@dataclass
class TemporalSplit:
    """Three chronologically ordered partitions, plus their provenance.

    The metadata is not decoration: every model must document its
    training, validation, and test windows, and this carries them.
    """

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    date_col: str = DATE_COL
    meta: dict = field(default_factory=dict)

    def summary(self) -> dict:
        """Window boundaries and sizes, for the model card."""
        out = {}
        for name, part in [
            ("train", self.train),
            ("validation", self.validation),
            ("test", self.test),
        ]:
            if len(part) == 0:
                out[name] = {"rows": 0, "start": None, "end": None}
            else:
                dates = pd.to_datetime(part[self.date_col])
                out[name] = {
                    "rows": len(part),
                    "start": str(dates.min().date()),
                    "end": str(dates.max().date()),
                }
        return out


def assert_chronological(train: pd.DataFrame, later: pd.DataFrame,
                         date_col: str = DATE_COL) -> None:
    """Raise if any training row is dated on or after any later row.

    This is the single invariant that makes a split honest. It is cheap
    to check and catastrophic to skip.
    """
    if len(train) == 0 or len(later) == 0:
        return

    train_max = pd.to_datetime(train[date_col]).max()
    later_min = pd.to_datetime(later[date_col]).min()

    if train_max >= later_min:
        raise ValueError(
            f"temporal overlap: training data extends to {train_max.date()} "
            f"but the later partition starts at {later_min.date()}. "
            f"A model trained on this split would see the future."
        )


def split_by_date(
    df: pd.DataFrame,
    train_end: str,
    validation_end: str,
    date_col: str = DATE_COL,
) -> TemporalSplit:
    """Split into train / validation / test at two date boundaries.

    train       : dates <= train_end
    validation  : train_end < dates <= validation_end
    test        : dates > validation_end

    Boundaries are inclusive on the left partition, so a date belongs to
    exactly one partition and no row is silently dropped.
    """
    dates = pd.to_datetime(df[date_col])
    t_end = pd.Timestamp(train_end)
    v_end = pd.Timestamp(validation_end)

    if t_end >= v_end:
        raise ValueError(f"train_end {train_end} must precede validation_end {validation_end}")

    train = df[dates <= t_end]
    validation = df[(dates > t_end) & (dates <= v_end)]
    test = df[dates > v_end]

    if len(train) + len(validation) + len(test) != len(df):
        raise AssertionError("partitions do not sum to the input; a row was lost")

    assert_chronological(train, validation, date_col)
    assert_chronological(validation, test, date_col)
    assert_chronological(train, test, date_col)

    return TemporalSplit(
        train=train,
        validation=validation,
        test=test,
        date_col=date_col,
        meta={"train_end": train_end, "validation_end": validation_end},
    )


def expanding_window_splits(
    df: pd.DataFrame,
    test_dates: list[str],
    date_col: str = DATE_COL,
) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
    """Walk-forward evaluation: for each test date, train on everything before.

    Returns (train, test) pairs. This mirrors deployment — a model in
    production is always trained on the past and scored on what comes
    next — and gives several evaluation points instead of one.

    Test dates with no preceding data are skipped rather than yielding an
    empty training set.
    """
    dates = pd.to_datetime(df[date_col])
    pairs = []

    for d in sorted(test_dates):
        cutoff = pd.Timestamp(d)
        train = df[dates < cutoff]
        test = df[dates == cutoff]

        if len(train) == 0 or len(test) == 0:
            continue

        assert_chronological(train, test, date_col)
        pairs.append((train, test))

    return pairs
