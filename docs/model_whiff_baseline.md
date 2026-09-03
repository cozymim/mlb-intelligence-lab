# P(Whiff | Swing) — Baselines

Established BEFORE any model was fitted. Building baselines after seeing
model results invites choosing a baseline the model can beat.

## Target

`P(whiff | swing)` on 338,364 swings from the 2024 season.
Swing and whiff definitions from `src/features/plate_discipline.py`:
foul tips are swings but not whiffs; bunts are excluded from both.

League whiff rate: 23.22%.

## Temporal split

| Split | Rows | Dates | Whiff rate |
|---|---|---|---|
| Train | 200,735 | 03-28 to 07-14 | 23.01% |
| Validation | 83,492 | 07-19 to 08-31 | 23.12% |
| Test | 54,137 | 09-01 to 09-29 | **24.13%** |

The four-day gap between train and validation is the All-Star break
(2024-07-15 to 07-18), which produced zero-row snapshots on Day 15.

**September is a different environment.** Whiff rate is a full point
higher in the test window, and every baseline scores ~0.01 worse there.
Expanded rosters, accumulated fatigue, and playoff-race bullpen usage
are candidate causes. Test-set degradation is therefore not necessarily
model failure.

**A random split would have hidden this** — all three partitions would
have shown 23.2%.

## Three baselines

| Baseline | Log Loss | Brier | AUC |
|---|---|---|---|
| Constant (league rate) | 0.54072 | 0.17775 | — |
| Lookup: pitch_type x count x stand x p_throws | 0.52349 | 0.17176 | 0.626 |
| **Lookup + zone flag** | **0.48524** | **0.15629** | **0.709** |

Validation set. Grouped means with shrinkage toward the global rate
(prior strength 50), which is necessary: unshrunk cells of 0.0 or 1.0
produce infinite log loss.

**Any model must beat 0.48524, not 0.54072.**

### The zone flag carries 69% of the total improvement

Constant to lookup: 0.0173. Lookup to lookup+zone: 0.0383.

Day 21 measured in-zone whiff rate at ~14% versus ~40% out of zone. That
3x gap converts directly into predictive power. The validated zone
definition from Day 13 is doing most of the work here.

### More cells is not better

The zone version has 329 cells against 583 for the handedness version,
and scores far better. Splitting on handedness combinations (4 ways)
carried less information than splitting on in-zone (2 ways). **Which
axis you split on matters more than how finely you split.**

## Calibration of the best baseline

| Predicted | n | Predicted | Actual | Gap |
|---|---|---|---|---|
| 0-10% | 9,016 | 0.0885 | 0.0821 | -0.0064 |
| 10-15% | 12,704 | 0.1300 | 0.1293 | -0.0007 |
| 15-20% | 30,798 | 0.1704 | 0.1647 | -0.0057 |
| 20-25% | 7,483 | 0.2228 | 0.2198 | -0.0029 |
| 25-30% | 5,120 | 0.2777 | 0.2896 | +0.0120 |
| 30-40% | 6,745 | 0.3418 | 0.3647 | +0.0229 |
| 40%+ | 11,626 | 0.5151 | 0.5384 | +0.0233 |

Well calibrated overall, but with a **systematic direction**: low
predictions run high, high predictions run low. This is over-shrinkage —
prior strength 50 pulls extreme cells toward the global 0.23. A real
40% cell is reported as 34%.

A logistic model applies no such shrinkage and should not carry this
bias. **Equal log loss with better calibration would still be an
improvement**, since a front office acts on the probability, not the
ranking.

## Headroom for a model

Correlation with the target among swings, for variables the baselines
do not use:

| Variable | r |
|---|---|
| plate_z | **-0.177** |
| release_speed | -0.103 |
| pfx_z | -0.101 |
| plate_x | +0.077 |
| pfx_x | +0.045 |
| release_spin_rate | +0.015 |
| release_extension | +0.012 |

`plate_z` is the strongest: lower pitches whiff more. The baseline
already knows in-zone versus out; a continuous height subdivides "out of
zone" into "just below" and "well below".

`plate_x` is signed relative to the catcher's view, so its meaning
inverts with batter handedness — the same issue as pfx_x on Day 19.
Normalising should strengthen it.

**Spin and extension look useless at r ~ 0.01, but pitch type is not
controlled.** Curveballs have high spin and high whiff; four-seams have
high spin and low whiff. Pooling cancels the effect — the same trap as
the Day 23 separation analysis. Must be checked within pitch type before
concluding.

**Expectation:** with the strongest unused signal at -0.177, a logistic
model is unlikely to beat 0.48524 by a wide margin. A result in the
0.47-0.48 range would be honest and unremarkable, and will be reported
as such.
