# KBO to MLB Strikeout Translation

A prospective scouting model: given a KBO hitter who has never played in
MLB, what would his strikeout rate be there?

## Only K% is modelled

Day 45 measured cross-league correlations across 40 players with 200+
KBO PA and 100+ MLB PA:

| Metric | League ratio | Correlation across players |
|---|---|---|
| K% | 0.69 | **0.77** |
| BB% | 1.24 | 0.32 |
| ISO | 1.29 | 0.28 |

All three league means shift. **Only for strikeouts does the ordering of
players survive the move.** A hitter who struck out more in MLB strikes
out more in KBO; who walks or slugs more is not predictable from the KBO
line at r = 0.28-0.32.

**Projecting a KBO home run leader's MLB power from his ISO is not
supported by this data.** Projecting his strikeout rate is.

This matches Day 16, which measured K% as the fastest-stabilising rate.
Noisy metrics do not transmit across leagues, because most of what they
measure is noise.

## Model

    mu                      league shift in log-odds of a strikeout
    delta_i ~ N(mu, tau)    each player's own shift, partially pooled
    K_i ~ Binomial(PA_i, invlogit(mlb_logit_i + delta_i))

Log-odds rather than rates: rates are bounded, log-odds are not, so a
normal hierarchy is appropriate and shrinkage behaves sensibly near the
boundaries.

47 players with 100+ PA in both leagues. PyMC, 2000 tune / 2000 draws,
4 chains, seed 42. All r-hat 1.00, ESS above 5,000.

| Parameter | Mean | SD | 89% interval |
|---|---|---|---|
| mu | **-0.427** | 0.038 | [-0.49, -0.37] |
| tau | **0.229** | 0.032 | [0.18, 0.28] |

## tau is six times mu's uncertainty

**The league factor is well determined. An individual's deviation from
it is not.**

This is the single most important number in the model. It means
projection intervals must be wide, and that wide intervals are the
honest answer rather than a modelling failure.

## The ratio is not constant

A constant shift in log-odds is not a constant ratio in rates:

| MLB K% | KBO K% | Ratio |
|---|---|---|
| 15% | 10.3% | 0.69 |
| 25% | 17.9% | 0.71 |
| 35% | 26.0% | **0.74** |

The single ratio of 0.69 computed on Day 45 fits low-strikeout hitters
and **understates high-strikeout hitters by about 1.8 points** at a 35%
MLB rate. Small in absolute terms, but it biases exactly the players a
club would worry about.

## Shrinkage does what it is for

| Player | KBO PA | Raw shift | Posterior | Moved |
|---|---|---|---|---|
| Justin Bour | 117 | **+0.150** | **-0.135** | 0.285 |
| Tyler Saladino | 163 | +0.109 | -0.110 | 0.219 |
| Mac Williamson | 168 | +0.053 | -0.126 | 0.180 |
| Darin Ruf | 1,756 | -0.546 | -0.538 | 0.008 |
| Jose Pirela | 1,856 | -0.518 | -0.511 | 0.007 |
| J. M. Fernandez | 2,480 | -0.598 | -0.582 | 0.016 |

Correlation between KBO PA and shrinkage: **-0.48**.

**Bour's sign reverses.** On 117 plate appearances his raw estimate says
he struck out MORE in KBO; the model pulls him back toward the league
factor. Fernandez, on 2,480, barely moves.

Shrinkage depends on distance from the mean as well as sample size:
Robel Garcia (156 PA) moved only 0.073 because his raw estimate already
sat near mu.

**An unweighted average or an ordinary regression would treat Bour's 117
PA and Fernandez's 2,480 identically.**

## Projections

| KBO K% | KBO PA | Projected MLB K% | 80% interval |
|---|---|---|---|
| 10% | 500 | 14.8% | [10.5%, 19.4%] |
| 15% | 500 | 21.5% | [16.0%, 27.4%] |
| 15% | 150 | 21.4% | [14.8%, 28.5%] |
| 22% | 500 | 30.3% | [23.6%, 37.5%] |

An 11-point interval at 500 PA. That is what 47 transition players
supports.

### More KBO plate appearances barely help

500 PA gives an 11.4-point interval; 150 PA gives 13.7. **Only 2.3
points of difference.**

Because the uncertainty is dominated by tau — the personal deviation —
not by observation noise. Watching a player for another KBO season
sharpens the observed rate but says nothing about whether HE will
translate typically.

**The binding constraint is the number of transition players, not the
size of any one player's sample.** More KBO seasons do not fix this;
more players moving between the leagues would.

## Limitations

- **47 players.** Every interval reflects that.
- **Selection bias, unmodelled.** Foreign hitters signed by KBO are MLB
  players who could not hold a job there; the seven Koreans posted to
  MLB were KBO stars. The two directions are selected oppositely. This
  sample is almost entirely the first kind.
- **Age is a confound.** Nine of eleven players who returned to MLB came
  back with a K% at or worse than before, but a KBO stint costs two to
  four years and K% rises with age. Birth dates are not in the cached
  Chadwick columns, so the two effects are not separable here.
- **ABS.** KBO introduced automated ball-strike calling in 2024, and the
  2024 foreign-hitter cohort shows the lowest K% and highest average of
  any season in the sample. Thirteen players is too few to attribute
  this, and it is recorded as an observation, not a finding.
- **Park and run environment are not adjusted.**
- K% only. BB% and ISO are not projectable from this data.

## Prospect selection

23 current KBO hitters, 2023-2025 seasons, chosen as plausible MLB
posting candidates: young enough for a club to invest in, and producing
at a level that draws attention.

Two players were removed after the first pass:
- **Song Sung Mun** — already signed with an MLB club, so he is no
  longer a projection target
- **Kim Tae Gun** — too old to be a posting candidate

The list is a judgment call, not a systematic screen. It is illustrative
of what the method produces, not a ranked board.
