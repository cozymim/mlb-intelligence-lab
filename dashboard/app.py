"""MLB Intelligence Lab — dashboard entry point.

Public-data approximation of a Baseball Operations analytics workflow.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.data import available, load

st.set_page_config(page_title="MLB Intelligence Lab", page_icon="⚾",
                   layout="wide")

st.title("MLB Intelligence Lab")
st.caption("A public-data approximation of a Baseball Operations "
           "analytics workflow. 2024 season.")

try:
    batters = load("batters")
    pitchers = load("pitchers")
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Qualified batters", len(batters))
c2.metric("Qualified pitchers", len(pitchers))
c3.metric("Pitches analysed", "710,632")

st.markdown("""
### What this is

Statcast pitch-level data turned into metrics, models, and scouting
recommendations — with every modelling decision documented and every
recommendation traceable to a measured number.

**Use the sidebar to navigate.**

### What it is not

A recreation of a proprietary club system. MLB organisations hold data
unavailable here: full biomechanics, minor league tracking, internal
medical and player development records.
""")

with st.expander("Data tables loaded"):
    st.write(available())
