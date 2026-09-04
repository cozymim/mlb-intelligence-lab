# P(Whiff | Swing) — Gradient Boosting

Two experiments from the Day 28 error analysis, run cheapest first.

## Experiment 1: rare-pitch threshold — no effect

Day 28 found the logistic model losing badly on knuckle curves
(-0.0325 vs baseline) and hypothesised that raising the bucketing
threshold from 500 would help.

| Threshold | Kept types | Log Loss |
|---|---|---|
| 500 | 10 | 0.46449 |
| 1500 | 9 | 0.46454 |
| 3000 | 9 | 0.46454 |
| 6000 | 8 | 0.46447 |

**Total spread: 0.00007. The hypothesis was wrong.**

**Why.** KC is 769 of 41,746 evaluation swings (1.8%). Losing 0.0325 on
1.8% of rows costs 0.0006 overall. The group-level loss looked alarming
without being material.

**Lesson: multiply group-level improvement by group size before acting
on it.** Skipping that calculation led to a wasted hypothesis.

## Experiment 2: gradient boosting — large win

| Model | Log Loss | Brier | AUC | ECE |
|---|---|---|---|---|
| Lookup baseline | 0.48102 | 0.15451 | 0.71205 | 0.01044 |
| Logistic (isotonic) | 0.46449 | 0.14694 | 0.73090 | 0.00883 |
| **Boosting (uncalibrated)** | **0.43472** | **0.13719** | **0.77855** | **0.00575** |
| Boosting (isotonic) | 0.43981 | 0.13732 | 0.77834 | 0.00667 |

Boosting beats the logistic model by **0.0298** — 1.8x the margin by
which the logistic model beat the baseline. The threshold set in advance
for justifying the extra complexity was 0.005; this clears it sixfold.

### Calibration made boosting WORSE

Log loss 0.43472 to 0.43981, ECE 0.00575 to 0.00667.

Boosting predicts the observed rate in each leaf, structurally similar
to the lookup table, so it is already well calibrated — better than the
calibrated logistic model. Isotonic regression then discretises away
resolution without correcting anything.

**Day 27 concluded that calibration was essential. That conclusion was
model-specific, not general.** Calibration must be diagnosed per model,
never applied by default. The uncalibrated boosting model is the one
adopted.

### It fixed the pitch types the logistic model failed on

| Pitch | n | Logistic vs base | Boosting vs base | Boosting vs logistic |
|---|---|---|---|---|
| KC | 769 | -0.0325 | -0.0041 | **+0.0284** |
| FC | 3,661 | -0.0250 | **+0.0452** | **+0.0702** |
| SI | 5,966 | -0.0077 | **+0.0166** | +0.0243 |
| FF | 13,391 | +0.0197 | +0.0307 | +0.0110 |
| CU | 2,428 | +0.0543 | +0.0801 | +0.0258 |

**Boosting beats the logistic model on every pitch type.** The two it
previously lost to the baseline on (FC, SI) now win by a wide margin.

**Cutter is the clearest case.** Its height correlation is -0.084,
essentially nothing. The logistic model is forced to carry a
`FC x plate_z_rel` term regardless, which is pure noise. A tree simply
does not split there. This is the structural argument for trees stated
on Day 28, confirmed.

## Permutation importance

| Feature | Importance |
|---|---|
| plate_z_rel | **0.1447** |
| plate_x_bat | 0.0445 |
| strikes | 0.0183 |
| pitch_type_b_FF | 0.0062 |
| release_speed | 0.0057 |
| pfx_z | 0.0048 |
| release_spin_rate | 0.0032 |
| pitch_type_b_SI_x_pz | 0.0008 |

**Location dominates.** Height is 3.3x the next feature and 8x the
third. Velocity and spin remain marginal, consistent with the Day 25
within-pitch-type correlations of 0.01-0.07. Statcast's most
publicised measurements contribute little to whiff prediction; where
the pitch ends up is nearly everything.

**The explicit interaction terms are now near-worthless** (0.0008).
They were mandatory for the logistic model — without them it lost to the
baseline — and are redundant for trees, which learn interactions
directly. **Changing model class changes which feature engineering is
worth doing.**

Importances are associations, not causal effects.

## Hyperparameters are irrelevant here

| Config | Iterations | Log Loss | ECE |
|---|---|---|---|
| leaves 15, lr 0.06 | 322 | 0.43594 | 0.00694 |
| **leaves 31, lr 0.06** | 292 | **0.43472** | **0.00575** |
| leaves 63, lr 0.06 | 161 | 0.43535 | 0.00618 |
| leaves 31, lr 0.03 | 424 | 0.43523 | 0.00665 |

Total spread 0.0012, about 4% of the margin over the logistic model.
Early stopping selects the iteration count. **No tuning budget is
warranted** — a useful negative result, given how often projects spend
days here.

## Final standing (second half of validation, 41,746 swings)

| Model | Log Loss | vs baseline |
|---|---|---|
| Constant | — | — |
| Lookup + zone | 0.48102 | baseline |
| Logistic (linear only) | loses | — |
| Logistic + interactions + isotonic | 0.46449 | +3.4% |
| **Boosting** | **0.43472** | **+9.6%** |
