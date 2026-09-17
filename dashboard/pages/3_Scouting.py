"""Scouting reports: how to attack a hitter, how to hit a pitcher."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.data import load
from src.scouting.batter_report import (
    DAMAGE_NOT_MEASURED, INSUFFICIENT, approach_with_damage,
)
from src.scouting.pitcher_report import (
    NOT_MEASURED, hitting_approach,
)

st.set_page_config(page_title="Scouting", page_icon="📋", layout="wide")
st.title("Scouting reports")

st.caption(
    "Every line traces to a measured gap against league, with its sample "
    "size attached. Where the sample is too small the report says so — "
    "**an absent warning is not evidence of safety.**")

side = st.radio("Report type", ["Facing a hitter", "Facing a pitcher"],
                horizontal=True)

if side == "Facing a hitter":
    batters = load("batters")
    pitch_splits = load("batter_pitch_splits")
    pitch_league = load("batter_pitch_league")
    damage = load("batter_damage_splits")
    damage_league = load("batter_damage_league")

    lookup = batters["name"].dropna().sort_values()
    choice = st.selectbox("Hitter", lookup.index,
                          format_func=lambda i: lookup[i])

    st.subheader(f"Pitching plan: {batters.loc[choice, 'name']}")

    recs = approach_with_damage(choice, pitch_splits, pitch_league,
                                damage, damage_league)

    for line in recs:
        if line == INSUFFICIENT:
            st.warning(line)
        elif "AVOID" in line:
            st.error(line)
        elif "chase pitch ONLY" in line:
            st.warning(line)
        elif DAMAGE_NOT_MEASURED in line:
            st.info(line)
        elif "ATTACK" in line:
            st.success(line)
        else:
            st.write(line)

    with st.expander("How to read this"):
        st.markdown("""
| Verdict | Meaning |
|---|---|
| **ATTACK** (green) | Whiffs above league, damage at or below |
| **chase pitch ONLY** (orange) | Whiffs above league BUT punishes contact — keep it out of the zone |
| **AVOID** (red) | Damage above league without the whiffs |
| **DAMAGE NOT MEASURED** (blue) | Below 25 batted balls. **Not the same as safe.** |

Aaron Judge's curveball showed the largest whiff gap of any pitch he
faced and was briefly the only ATTACK recommendation. On 17 batted balls
it barrels at 23.5%, over three times league — below the threshold, so
the risk was simply missing from the report.

Elite hitters frequently have no ATTACK pitch at all. That is a
realistic output, not a failure.
        """)

else:
    pitchers = load("pitchers")
    outcomes = load("pitcher_outcomes")
    out_league = load("pitcher_outcome_league")
    usage = load("pitcher_usage")
    usage_league = load("pitcher_usage_league")["lg_pct"]

    lookup = pitchers["name"].dropna().sort_values()
    choice = st.selectbox("Pitcher", lookup.index,
                          format_func=lambda i: lookup[i])

    st.subheader(f"Hitting plan: {pitchers.loc[choice, 'name']}")

    recs = hitting_approach(choice, outcomes, out_league, usage, usage_league)

    for line in recs:
        if line == INSUFFICIENT:
            st.warning(line)
        elif "OUT PITCH" in line:
            st.error(line)
        elif "Hunt" in line:
            st.success(line)
        elif NOT_MEASURED in line:
            st.info(line)
        elif "sit on it" in line:
            st.success(line)
        else:
            st.write(line)

    with st.expander("How to read this"):
        st.markdown("""
| Line | Meaning |
|---|---|
| **OUT PITCH** (red) | Thrown far more than league with two strikes |
| **Hunt** (green) | Whiffs below league — but check the usage figure |
| **sit on it** (green) | Heavy fastball tendency when behind in the count |
| **NOT MEASURED** (blue) | Too few swings to judge |

**Usage matters as much as weakness.** Tarik Skubal's curveball whiffs
12 points below league, but he throws it 4.2% of the time — once every
25 pitches. Chris Sale's changeup is weaker by less and appears once
every seven. Only the second is something a hitter can plan around.
        """)
