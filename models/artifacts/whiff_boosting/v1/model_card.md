# Model Card — P(Whiff | Swing) v1

## What this predicts

Given that a batter swings, the probability the swing misses entirely.

Swing and whiff definitions from `src/features/plate_discipline.py`,
tested and documented: foul tips are swings but NOT whiffs (the bat made
contact); bunts are excluded from both.

## Baseball question and use

**Question.** Which pitches, in which locations and counts, generate
swing-and-miss?

**Who would use it.** Advance scouting and pitching strategy. The output
is a probability attached to a pitch type in a location, which supports
questions like "does this hitter's chase profile leave him exposed to
sliders below the zone".

**Decision it supports.** Pitch selection and location planning against
a specific hitter. It does NOT decide anything on its own; it quantifies
one dimension of pitch effectiveness. A sinker scores badly here by
design because it exists to induce ground balls (see Day 22).

**Prediction timestamp.** The moment of release. Only information
available before the ball reaches the plate is used.

## Data and splits

2024 regular season, 338,364 swings from 710,632 pitches.

| Split | Rows | Dates | Whiff rate |
|---|---|---|---|
| Train | 200,735 | 03-28 to 07-14 | 23.01% |
| Validation | 83,492 | 07-19 to 08-31 | 23.12% |
| Test | 54,137 | 09-01 to 09-29 | **24.13%** |

Chronological, by date, via `src/utils/temporal.py`, which raises if any
training row is dated at or after any later partition. The four-day
train/validation gap is the All-Star break.

**The test set is a different environment.** September whiff rate is a
full point higher — expanded rosters, fatigue, playoff-race bullpen
usage are candidates. A random split would have hidden this entirely.

**The test set was evaluated once**, after all modelling decisions were
made on validation.

## Model

`HistGradientBoostingClassifier`, 292 iterations (early stopping),
learning rate 0.06, 31 leaf nodes, L2 1.0, seed 42.

**Not calibrated.** Isotonic regression made it worse (ECE 0.00575 to
0.00667). Boosting predicts each leaf's observed rate and is already
well calibrated. The logistic model needed calibration; this one does
not. Calibration is diagnosed per model, never applied by default.

### Features (31)

Numeric: plate_x_bat, plate_z_rel, release_speed, pfx_x, pfx_z,
release_spin_rate, release_extension, balls, strikes.
Categorical: pitch_type (bucketed), stand, p_throws.
Plus pitch_type x plate_z_rel interactions (near-worthless for trees;
retained from the logistic model, importance 0.0008).

`plate_x_bat` flips sign for left-handed batters so positive means away.
`plate_z_rel` is height relative to each batter's own zone, since zone
tops vary by 36 cm across hitters (Day 13).

### Excluded features

41 of 119 columns are blocked by `src/utils/leakage.py`: 26
post-outcome (launch_speed, events, estimated_woba_using_speedangle,
delta_run_exp, post_*_score, and the `type` column), 9 identifiers, 6
empty in all seasons. `check_features()` runs on the matrix immediately
before fitting and names any offender.

**No player-identity features.** The model knows nothing about who threw
the pitch or who swung.

## Results — TEST SET

| Model | Log Loss | Brier | AUC | ECE |
|---|---|---|---|---|
| Constant (league rate) | 0.55294 | 0.18321 | — | 0.01121 |
| Lookup + zone baseline | 0.49466 | 0.16031 | 0.71292 | 0.01382 |
| **Boosting** | **0.44690** | **0.14225** | **0.77741** | **0.00954** |

**9.7% better log loss than the baseline**, and better calibrated.

### Held up from validation to test

| | Validation | Test | Change |
|---|---|---|---|
| Baseline log loss | 0.48102 | 0.49466 | +0.0136 |
| Boosting log loss | 0.43472 | 0.44690 | +0.0122 |
| **Margin** | **0.0463** | **0.0478** | **+0.0015** |
| Boosting AUC | 0.77855 | 0.77741 | -0.0011 |

Both models degrade by almost exactly the same amount, and the margin
widens slightly. **The degradation is the September environment, not
model failure.** AUC is unchanged, so ranking ability is fully intact;
only the probability level shifted.

### Calibration on test

| Predicted | Actual | Gap | n |
|---|---|---|---|
| 0.0564 | 0.0515 | -0.0048 | 5,414 |
| 0.0805 | 0.0730 | -0.0076 | 5,414 |
| 0.1014 | 0.1027 | +0.0013 | 5,413 |
| 0.1243 | 0.1274 | +0.0031 | 5,414 |
| 0.1518 | 0.1600 | +0.0082 | 5,413 |
| 0.1857 | 0.1949 | +0.0092 | 5,414 |
| 0.2305 | 0.2294 | -0.0011 | 5,414 |
| 0.2953 | 0.3200 | +0.0247 | 5,413 |
| 0.4049 | 0.4296 | +0.0248 | 5,414 |
| 0.7139 | 0.7246 | +0.0107 | 5,414 |

Mild under-prediction in the middle-upper bands, consistent with a model
trained through July scoring a higher-whiff September. The top band
(71% predicted, 72% actual) is accurate.

## What matters most

Permutation importance on validation:

| Feature | Importance |
|---|---|
| plate_z_rel | 0.1447 |
| plate_x_bat | 0.0445 |
| strikes | 0.0183 |
| release_speed | 0.0057 |
| release_spin_rate | 0.0032 |

**Location dominates.** Height is 3.3x the next feature. Velocity and
spin are marginal — a notable result given how prominent those metrics
are in public discussion. Where the pitch ends up is nearly everything.

Importances are associations, not causal effects.

## Limitations

- **One season.** No evidence the model transfers to other years. 2023
  rule changes and the 2020 tracking-hardware switch make earlier
  seasons non-comparable without explicit handling.
- **No player identity.** Per-pitcher residual bias has a standard
  deviation of 0.043 against a league rate of 0.23, so who throws the
  pitch clearly matters. An idealised per-pitcher offset (computed with
  leakage, so an upper bound) improves log loss by only 0.004.
- **Distribution shift is real and unmodelled.** September differs from
  July. Deployment across a season boundary would need monitoring.
- **Whiff is one dimension of pitch quality, not the whole of it.**
  Ranking pitches by this model would systematically penalise the 78 of
  445 qualified pitchers who throw 35%+ sinkers (Day 22).
- **Rare pitch types are bucketed as OTHER** below 500 training swings.
  The threshold is a judgment call; raising it to 6,000 changed log loss
  by 0.00007, so the choice is not material.
- **Public data only.** No bat tracking, no biomechanics, no catcher
  framing or positioning inputs that a club would have.

## Reproduction

    from src.models import whiff
    from src.models.whiff import fit_boosting

    wm = whiff.build()
    gb = fit_boosting(wm.X_train, wm.y_train)

Seed 42 throughout. Raw Statcast snapshots in `data/raw/` carry both the
game date and the ingestion date in their filenames, because Statcast is
revised retroactively.

Artifacts: `model.joblib` (1.08 MB, gitignored), `metadata.json`,
`test_metrics.csv`.

## Version history

**v1 (2026-09-03)** — first production model. Gradient boosting,
uncalibrated. Beats the lookup baseline by 9.7% on log loss.
