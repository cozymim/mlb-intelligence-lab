import pandas as pd
import pytest

from src.features.rolling import add_prior_chase_rate, as_of_date_rate, shrink


def frame(specs):
    """specs: list of (batter, date, is_swing, in_zone)."""
    return pd.DataFrame({
        "batter": [s[0] for s in specs],
        "game_date": [s[1] for s in specs],
        "is_swing": [s[2] for s in specs],
        "in_zone": [s[3] for s in specs],
    })


def test_shrinkage_pulls_small_samples_toward_the_league():
    n = pd.Series([10, 1000])
    observed = pd.Series([1.0, 1.0])
    out = shrink(observed, n, league_mean=0.3, regression_pa=200)

    assert out.iloc[0] < 0.35    # 10 opportunities: mostly league
    assert out.iloc[1] > 0.85    # 1000: mostly the player


def test_shrinkage_is_halfway_at_the_regression_constant():
    out = shrink(pd.Series([1.0]), pd.Series([200]),
                 league_mean=0.0, regression_pa=200)
    assert out.iloc[0] == pytest.approx(0.5)


def test_first_date_gets_the_league_mean():
    """No prior data means no player information, fully shrunk."""
    df = frame([(1, "2024-04-01", True, False)])
    out = add_prior_chase_rate(df, league_mean=0.282)
    assert out["batter_prior_chase"].iloc[0] == pytest.approx(0.282)


def test_same_day_pitches_do_not_see_each_other():
    """LEAKAGE TEST. All four pitches are on one date; every one must
    still show the league mean, not a rate built from its neighbours."""
    df = frame([
        (1, "2024-04-01", True, False),
        (1, "2024-04-01", True, False),
        (1, "2024-04-01", True, False),
        (1, "2024-04-01", False, False),
    ])
    out = add_prior_chase_rate(df, league_mean=0.282)
    values = out["batter_prior_chase"].tolist()
    assert values == pytest.approx([0.282] * 4)


def test_later_dates_see_earlier_ones():
    df = frame(
        [(1, "2024-04-01", True, False)] * 300
        + [(1, "2024-04-02", False, False)]
    )
    out = add_prior_chase_rate(df, league_mean=0.282, regression_pa=200)
    day2 = out[out["game_date"] == "2024-04-02"]["batter_prior_chase"].iloc[0]

    # 300 chases out of 300, shrunk with 200 league opportunities
    assert day2 == pytest.approx((300 + 0.282 * 200) / 500, abs=1e-6)
    assert day2 > 0.282   # moved toward the player's actual behaviour


def test_players_do_not_contaminate_each_other():
    df = frame([
        (1, "2024-04-01", True, False),
        (2, "2024-04-01", False, False),
        (1, "2024-04-02", True, False),
        (2, "2024-04-02", True, False),
    ])
    out = add_prior_chase_rate(df, league_mean=0.5, regression_pa=10)
    day2 = out[out["game_date"] == "2024-04-02"].set_index("batter")

    assert day2.loc[1, "batter_prior_chase"] > 0.5   # chased on day 1
    assert day2.loc[2, "batter_prior_chase"] < 0.5   # did not


def test_output_never_depends_on_row_order():
    """Statcast does not arrive sorted; the result must not care."""
    specs = [
        (1, "2024-04-02", True, False),
        (1, "2024-04-01", True, False),
        (1, "2024-04-03", False, False),
    ]
    a = add_prior_chase_rate(frame(specs))
    b = add_prior_chase_rate(frame(list(reversed(specs))))

    a_sorted = a.sort_values("game_date")["batter_prior_chase"].tolist()
    b_sorted = b.sort_values("game_date")["batter_prior_chase"].tolist()
    assert a_sorted == pytest.approx(b_sorted)


def test_in_zone_pitches_are_not_in_the_chase_denominator():
    df = frame([
        (1, "2024-04-01", True, True),    # zone swing, irrelevant
        (1, "2024-04-02", False, False),
    ])
    out = add_prior_chase_rate(df, league_mean=0.4, regression_pa=100)
    day2 = out[out["game_date"] == "2024-04-02"]["batter_prior_chase"].iloc[0]
    assert day2 == pytest.approx(0.4)   # no out-of-zone history yet


def test_missing_columns_raise():
    with pytest.raises(KeyError):
        add_prior_chase_rate(pd.DataFrame({"batter": [1]}))


def test_output_is_float64_not_object():
    """Third dtype-propagation bug in this project. Nullable arithmetic
    silently produces object columns that break describe() and sklearn."""
    df = frame([
        (1, "2024-04-01", True, False),
        (1, "2024-04-02", False, False),
    ])
    out = add_prior_chase_rate(df)
    assert out["batter_prior_chase"].dtype == "float64"


def test_output_is_float64_with_nullable_input():
    """The real pipeline hands us Float64/boolean nullable columns."""
    df = frame([
        (1, "2024-04-01", True, False),
        (1, "2024-04-02", False, False),
    ])
    df["is_swing"] = df["is_swing"].astype("boolean")
    df["in_zone"] = df["in_zone"].astype("boolean")

    out = add_prior_chase_rate(df)
    assert out["batter_prior_chase"].dtype == "float64"
