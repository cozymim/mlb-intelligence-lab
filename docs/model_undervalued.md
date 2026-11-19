# Undervalued hitters: does skill predict next season beyond regression to the mean?

## Question

A hitter whose skill score (wOBA predicted from chase, zone swing, zone
contact and barrel rates) is well above his actual wOBA looks like a
buy-low candidate. That claim is only worth something if skill predicts
next season's wOBA better than plain regression to the mean, because
every extreme season regresses whether or not a model exists.

## Pre-registered design (written before any result was seen)

**Pairs.** Season t predicts season t+1: 2021->2022, 2022->2023, 2023->2024.
2020 is excluded as a short season.

**Population.** Hitters qualified in season t under the existing
batter-score thresholds, with at least 200 wOBA plate appearances in t+1.

**Leakage rules.** The skill-score weights are refit on season t alone.
The league mean used for regression is season t's, never t+1's.

**Methods compared, all predicting wOBA in t+1:**

| Method | Prediction |
|---|---|
| last_season | wOBA in t, unchanged |
| regressed_k100 / k300 / k600 | wOBA in t shrunk toward the season-t league mean, weight PA / (PA + k) |
| skill_score | wOBA predicted from season-t skill rates |

The shrinkage constant k is not tuned. Three values are reported, and
the skill score is compared against whichever baseline did best in each
pair. Choosing the best baseline after seeing t+1 favours the baselines,
so this comparison is deliberately harder for the model.

**Metric.** Mean absolute error of t+1 wOBA, unweighted.

**Pass criterion.** The skill score must beat the best baseline in all
three pairs. Winning on average while losing a pair is a fail. This is
stricter than the projection system was held to before its cross-season
validation, which it then failed.

**If it fails,** no undervalued-player list is published. The finding
is that public skill rates carry no information about next-season wOBA
beyond regression to the mean, and that is reported as the result.

**If it passes,** the next step tests the list itself: whether hitters
with the largest positive gap (skill minus actual) gained more in t+1
than the best baseline predicted.

## Results (Day 54)

**Verdict: FAIL** under the pre-registered criterion. No undervalued
list is published.

The test was run twice. The first run used Statcast's `woba_value` as
supplied. While checking it, league wOBA came out at .331 for 2023
against .316 on Savant, which led to a definition bug (see
`docs/model_batter_score.md`, Correction). The second run uses the
corrected wOBA. The criterion was not changed between runs.

Corrected run, mean absolute error of t+1 wOBA:

| Pair | n | Best baseline | Baseline MAE | Skill MAE | Skill vs best |
|---|---|---|---|---|---|
| 2021->2022 | 246 | regressed_k600 | 0.0262 | 0.0290 | -10.65% |
| 2022->2023 | 253 | regressed_k300 | 0.0247 | 0.0255 | -3.27% |
| 2023->2024 | 267 | regressed_k600 | 0.0282 | 0.0279 | +0.77% |

Before the fix the same three figures were -11.42%, -3.56% and -0.12%.
The fix improved the skill score in every pair and flipped the sign of
the last one. That is reported, but it is not evidence: one narrow win
out of three is exactly what the criterion was written to reject, and
the projection system's single-season result failed the same way.

**What the skill score does do.** It beats last season's wOBA and the
lightly regressed baseline (k=100) in all three pairs. Skill rates carry
real information about next season.

**What it does not do.** It never clearly beats wOBA regressed hard
toward the league mean (k=300 or 600). Four public skill rates know
about as much as "extreme seasons come back to the middle" and not
reliably more. A list of hitters whose skill outruns their results
would mostly be a list of hitters who had unusual seasons.

**Not tested here, and each would need its own pre-registration:**
Statcast's xwOBA as the skill measure, and a blend of skill score and
regressed wOBA, which could beat both if they carry different
information. A blend's mixing weight would have to be fitted on early
pairs and scored only on a held-out later one.
