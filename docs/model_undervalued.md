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

## Results

(not yet run)
