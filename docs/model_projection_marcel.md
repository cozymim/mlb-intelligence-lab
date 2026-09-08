# Projection System — Marcel Baseline

Baseline established before building anything, following the Day 25
principle: constructing a baseline after seeing model results invites
choosing one the model can beat.

## The algorithm, verified not remembered

Tom Tango's Marcel, described by him as "the minimum level of competence
you should expect from any forecaster".

| Component | Batting | Pitching |
|---|---|---|
| Weights (recent first) | **5 / 4 / 3** | 3 / 2 / 1 |
| Regression | **100 PA** | 134 outs (~44.2 IP) |
| Age adjustment | (age-29) x 0.003 above 29, x 0.006 below | same |

Only the batting side is implemented.

### The age adjustment is deliberately omitted

Two reasons, the second more important:

1. Birth dates are not in the cached Chadwick columns.
2. **Tango's coefficients were fitted for offensive PRODUCTION**, which
   declines after 29. **Strikeout rate moves the opposite way — it rises
   with age.** Applying production coefficients to K% would push
   projections in the wrong direction.

Recorded as a limitation rather than approximated with the wrong sign.

## Pitchers had to be excluded, and it mattered enormously

Season lines built from raw plate appearances contained pitchers:

| Season | With pitchers | Hitters only |
|---|---|---|
| 2021 | 1,047 | 513 |
| 2022 | 693 | 542 |
| 2023 | 656 | 523 |
| 2024 | 651 | 548 |

**In 2021, 534 of 1,047 "batters" were pitchers** — the National League
had no DH until the universal DH arrived in 2022. Pitchers strike out at
roughly twice the hitter rate.

**Marcel regresses toward the league rate, so a corrupted league rate
corrupts every projection.** The uncorrected league K% came out at 0.679
against a true value near 0.225.

Small numbers of pitcher plate appearances persist after 2022 (position
players pitching in blowouts, and the reverse), so the filter applies to
every season.

## Results — projecting 2024 from 2021-2023

257 batters with 200+ PA in 2024 and prior history.

### K%

| Model | MAE | RMSE | Correlation |
|---|---|---|---|
| League average | 0.0476 | 0.0587 | — |
| Previous season only | 0.0287 | 0.0390 | 0.785 |
| **Marcel** | **0.0271** | **0.0348** | **0.808** |

### BB%

| Model | MAE | RMSE | Correlation |
|---|---|---|---|
| League average | 0.0220 | 0.0272 | — |
| Previous season only | 0.0169 | 0.0221 | 0.723 |
| **Marcel** | **0.0143** | **0.0179** | **0.763** |

**Marcel beats both baselines on both metrics**, but by very different
margins.

### The gain is concentrated where the noise is

| Metric | MAE gain over last-season-only |
|---|---|
| K% | **5.6%** |
| BB% | **15.4%** |

**BB% benefits nearly three times as much.** Day 16 measured BB% as the
noisier of the two, and multi-year weighting plus regression is exactly
the remedy for noise. For K%, last season alone is nearly as good — a
5.6% edge is real but modest, and worth stating plainly.

### RMSE improves more than MAE

For K%, MAE improves 5.6% but RMSE improves 10.8%. Marcel
disproportionately reduces LARGE errors, which is what regression to the
mean is for: players who were extreme last season get pulled back.

## Any model must beat these numbers

**K%: MAE 0.0271. BB%: MAE 0.0143.**

Not the league average, and not last season.

## Limitations

- **One projection season.** With four seasons of data and a three-year
  window, 2024 is the only year that can be projected. These results are
  a single snapshot.
- **257 batters.** A small evaluation set.
- No age adjustment (see above).
- Playing time is not projected. Marcel normally projects PA as well;
  here rates are evaluated directly against realised rates.
- League environment shifts are not modelled beyond the regression
  target moving with the weighted window.
