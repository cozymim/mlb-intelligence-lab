"""KBO to MLB strikeout projection.

A prospective scouting tool: enter a KBO hitter's strikeout rate and
plate appearances, get his projected MLB rate with a credible interval.

The interval is the point. Forty-seven transition players cannot support
a precise answer, and presenting one would be false precision.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dashboard.data import load
from src.models.kbo_translation import (
    MU_MEAN, MU_SD, TAU_MEAN, expected_kbo_k, project_mlb_k, projection_summary,
)

st.set_page_config(page_title="KBO scouting", page_icon="🇰🇷", layout="wide")
st.title("KBO to MLB projection")

st.caption(
    "Strikeout rate only. Across 40 transition players, K% correlates "
    "0.77 between leagues; BB% and ISO correlate 0.28-0.32. League means "
    "shift for all three, but only for strikeouts does the ordering of "
    "players survive the move.")

tab_players, tab_calc, tab_evidence, tab_method = st.tabs(
    ["Prospects", "Calculator", "Evidence", "Method and limits"])

with tab_players:
    st.subheader("Current KBO hitters, projected to MLB")

    prospects = load("kbo_prospects")
    career = (prospects.groupby(["player_en", "player_ko"])[["pa", "so"]]
              .sum().reset_index())
    career["kbo_k"] = career["so"] / career["pa"]

    rows = []
    for _, r in career.iterrows():
        s = projection_summary(r["kbo_k"], int(r["pa"]))
        draws = project_mlb_k(r["kbo_k"], int(r["pa"]))
        rows.append({
            "Player": r["player_ko"],
            "Name": r["player_en"],
            "KBO PA": int(r["pa"]),
            "KBO K%": r["kbo_k"],
            "Projected MLB K%": s["mlb_k_pct"],
            "Low": s["lower"],
            "High": s["upper"],
            "P(better than league)": float((draws < 0.225).mean()),
        })

    table = pd.DataFrame(rows).sort_values("Projected MLB K%")
    st.dataframe(
        table.style.format({
            "KBO K%": "{:.1%}", "Projected MLB K%": "{:.1%}",
            "Low": "{:.1%}", "High": "{:.1%}",
            "P(better than league)": "{:.0%}"}),
        use_container_width=True, hide_index=True, height=520)

    st.caption("Sorted by projected MLB strikeout rate. League average is "
               "22.5%. The **Low-High** columns are an 80% credible "
               "interval; **P(better than league)** is the posterior "
               "probability the player would strike out less than an "
               "average MLB hitter.")

    st.error(
        "**The model was fitted on players moving the OTHER direction.** "
        "Its 47 players are MLB hitters who could not hold a job there and "
        "signed in KBO. These prospects would move the opposite way: KBO "
        "stars posted to MLB. Whether the same translation applies to both "
        "groups is untested — the seven Korean position players ever posted "
        "are too few to check. Treat these as illustrative of the method, "
        "not as club-grade projections.")

with tab_calc:
    st.subheader("Project a KBO hitter")

    c1, c2 = st.columns(2)
    kbo_k = c1.slider("KBO strikeout rate", 0.05, 0.35, 0.15, 0.005,
                      format="%.1f%%",
                      help="Strikeouts divided by plate appearances")
    kbo_pa = c2.slider("KBO plate appearances", 100, 2500, 500, 50)

    s = projection_summary(kbo_k, kbo_pa)
    draws = project_mlb_k(kbo_k, kbo_pa)

    m1, m2, m3 = st.columns(3)
    m1.metric("Projected MLB K%", f"{s['mlb_k_pct']:.1%}")
    m2.metric("80% interval",
              f"{s['lower']:.1%} – {s['upper']:.1%}")
    m3.metric("Interval width", f"{(s['upper'] - s['lower']) * 100:.1f} pts")

    LEAGUE_MLB_K = 0.225
    p_worse = float((draws > LEAGUE_MLB_K).mean())
    st.progress(p_worse)
    st.caption(f"**{p_worse:.0%} probability his MLB strikeout rate would "
               f"exceed the league average of {LEAGUE_MLB_K:.1%}.** "
               f"Derived from the posterior, not asserted.")

    hist = pd.DataFrame({"MLB K%": draws})
    st.bar_chart(
        hist["MLB K%"].value_counts(bins=40, sort=False).rename("draws"))
    st.caption("Posterior distribution of the projection.")

    st.divider()
    st.markdown("#### Why the interval is wide")
    st.info(
        f"The league factor is well determined (mu = {MU_MEAN:.3f}, "
        f"sd {MU_SD:.3f}). **How far an individual deviates from it is "
        f"not** (tau = {TAU_MEAN:.3f}) — six times larger. "
        f"With 47 transition players, a narrow interval would be false "
        f"precision.")
    st.warning(
        "**More KBO plate appearances barely help.** 500 PA gives an "
        "11.4-point interval; 150 PA gives 13.7. The uncertainty comes "
        "from not knowing whether THIS player translates typically, not "
        "from measurement error in his KBO rate. Another season of "
        "watching him does not fix that — more players moving between "
        "the leagues would.")

with tab_evidence:
    st.subheader("The 47 players this is built on")

    pairs = load("kbo_pairs")
    show = pairs.copy()
    show["expected_kbo_k"] = show["mlb_k"].map(expected_kbo_k)
    show["residual"] = show["kbo_k"] - show["expected_kbo_k"]
    show = show.sort_values("kbo_pa", ascending=False)

    st.dataframe(
        show[["player_en", "kbo_pa", "kbo_k", "mlb_pa", "mlb_k",
              "expected_kbo_k", "residual"]]
        .style.format({"kbo_k": "{:.1%}", "mlb_k": "{:.1%}",
                       "expected_kbo_k": "{:.1%}", "residual": "{:+.1%}",
                       "kbo_pa": "{:.0f}", "mlb_pa": "{:.0f}"}),
        use_container_width=True, hide_index=True, height=420)

    st.caption("`expected_kbo_k` applies the league factor to the player's "
               "actual MLB rate. `residual` is how far he landed from it — "
               "the spread of that column is what tau measures.")

    st.markdown("#### The ratio is not constant")
    ratio = pd.DataFrame([
        {"MLB K%": f"{k:.0%}", "Implied KBO K%": f"{expected_kbo_k(k):.1%}",
         "Ratio": f"{expected_kbo_k(k) / k:.2f}"}
        for k in [0.15, 0.20, 0.25, 0.30, 0.35]])
    st.dataframe(ratio, use_container_width=True, hide_index=True)
    st.caption("A constant shift in log-odds is not a constant ratio. "
               "Applying a single 0.69 understates high-strikeout hitters "
               "by about 1.8 points at a 35% MLB rate.")

with tab_method:
    st.subheader("Method")
    st.code("""mu                      league shift in log-odds of a strikeout
delta_i ~ N(mu, tau)    each player's own shift, partially pooled
K_i ~ Binomial(PA_i, invlogit(mlb_logit_i + delta_i))""", language="text")

    st.markdown("""
Log-odds rather than rates, because rates are bounded and log-odds are
not, so a normal hierarchy is appropriate and shrinkage behaves sensibly
near the boundaries.

The binomial carries sample size, so a 117-PA player constrains his own
deviation far less than a 2,480-PA one.

**Shrinkage in action.** Justin Bour's raw estimate on 117 KBO plate
appearances says he struck out MORE in Korea. The model pulls him back:
+0.150 becomes -0.135, the sign reversing. Jose Miguel Fernandez, on
2,480, moves only -0.598 to -0.582. Correlation between KBO PA and
shrinkage: -0.48.

An unweighted average would treat those two observations identically.
    """)

    st.markdown("#### Limitations")
    st.error("""
**47 players.** Every interval reflects that.

**Selection bias, unmodelled and running in opposite directions.**
Foreign hitters signed by KBO are MLB players who could not hold a job
there. The seven Koreans posted to MLB were KBO stars. This sample is
almost entirely the first kind, so it may not describe the second.

**Age is a confound.** Nine of eleven players who returned to MLB came
back with a K% at or worse than before — but a KBO stint costs two to
four years, and strikeout rate rises with age. Birth dates are not in
the cached player register, so the two effects are not separable here.

**ABS.** KBO introduced automated ball-strike calling in 2024, and that
cohort shows the sample's lowest K%. Thirteen players is too few to
attribute it. Recorded as an observation, not a finding.

**K% only.** BB% and ISO are not projectable from this data.
    """)
