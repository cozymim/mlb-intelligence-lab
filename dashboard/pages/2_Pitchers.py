"""Pitcher profiles: arsenal, outcomes, and count tendency."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.data import load

st.set_page_config(page_title="Pitchers", page_icon="⚾", layout="wide")
st.title("Pitcher profiles")

pitchers = load("pitchers")
outcomes = load("pitcher_outcomes")
out_league = load("pitcher_outcome_league")
usage = load("pitcher_usage")
usage_league = load("pitcher_usage_league")

lookup = pitchers["name"].dropna().sort_values()
choice = st.selectbox("Player", lookup.index, format_func=lambda i: lookup[i])
row = pitchers.loc[choice]
median = pitchers.median(numeric_only=True)

st.subheader(row["name"])

SPECS = [
    ("k_pct", "K%", False),
    ("bb_pct", "BB%", True),
    ("barrel_pct", "Barrel% allowed", True),
    ("gb_pct", "Ground ball%", False),
]
cols = st.columns(4)
for col_obj, (metric, label, invert) in zip(cols, SPECS):
    gap = row[metric] - median[metric]
    col_obj.metric(label, f"{row[metric]:.1%}", f"{gap:+.1%}",
                   delta_color="inverse" if invert else "normal")

st.caption("Deltas against the qualified-pitcher median. BB% and Barrel% "
           "are inverted: lower is better. "
           "**Whiff rate is deliberately absent** — it inverts the true "
           "outcome ranking, penalising sinker-heavy pitchers for doing "
           "their job.")

# --- arsenal
st.subheader("Arsenal")

if choice in outcomes.index.get_level_values(0):
    arsenal = outcomes.loc[choice].join(out_league)
    arsenal = arsenal[arsenal["pitches"] >= 100].copy()
    arsenal["usage"] = arsenal["pitches"] / arsenal["pitches"].sum()
    arsenal["velo_vs_lg"] = arsenal["velo"] - arsenal["lg_velo"]
    arsenal["whiff_vs_lg"] = arsenal["whiff_pct"] - arsenal["lg_whiff"]

    show = arsenal.sort_values("usage", ascending=False)[
        ["usage", "velo", "velo_vs_lg", "zone_pct",
         "whiff_pct", "whiff_vs_lg", "swings"]]
    st.dataframe(
        show.style.format({
            "usage": "{:.1%}", "velo": "{:.1f}", "velo_vs_lg": "{:+.1f}",
            "zone_pct": "{:.1%}", "whiff_pct": "{:.1%}",
            "whiff_vs_lg": "{:+.1%}", "swings": "{:.0f}"}),
        use_container_width=True)

    thin = arsenal[arsenal["swings"] < 40]
    if len(thin):
        st.info("Not enough swings to judge: " +
                ", ".join(f"{pt} ({int(r['swings'])})"
                          for pt, r in thin.iterrows()) +
                ". **Absence of a warning here is not evidence of safety.**")
else:
    st.warning("INSUFFICIENT SAMPLE")

# --- count tendency
st.subheader("Pitch mix by count")

u = usage[usage["pitcher"] == choice]
if len(u):
    pivot = u.pivot_table(index="pitch_type", columns="count_bucket",
                          values="pct", aggfunc="first")
    order = [c for c in ["behind", "even", "ahead", "two_strike"]
             if c in pivot.columns]
    pivot = pivot[order].dropna(how="all")

    lg = usage_league.reset_index()
    lg_pivot = lg.pivot_table(index="pitch_type", columns="count_bucket",
                              values="lg_pct", aggfunc="first")[order]

    diff = (pivot - lg_pivot.reindex(pivot.index)).dropna(how="all")
    st.dataframe(diff.style.format("{:+.1%}", na_rep="—")
                 .background_gradient(cmap="RdBu_r", vmin=-0.2, vmax=0.2),
                 use_container_width=True)
    st.caption("Difference from league usage in each count state. Positive "
               "means thrown more often than league. The two-strike column "
               "identifies the out pitch.")

    fastballs = u[(u["count_bucket"] == "behind")
                  & u["pitch_type"].isin(["FF", "SI", "FC"])]["pct"].sum()
    if fastballs > 0.55:
        st.warning(f"**Behind in the count: {fastballs:.1%} fastballs.** "
                   f"League is about 54.5%.")
else:
    st.warning("INSUFFICIENT SAMPLE")
