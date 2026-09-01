import pandas as pd
import pytest

from src.utils.temporal import (
    assert_chronological,
    expanding_window_splits,
    split_by_date,
)


def make_df(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"game_date": dates, "value": range(len(dates))})


def test_split_partitions_are_exhaustive_and_disjoint():
    df = make_df(["2024-04-01", "2024-05-01", "2024-06-01", "2024-07-01"])
    s = split_by_date(df, train_end="2024-05-01", validation_end="2024-06-01")

    assert len(s.train) == 2          # April 1, May 1
    assert len(s.validation) == 1     # June 1
    assert len(s.test) == 1           # July 1
    assert len(s.train) + len(s.validation) + len(s.test) == len(df)


def test_boundary_date_belongs_to_the_earlier_partition():
    df = make_df(["2024-05-01"])
    s = split_by_date(df, train_end="2024-05-01", validation_end="2024-06-01")
    assert len(s.train) == 1
    assert len(s.validation) == 0


def test_chronology_check_rejects_overlap():
    train = make_df(["2024-06-01"])
    later = make_df(["2024-05-01"])
    with pytest.raises(ValueError, match="temporal overlap"):
        assert_chronological(train, later)


def test_chronology_check_rejects_same_day_in_both():
    """Same-day overlap is still leakage."""
    train = make_df(["2024-05-01"])
    later = make_df(["2024-05-01"])
    with pytest.raises(ValueError):
        assert_chronological(train, later)


def test_chronology_check_passes_on_clean_split():
    train = make_df(["2024-04-01", "2024-05-01"])
    later = make_df(["2024-06-01"])
    assert_chronological(train, later)  # must not raise


def test_reversed_boundaries_are_rejected():
    df = make_df(["2024-04-01"])
    with pytest.raises(ValueError, match="must precede"):
        split_by_date(df, train_end="2024-06-01", validation_end="2024-05-01")


def test_split_summary_reports_windows():
    df = make_df(["2024-04-01", "2024-05-01", "2024-06-01", "2024-07-01"])
    s = split_by_date(df, train_end="2024-05-01", validation_end="2024-06-01")
    summary = s.summary()

    assert summary["train"]["start"] == "2024-04-01"
    assert summary["train"]["end"] == "2024-05-01"
    assert summary["test"]["rows"] == 1


def test_expanding_window_trains_only_on_the_past():
    df = make_df(["2024-04-01", "2024-05-01", "2024-06-01"])
    pairs = expanding_window_splits(df, ["2024-05-01", "2024-06-01"])

    assert len(pairs) == 2
    assert len(pairs[0][0]) == 1   # trains on April only
    assert len(pairs[1][0]) == 2   # trains on April + May


def test_expanding_window_skips_dates_with_no_history():
    df = make_df(["2024-04-01", "2024-05-01"])
    pairs = expanding_window_splits(df, ["2024-04-01"])
    assert pairs == []


def test_empty_partition_does_not_crash_summary():
    df = make_df(["2024-04-01"])
    s = split_by_date(df, train_end="2024-05-01", validation_end="2024-06-01")
    assert s.summary()["test"]["rows"] == 0
    assert s.summary()["test"]["start"] is None
