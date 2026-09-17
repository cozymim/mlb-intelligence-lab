"""Model performance: baselines, results, calibration, and failures.

Day 24 designated this page mandatory and specified it must not be
sanitised. It reports what the models actually did, including where they
lost.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

st.set_page_config(page_title="Model performance", page_icon="📊",
                   layout="wide")
st.title("Model performance")

st.caption("Baselines were fixed before any model was fitted. Building a "
           "baseline after seeing results invites choosing one the model "
           "can beat.")

tab1, tab2, tab3 = st.tabs(
    ["P(Whiff | Swing)", "Season projection", "Evaluation scores"])

with tab1:
    st.subheader("P(Whiff | Swing) — test set")
    st.caption("54,137 September swings. Evaluated ONCE, after every "
               "modelling decision was locked on validation.")

    whiff = pd.DataFrame([
        {"Model": "Constant (league rate)", "Log Loss": 0.55294,
         "Brier": 0.18321, "AUC": None, "ECE": 0.01121},
        {"Model": "Lookup + zone (baseline)", "Log Loss": 0.49466,
         "Brier": 0.16031, "AUC": 0.71292, "ECE": 0.01382},
        {"Model": "Gradient boosting", "Log Loss": 0.44690,
         "Brier": 0.14225, "AUC": 0.77741, "ECE": 0.00954},
    ])
    st.dataframe(whiff, use_container_width=True, hide_index=True)
    st.success("**9.7% better log loss than the baseline**, and better "
               "calibrated.")

    st.markdown("#### What failed")
    st.error(
        "**A linear logistic regression LOST to a two-line groupby.** "
        "0.51151 against the baseline's 0.48524 on validation — worse than "
        "no machine learning at all. `plate_z` correlates +0.21 with whiff "
        "for four-seams and -0.50 for knuckle curves, and one coefficient "
        "cannot represent both.")
    st.info(
        "Adding a `pitch_type x plate_z` interaction recovered it. **That "
        "single change was worth four times the model's eventual margin "
        "over the baseline** — most of the value came from finding the "
        "sign reversal, not from the choice of algorithm.")

    st.markdown("#### Calibration held up")
    st.caption("Validation ECE 0.0058 to test 0.0095, still well below the "
               "baseline's 0.0138. AUC moved 0.77855 to 0.77741 — ranking "
               "ability fully intact.")
    st.caption("September is a different environment: whiff rate is a full "
               "point higher than in validation, and every model degrades "
               "by roughly the same amount. **A random split would have "
               "hidden this entirely.**")

with tab2:
    st.subheader("Season projection — K% and BB%")
    st.caption("Five-fold cross-validated MAE, 254 batters, projecting 2024 "
               "from 2021-2023.")

    proj = pd.DataFrame([
        {"Model": "League average", "K% MAE": 0.0476, "BB% MAE": 0.0220},
        {"Model": "Previous season only", "K% MAE": 0.0287, "BB% MAE": 0.0169},
        {"Model": "Marcel (verified implementation)", "K% MAE": 0.0271,
         "BB% MAE": 0.0144},
        {"Model": "Marcel + Statcast skills", "K% MAE": 0.0265,
         "BB% MAE": 0.0137},
    ])
    st.dataframe(proj, use_container_width=True, hide_index=True)

    st.info("**Marcel beats last-season-only by 5.6% (K%) and 15.4% (BB%). "
            "Skills beat Marcel by a further 2.2% and 4.9%.** Real, but "
            "narrow.")

    st.markdown("#### What failed")
    st.error(
        "**A five-feature skill model gained nothing.** It scored 0.0261 in "
        "training — apparently 3.7% better — and 0.0269 under "
        "cross-validation, identical to Marcel rescaled. All of the "
        "apparent gain was overfitting.")
    st.warning(
        "`whiff_pct` correlates -0.91 with `zone_contact_pct`; `swing_pct` "
        "0.85-0.88 with the swing rates. **Condition number was 14.2, below "
        "the textbook threshold of 30**, and the redundancy still overfit "
        "254 rows. Dropping three features improved the result.")

    st.markdown("#### Where the gain sits")
    quart = pd.DataFrame([
        {"Marcel error quartile": "0.000-0.010", "Mean improvement": -0.0042},
        {"Marcel error quartile": "0.010-0.022", "Mean improvement": -0.0003},
        {"Marcel error quartile": "0.022-0.039", "Mean improvement": 0.0025},
        {"Marcel error quartile": "0.039-0.120", "Mean improvement": 0.0045},
    ])
    st.dataframe(quart, use_container_width=True, hide_index=True)
    st.caption("**Where Marcel is already accurate, skills make it worse.** "
               "The overall gain nets damage to good projections against "
               "repair of bad ones. For acquisition work that is a "
               "favourable trade: a 2-point miss is tolerable, a 12-point "
               "miss changes the decision.")

with tab3:
    st.subheader("Batter and pitcher evaluation scores")

    st.markdown("#### The first version failed its sensitivity test")
    st.error(
        "Equal weights across three axes produced rankings that depended "
        "entirely on the weighting. **Power-heavy and contact-heavy "
        "rankings correlated at Spearman 0.053** and shared two names in "
        "their top tens. The score measured the weighting choice, not the "
        "batter.")

    sens = pd.DataFrame([
        {"Version": "Arbitrary equal weights", "Min rank correlation": 0.053},
        {"Version": "Weights learned from wOBA", "Min rank correlation": 0.990},
    ])
    st.dataframe(sens, use_container_width=True, hide_index=True)

    st.success(
        "Regressing observed wOBA on standardised skill rates anchors the "
        "weights to something external. Rank correlation across 5-fold "
        "resampling rises from 0.053 to 0.990.")

    st.markdown("#### Learned weights")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("**Batters** — wOBA per 1 sd")
        st.dataframe(pd.DataFrame([
            {"Skill": "Barrel%", "Weight": 0.0289},
            {"Skill": "Zone Contact%", "Weight": 0.0184},
            {"Skill": "Chase%", "Weight": -0.0075},
            {"Skill": "Zone Swing%", "Weight": 0.0067},
        ]), use_container_width=True, hide_index=True)
        st.caption("Power carries roughly four times the weight of plate "
                   "discipline. R-squared 0.50.")
    with c2:
        st.caption("**Pitchers** — wOBA allowed per 1 sd")
        st.dataframe(pd.DataFrame([
            {"Skill": "K%", "Weight": -0.0196},
            {"Skill": "Barrel%", "Weight": 0.0106},
            {"Skill": "BB%", "Weight": 0.0098},
            {"Skill": "HardHit%", "Weight": 0.0052},
            {"Skill": "GB%", "Weight": 0.0018},
            {"Skill": "Chase%", "Weight": -0.0007},
        ]), use_container_width=True, hide_index=True)
        st.caption("Strikeouts carry roughly twice the weight of barrel "
                   "suppression. R-squared 0.52.")

    st.info(
        "**R-squared near 0.50 is the honest number.** The unexplained half "
        "includes speed, batted-ball direction, opposing pitcher quality, "
        "park, and luck. A value near 0.9 would suggest outcome information "
        "had leaked into the features. Giancarlo Stanton is the clearest "
        "miss: 20.9% barrel rate, 0.341 wOBA, predicted 0.381 — he is slow, "
        "and the model has no speed input.")
