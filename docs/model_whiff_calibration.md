# P(Whiff | Swing) — Calibration

AUC measures ranking. A front office acts on the probability itself: a
stated 58% whiff chance must whiff about 58% of the time, or the
decision built on it is wrong. Log loss and calibration are related but
not the same, and they disagreed here.

## The raw logistic model is poorly calibrated

Reliability on the validation set, 10 quantile bins:

| Predicted | Actual | Gap | n |
|---|---|---|---|
| 0.0617 | 0.1163 | **+0.0546** | 8,350 |
| 0.0970 | 0.1003 | +0.0033 | 8,349 |
| 0.1213 | 0.1091 | -0.0122 | 8,349 |
| 0.1459 | 0.1215 | -0.0244 | 8,349 |
| 0.1743 | 0.1685 | -0.0058 | 8,349 |
| 0.2075 | 0.1940 | -0.0135 | 8,349 |
| 0.2484 | 0.2162 | -0.0322 | 8,349 |
| 0.3014 | 0.2738 | -0.0276 | 8,349 |
| 0.3839 | 0.3654 | -0.0185 | 8,349 |
| 0.5829 | 0.6468 | **+0.0639** | 8,350 |

**Both tails under-predict.** A 6% prediction whiffs 12% of the time; a
58% prediction whiffs 65%. The middle drifts the other way.

The lookup baseline never exceeds +0.0248. **It is better calibrated
than the model that beats it on log loss.**

ECE: logistic 0.02560, baseline 0.00903 — the model is 2.8x worse.

**Cause.** Logistic regression assumes a linear logit. Reaching extreme
probabilities requires extreme feature values, so a non-linear true
relationship leaves the tails unreachable. The lookup table has no such
constraint: it reports each cell's observed mean.

## Isotonic calibration fixes it; Platt scaling does not

Fitted on the first half of validation, evaluated on the second half, so
the calibration and evaluation sets are disjoint (using the same data
for both is a form of leakage).

| Model | Log Loss | Brier | AUC | ECE |
|---|---|---|---|---|
| Lookup baseline | 0.48102 | 0.15451 | 0.71205 | 0.01044 |
| Logistic raw | 0.46854 | 0.14819 | 0.73145 | 0.02776 |
| **Logistic + isotonic** | **0.46449** | **0.14694** | 0.73090 | **0.00883** |
| Logistic + sigmoid | 0.46880 | 0.14835 | 0.73145 | 0.03004 |

**Isotonic cuts ECE by 68%** and lands below the baseline. With it, the
logistic model wins on every metric.

**Sigmoid (Platt) made calibration worse** (0.02776 to 0.03004). It
fits a sigmoid to the score, but the output of a logistic regression is
already a sigmoid — there is no shape left to correct. The observed
error pattern (both tails under, middle over) is not a sigmoid
distortion and cannot be represented that way.

Isotonic is non-parametric: it learns any monotonic mapping. With
~41,000 calibration samples, overfitting risk is low.

**The calibration method must match the error shape.** Taking the
default would have made things worse here.

**AUC is essentially unchanged** (0.73145 to 0.73090). Isotonic is a
monotonic transform, so ranking is preserved; the tiny drop comes from
ties introduced by its step function. This is the point of calibration —
it corrects probabilities while leaving the ordering alone.

Note: the numbers in this table are computed on the second half of the
validation set, so they are not comparable to the full-validation
figures in `model_whiff_baseline.md`. Only within-table comparisons are
valid.
