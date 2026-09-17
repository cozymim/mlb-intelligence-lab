"""Batter profiles: skills, evaluation score, and comparables."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.data import load
from src.models.similarity import (
    SIMILARITY_FEATURES, build_distance_matrix, dimension_dominance, nearest,
)

st.set_page_config(page_title="Batters", page_icon="🏏", layout="wide")
st.title("Batter profiles")

batters = load("batters")
lookup = batters["name"].dropna().sort_values()

choice = st.selectbox("Player", lookup.index, format_func=lambda i: lookup[i])
row = batters.loc[choice]
median = batters.median(numeric_only=True)

st.subheader(row["name"])

SPECS = [
    ("chase_pct", "Chase%", "pct", True),
    ("zone_contact_pct", "Zone Contact%", "pct", False),
    ("barrel_pct", "Barrel%", "pct", False),
    ("woba", "wOBA", "rate", False),
]

cols = st.columns(4)
for col_obj, (metric, label, kind, invert) in zip(cols, SPECS):
    gap = row[metric] - median[metric]
    if kind == "pct":
        value, change = f"{row[metric]:.1%}", f"{gap:+.1%}"
    else:
        value, change = f"{row[metric]:.3f}", f"{gap:+.3f}"
    col_obj.metric(label, value, change,
                   delta_color="inverse" if invert else "normal")

st.caption("Deltas are against the qualified-batter median. Chase% is "
           "inverted: lower is better.")

st.subheader("Sample")
s1, s2, s3 = st.columns(3)
s1.metric("Pitches seen", f"{int(row['pitches']):,}")
s2.metric("Batted ball events", f"{int(row['bbe']):,}")
s3.metric("Swings", f"{int(row['n_swings']):,}")

st.subheader("Most similar batters")

distances = build_distance_matrix(batters)
comps = nearest(choice, distances, batters, n=8)
comps.insert(0, "name", batters.loc[comps.index, "name"])
st.dataframe(comps[["name", "distance"] + SIMILARITY_FEATURES].round(3),
             use_container_width=True, hide_index=True)

dom = dimension_dominance(choice, batters)
top_axis, top_share = dom.index[0], dom.iloc[0]
if top_share > 0.5:
    st.warning(
        f"**{top_share:.0%} of the distance comes from `{top_axis}`.** "
        f"For a player extreme on one axis, similarity becomes a ranking "
        f"on that axis alone.")
else:
    st.caption("Distance contribution: " +
               ", ".join(f"{k} {v:.0%}" for k, v in dom.items()))
