# P(Whiff | Swing) — Logistic Regression

Baselines were fixed before fitting: see `docs/model_whiff_baseline.md`.

## Result

Validation set (83,492 swings, 2024-07-19 to 08-31):

| Model | Log Loss | Brier | AUC |
|---|---|---|---|
| Constant (league rate) | 0.54072 | 0.17775 | — |
| Lookup + zone (baseline) | 0.48524 | 0.15629 | 0.70892 |
| **Logistic A (linear)** | **0.51151** | 0.16440 | **0.65086** |
| Logistic C (+ interactions) | **0.47650** | **0.15088** | **0.72245** |

### The linear model LOSES to the baseline

Logistic A is worse than a two-line groupby on every metric: 0.026 worse
log loss, 0.058 worse AUC.

This was predicted on Day 25. `plate_z` correlates +0.21 with whiff for
four-seams and -0.50 for knuckle curves. A single coefficient cannot
represent both, so the effects partly cancel.

**Without a baseline, "logistic regression, AUC 0.651" would have looked
like a result.** It is worse than no machine learning at all.

### Interactions recover it

Adding `pitch_type x plate_z_rel` improves log loss by 0.035 — four
times the 0.009 margin by which the final model beats the baseline.
**Most of the value came from identifying the sign reversal, not from
the choice of algorithm.**

Final margin over the baseline: 1.8% on log loss. Real, but modest.
Described as "beats a well-constructed lookup table by 1.8%", not as a
sophisticated predictive system.

## Features

Numeric: plate_x_bat, plate_z_rel, release_speed, pfx_x, pfx_z,
release_spin_rate, release_extension, balls, strikes.
Categorical: pitch_type, stand, p_throws (one-hot, drop_first).
Plus pitch_type x plate_z_rel interactions. 26 base features.

**plate_z_rel** is height relative to the batter's own zone
(0 = bottom, 1 = top). Day 13 measured a 36 cm spread in zone tops
across batters, so absolute height is not comparable between hitters.
Effect on within-pitch-type correlations was mixed: stronger for CH
(-0.30 to -0.32), FS (-0.37 to -0.40), weaker for FF (+0.24 to +0.21).

**plate_x_bat** flips sign for left-handed batters so positive means
away. Measured benefit was negligible (log loss 0.51272 to 0.51151).
Retained for interpretability, not justified on performance — the model
already carries a `stand` dummy that captures part of the same
information.

Imputation and scaling live inside the sklearn Pipeline so they are fit
on training data only. Leakage guard `check_features()` runs on the
feature matrix immediately before fitting.

## Coefficients (standardised)

| Feature | Coefficient |
|---|---|
| pitch_type_FF x plate_z_rel | +1.647 |
| pitch_type_FF | -1.305 |
| plate_z_rel (main) | -1.044 |
| pitch_type_SI | -0.626 |
| pitch_type_SI x plate_z_rel | +0.546 |
| pitch_type_FC x plate_z_rel | +0.343 |
| plate_x_bat | +0.222 |

**The model learned the baseball.** Net height effect by pitch type
(main effect plus interaction):

| Pitch | Net plate_z_rel effect |
|---|---|
| FF four-seam | **+0.603** (high fastballs miss bats) |
| FC cutter | -0.701 |
| SI sinker | -0.498 |
| CH changeup (reference) | -1.044 |
| CU curveball | **-1.121** (low breaking balls miss bats) |

**Interpretation warning.** With interactions present, a main effect is
the value at `plate_z_rel = 0`, i.e. the bottom of the zone. The FF main
effect of -1.305 does not mean four-seams whiff less; it means a
four-seam at the bottom of the zone whiffs less, which is correct — that
is a hittable pitch. Main effects and interactions must be read
together.

Coefficients are associations, not causal effects.

## Known issue: rare pitch types

The one-hot encoding includes SC, EP, FO, CS, FA and KN with
coefficients between -0.08 and +0.06. These are almost certainly noise
on tiny samples. The rare-pitch-type policy deferred on Day 8 (exclude,
bucket as OTHER, or apply a minimum-count threshold) needs to be decided
before the next model.

## Rare pitch type policy (decided 2026-09-03)

Training-set counts show a clear cliff:

| Pitch | n |
|---|---|
| FF | 64,478 |
| ... | ... |
| KC | 3,052 |
| SV | 847 |
| KN | 312 |
| FA | 160 |
| EP | 107 |
| FO | 66 |
| CS | 14 |
| **SC** | **6** |

Model C assigned `SC x plate_z` a coefficient of -0.076 — essentially
identical to `CU x plate_z` (-0.077), which rests on 10,705 swings. A
six-swing estimate received the same weight as a ten-thousand-swing one.

**Policy: pitch types with fewer than 500 training swings are bucketed
as OTHER.** The threshold is placed between SV (847) and KN (312).

This is a judgment call, not a measured stabilization threshold like
those in `src/features/sample_size.py`, and is documented as such.

**Bucketed rather than excluded.** Dropping the rows would leave the
model unable to score a rare pitch type at prediction time. An OTHER
bucket at least returns that group's mean.

Interactions double the cost: each rare pitch type contributed two
parameters (a dummy and an interaction term), so bucketing removes 12.

### Result: 12 parameters removed, performance unchanged

| Model | Features | Log Loss | Brier | AUC |
|---|---|---|---|---|
| Logistic C (all pitch types) | 43 | 0.47650 | 0.15088 | 0.72245 |
| **Logistic D (bucketed)** | **31** | **0.47572** | **0.15080** | 0.72240 |

Log loss improved by 0.00078 and AUC fell by 0.00005 — no meaningful
difference either way. 665 swings (0.3%) changed bucket.

**Those 12 parameters were doing nothing.** Confirmation that the SC
coefficient on six swings was noise, and a demonstration that a simpler
model at equal performance is the one to keep.

**Model D is the accepted logistic model.**

## Final standing

| Model | Log Loss | vs baseline |
|---|---|---|
| Constant | 0.54072 | -11.4% |
| Lookup + zone | 0.48524 | baseline |
| Logistic A (linear) | 0.51151 | **-5.4% (loses)** |
| Logistic D | **0.47572** | **+2.0%** |

The honest summary: a logistic regression with a pitch-type by height
interaction beats a well-constructed lookup table by 2%. The linear form
loses to it outright.
