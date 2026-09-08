import numpy as np
import pandas as pd
import pytest

from src.models.marcel import (
    BATTING_REGRESSION_PA,
    BATTING_WEIGHTS,
    evaluate,
    project,
    season_lines,
)


def lines(rows):
    """rows: (batter, season, pa_count, k, bb)."""
    return pd.DataFrame(rows, columns=["batter", "season", "pa_count", "k", "bb"])


def three_seasons(pa=600, k=120):
    return lines([(1, 2021, pa, k, 50), (1, 2022, pa, k, 50), (1, 2023, pa, k, 50),
                  (2, 2021, pa, k, 50), (2, 2022, pa, k, 50), (2, 2023, pa, k, 50)])


def test_weights_are_the_published_5_4_3():
    assert BATTING_WEIGHTS == (5, 4, 3)
    assert BATTING_REGRESSION_PA == 100


def test_recent_season_is_weighted_most():
    """A player who improved should project closer to the recent season."""
    l = lines([
        (1, 2021, 600, 180, 50),   # 30% K
        (1, 2022, 600, 150, 50),   # 25%
        (1, 2023, 600, 120, 50),   # 20%
        (2, 2021, 600, 150, 50), (2, 2022, 600, 150, 50), (2, 2023, 600, 150, 50),
    ])
    p = project(l, 2024, "k")["projection"]
    # Unweighted mean would be 0.25; 5/4/3 pulls it below that.
    assert p.loc[1] < 0.25


def test_regression_pulls_small_samples_toward_the_league():
    """A 50-PA player should sit much closer to the league rate than a
    600-PA player with the same rate."""
    l = lines([
        (1, 2021, 50, 25, 5), (1, 2022, 50, 25, 5), (1, 2023, 50, 25, 5),
        (2, 2021, 600, 300, 60), (2, 2022, 600, 300, 60), (2, 2023, 600, 300, 60),
        (3, 2021, 600, 60, 60), (3, 2022, 600, 60, 60), (3, 2023, 600, 60, 60),
    ])
    out = project(l, 2024, "k")
    league = out["league_rate"].iloc[0]
    assert abs(out["projection"].loc[1] - league) < abs(out["projection"].loc[2] - league)


def test_regression_is_scaled_by_the_weight_sum():
    """Forgetting to scale makes regression 12x too weak. A 600-PA player
    at 50% K against a ~25% league should land clearly short of 50%."""
    l = lines([
        (1, 2021, 600, 300, 50), (1, 2022, 600, 300, 50), (1, 2023, 600, 300, 50),
        (2, 2021, 600, 60, 50), (2, 2022, 600, 60, 50), (2, 2023, 600, 60, 50),
    ])
    p = project(l, 2024, "k")["projection"].loc[1]
    assert p < 0.49


def test_league_rate_uses_the_weighted_window():
    l = three_seasons(pa=600, k=120)
    out = project(l, 2024, "k")
    assert out["league_rate"].iloc[0] == pytest.approx(0.2)


def test_pitchers_are_excluded_from_season_lines():
    """In 2021, 534 of 1,047 batters were pitchers. They strike out at
    roughly twice the hitter rate and corrupt the league mean."""
    pa = pd.DataFrame({
        "batter": [1, 1, 2, 2],
        "game_date": ["2021-04-01"] * 4,
        "events": ["strikeout", "single", "strikeout", "strikeout"],
    })
    out = season_lines(pa, pitcher_ids={2})
    assert out["batter"].tolist() == [1]


def test_intentional_walks_are_not_counted_as_walks():
    pa = pd.DataFrame({
        "batter": [1, 1],
        "game_date": ["2024-04-01"] * 2,
        "events": ["walk", "intent_walk"],
    })
    out = season_lines(pa)
    assert out["bb"].iloc[0] == 1


def test_missing_prior_seasons_raise():
    with pytest.raises(ValueError, match="no prior seasons"):
        project(three_seasons(), 2030, "k")


def test_evaluate_returns_nan_correlation_for_constant_predictions():
    pred = pd.Series([0.22] * 10)
    actual = pd.Series(np.linspace(0.15, 0.30, 10))
    assert np.isnan(evaluate(pred, actual)["corr"])
