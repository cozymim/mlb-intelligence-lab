import numpy as np
import pandas as pd

from src.data.validation import clean_woba


def _rows():
    return pd.DataFrame({
        "events": ["single", "field_error", "intent_walk", "catcher_interf",
                   "fielders_choice", "strikeout", "walk", "sac_bunt"],
        "woba_value": [0.9, 0.9, 0.7, 0.7, 0.9, 0.9, 0.7, 0.9],
        "woba_denom": [1, 1, 0, 1, 1, 1, np.nan, 0],
    })


def test_only_woba_events_reach_the_numerator():
    out = clean_woba(_rows())
    assert out["woba_value"].tolist() == [0.9, 0, 0, 0, 0, 0, 0.7, 0]


def test_errors_and_fielders_choice_count_as_outs():
    out = clean_woba(_rows())
    assert out["woba_denom"].tolist() == [1, 1, 0, 0, 1, 1, 1, 0]


def test_league_rate_is_not_inflated_by_non_woba_events():
    out = clean_woba(_rows())
    rate = out["woba_value"].sum() / out["woba_denom"].sum()
    assert abs(rate - 1.6 / 5) < 1e-12


def test_input_is_not_modified():
    rows = _rows()
    before = rows.copy()
    clean_woba(rows)
    pd.testing.assert_frame_equal(rows, before)
