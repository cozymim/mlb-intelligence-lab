import pandas as pd
import pytest

from src.features.plate_discipline import (
    SWING_DESCRIPTIONS,
    WHIFF_DESCRIPTIONS,
    BUNT_DESCRIPTIONS,
    add_swing_flags,
    whiff_rate,
    swing_rate,
    swinging_strike_rate,
)


def test_whiffs_are_a_subset_of_swings():
    """A whiff that is not a swing would make the rate exceed 1.0."""
    assert WHIFF_DESCRIPTIONS <= SWING_DESCRIPTIONS


def test_foul_tip_is_a_swing_but_not_a_whiff():
    """Bat contact occurred, so it cannot count as a miss."""
    assert "foul_tip" in SWING_DESCRIPTIONS
    assert "foul_tip" not in WHIFF_DESCRIPTIONS


def test_bunts_are_in_neither_set():
    assert BUNT_DESCRIPTIONS.isdisjoint(SWING_DESCRIPTIONS)
    assert BUNT_DESCRIPTIONS.isdisjoint(WHIFF_DESCRIPTIONS)


def test_rates_on_a_known_frame():
    df = pd.DataFrame({"description": [
        "ball",
        "called_strike",
        "foul",              # swing, no whiff
        "swinging_strike",   # swing + whiff
        "hit_into_play",     # swing, no whiff
        "foul_tip",          # swing, no whiff
        "missed_bunt",       # neither
    ]})
    # 4 swings out of 7 pitches, 1 whiff
    assert swing_rate(df) == pytest.approx(4 / 7)
    assert whiff_rate(df) == pytest.approx(1 / 4)
    assert swinging_strike_rate(df) == pytest.approx(1 / 7)


def test_whiff_rate_is_nan_without_swings():
    df = pd.DataFrame({"description": ["ball", "called_strike"]})
    assert pd.isna(whiff_rate(df))


def test_input_is_not_mutated():
    df = pd.DataFrame({"description": ["ball", "foul"]})
    before = list(df.columns)
    add_swing_flags(df)
    assert list(df.columns) == before


def test_missing_description_raises():
    with pytest.raises(KeyError):
        add_swing_flags(pd.DataFrame({"pitch_type": ["FF"]}))

def test_sql_fragments_are_deterministic():
    """Unsorted set iteration would break query caching and diffs."""
    from src.features.plate_discipline import swing_sql
    assert swing_sql() == swing_sql()


def test_sql_lists_match_the_python_sets():
    """The generated SQL must contain exactly the documented values."""
    from src.features.plate_discipline import (
        SWING_DESCRIPTIONS, WHIFF_DESCRIPTIONS, swing_sql, whiff_sql,
    )
    for v in SWING_DESCRIPTIONS:
        assert f"'{v}'" in swing_sql()
    for v in WHIFF_DESCRIPTIONS:
        assert f"'{v}'" in whiff_sql()
    # foul_tip is a swing but must never appear as a whiff
    assert "'foul_tip'" in swing_sql()
    assert "'foul_tip'" not in whiff_sql()


def test_sql_uses_the_given_column_name():
    from src.features.plate_discipline import swing_sql
    assert swing_sql("d") .startswith("d IN (")
