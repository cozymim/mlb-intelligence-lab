# Batter Impact Score — sensitivity test FAILED

## What was built

Three axes chosen from the Day 16 correlation structure:

| Axis | Metric(s) | Why |
|---|---|---|
| Discipline | Chase%, Zone Swing% | r = 0.52 with each other, one axis |
| Contact | Zone Contact% | orthogonal to discipline (r = -0.02) |
| Power | Barrel% only | HardHit% excluded, r = 0.78 is redundancy |

343 of 425 batters clear every stabilization threshold from
`src/features/sample_size.py`.

## The sensitivity test fails

Spearman rank correlation between weightings:

| | equal | power | discipline | contact |
|---|---|---|---|---|
| equal | 1.000 | 0.740 | 0.841 | 0.629 |
| power-heavy | 0.740 | 1.000 | 0.656 | **0.053** |
| discipline-heavy | 0.841 | 0.656 | 1.000 | 0.347 |
| contact-heavy | 0.629 | **0.053** | 0.347 | 1.000 |

**Power-heavy and contact-heavy rankings are unrelated.**

Top 10 under each:
- Power: Judge, Ohtani, Soto, Stanton, Seager, Carpenter, Rooker, Álvarez, Toglia, Tucker
- Contact: Kwan, Betts, Pasquantino, Seager, Álvarez, LeMahieu, Flores, Arráez, Grichuk, Ramírez

Two names overlap.

**The score measures the weighting choice, not the batter.** CLAUDE.md
requires arbitrary weights to be justified by statistics, baseball
reasoning, or sensitivity testing. This fails sensitivity testing, so a
single composite score is not defensible as constructed.

## "Equal weights" were not equal

`z_discipline` has standard deviation 0.483; the other axes have 1.000.

Averaging two z-scores that correlate at -0.52 (negated Chase% against
Zone Swing%) shrinks the variance:
var = (1 + 1 + 2(-0.52)) / 4 = 0.24, sd = 0.49. Exactly what was
observed.

**The discipline axis was silently receiving about half the intended
weight.** A composite built from correlated components must be
re-standardised after combining, or the stated weights are fiction.

## The axes are not orthogonal either

| | discipline | contact | power |
|---|---|---|---|
| discipline | 1.000 | -0.270 | +0.263 |
| contact | -0.270 | 1.000 | -0.535 |
| power | +0.263 | -0.535 | 1.000 |

Day 16 measured Chase% against Barrel% at -0.07. As a composite axis it
becomes +0.263, because Zone Swing% correlates +0.16 with Barrel% and is
now folded in. **Combining metrics into an axis creates correlations the
components did not have.**

The contact/power figure of -0.535 matches the -0.49 measured on Day 16
and is a genuine trade-off, not an artifact.

## Where this goes next

Three options:

**A. Abandon the single score; report three axes separately.** Most
honest, but hard to call an evaluation system.

**B. Learn the weights instead of choosing them.** Regress observed
production (wOBA, available in the Statcast data) on the three axes.
The weights then come from data rather than taste.

Not circular: the axes are skills (chase, contact, barrel rates) and
wOBA is production. Predicting production from skills is exactly the
question a front office asks.

**C. Fix only the standardisation bug and accept option A.**

**B is the chosen direction.** A composite whose weights survive
sensitivity testing is only possible if the weights are anchored to
something external, and production is the natural anchor.

## Note on the leaderboard

Aaron Judge ranks first under every weighting, with `z_power` = 4.802 —
nearly five standard deviations above the league. His `z_contact` is
-1.225, a clean illustration of the contact/power trade-off. He wins
regardless of weights because the power figure is extreme enough to
dominate any reasonable scheme, not because the scoring is sound.

---

# Resolution: weights learned from production

Option B was implemented. Weights are regression coefficients from
predicting observed wOBA from four standardised skill rates.

Not circular: the inputs are skills (chase, swing, contact, barrel
rates) and the target is production. Predicting production from skills
is the question a front office asks.

`woba_value` and `woba_denom` are Statcast's own linear weights — an
official metric, not something invented here.

## Learned weights (2024, 343 qualified batters)

wOBA change per 1 standard deviation of each skill:

| Skill | Coefficient | Relative |
|---|---|---|
| Barrel% | **+0.0292** | 100% |
| Zone Contact% | +0.0183 | 63% |
| Chase% | -0.0084 | 29% |
| Zone Swing% | +0.0068 | 23% |

**Power carries roughly three and a half times the weight of plate discipline.**
The equal weighting assumed a day earlier was not close.

All signs are baseball-correct: chasing hurts, the rest help.

**Zone Swing% is the weakest input**, which confirms the Day 14 finding
that it measures aggression rather than plate skill. It contributes
almost nothing to production once the other three are known.

## The sensitivity test now passes

5-fold resampling:

| | Arbitrary weights | Learned weights |
|---|---|---|
| Minimum rank correlation | **0.053** | **0.992** |

Coefficient stability across folds:

| Skill | Mean | SD | CV |
|---|---|---|---|
| Barrel% | 0.0289 | 0.0011 | 3.8% |
| Zone Contact% | 0.0184 | 0.0005 | 2.7% |
| Chase% | -0.0075 | 0.0013 | 17.3% |
| Zone Swing% | 0.0067 | 0.0009 | 13.4% |

Coefficient ordering is identical in every fold. The two smaller
coefficients are less stable in relative terms, but their sign never
flips.

**Why this version passes.** The arbitrary weights had no external
anchor, so nothing constrained them. These are fitted to observed
production, and that relationship does not change when the sample is
resampled.

This satisfies two of the three justifications CLAUDE.md requires —
statistical grounding and sensitivity testing — rather than none.

## R-squared is 0.52, and that is the honest number

Four skill rates explain just over half the variance in wOBA. The remainder
includes speed, batted-ball direction, opposing pitcher quality, and
luck — wOBA depends on whether batted balls found gaps, which skill
does not fully determine.

An R-squared near 0.9 would be a warning sign, not a triumph: it would
suggest outcome information had leaked into the features.

### The clearest miss is explainable

| Player | Predicted | Actual wOBA | Gap |
|---|---|---|---|
| Judge | 0.446 | 0.475 | -0.029 |
| Stanton | 0.371 | 0.330 | **+0.042** |
| Seager | 0.397 | 0.365 | +0.031 |

**Stanton has a 20.9% barrel rate and a 0.330 wOBA.** He is slow: no
infield hits, and well-struck balls are caught. The model has no speed
input and cannot see this. That is a concrete example of what the
missing 48% contains.

## Interpretation

The score is a predicted wOBA. "This skill profile is worth about a
0.400 wOBA" is directly meaningful, unlike a unitless composite index.

Standardisation uses the training distribution, not each new sample's
own mean — otherwise scoring a different season would grade players
relative to that season rather than to a fixed reference population.
Locked in by `test_standardisation_uses_training_distribution`.

## Limitations

- One season. Weights may differ in a different run environment.
- No speed, defence, or baserunning. The score evaluates hitting skill
  only, and Stanton shows what that omits.
- 343 of 425 batters qualify; the other 82 fall below a stabilization
  threshold and correctly receive no score.
- Regression coefficients are associations, not causal effects.

---

## Cross-season stability (2026-10-22)

Three separate questions, with three different answers.

### 1. Are the learned weights stable across seasons?

Refitting independently on each season:

| Season | Chase% | Zone Swing% | Zone Contact% | Barrel% | R² |
|---|---|---|---|---|---|
| 2021 | -0.0095 | 0.0077 | 0.0165 | 0.0300 | 0.503 |
| 2022 | -0.0031 | 0.0030 | 0.0193 | 0.0288 | 0.480 |
| 2023 | -0.0070 | 0.0032 | 0.0159 | 0.0288 | 0.494 |
| 2024 | -0.0084 | 0.0068 | 0.0183 | 0.0292 | 0.520 |

Coefficient of variation: **Barrel% 1.9%, Zone Contact% 9.1%**, Chase%
40.1%, Zone Swing% 46.7%.

**The two largest weights are nearly fixed; the two smallest swing by a
factor of three.** Chase% ranges -0.0031 to -0.0095 across seasons.

**All four signs hold in every season**, so the direction of each effect
is stable even where the magnitude is not. Small coefficients are less
stable because estimation error is large relative to their size — the
same pattern Day 36 found in the projection model.

R² holds between 0.480 and 0.520.

### 2. Does the choice of weights change the ranking?

Scoring each season's players with each season's weights:

| Players from | w2021 | w2022 | w2023 | w2024 |
|---|---|---|---|---|
| 2021 | 1.0000 | 0.9681 | 0.9901 | 0.9975 |
| 2022 | 0.9671 | 1.0000 | 0.9832 | 0.9801 |
| 2023 | 0.9874 | 0.9796 | 1.0000 | 0.9930 |
| 2024 | 0.9962 | 0.9751 | 0.9914 | 1.0000 |

**Every off-diagonal correlation is 0.967 or higher.**

The unstable small coefficients barely matter, because Barrel% and Zone
Contact% carry most of the weight and both are stable. **Which season's
weights are used does not change who ranks where.**

This matters more than the first result: the score is reproducible
regardless of which season it was calibrated on.

### 3. Does a player keep his score year to year?

A different question — about players changing, not weights. Scored with
2024 weights throughout, 145 batters qualified in all four seasons:

| | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|
| 2021 | 1.000 | 0.654 | 0.667 | **0.639** |
| 2022 | 0.654 | 1.000 | 0.751 | 0.723 |
| 2023 | 0.667 | 0.751 | 1.000 | 0.720 |
| 2024 | 0.639 | 0.723 | 0.720 | 1.000 |

**Adjacent seasons correlate 0.65-0.75; three years apart falls to
0.639.** On average the correlation falls with distance (0.708 one
season apart, 0.695 at two, 0.639 at three), but not in every row:
2021 correlates more with 2023 than with 2022. An earlier version of
this paragraph stated 0.71-0.75 and called the decay clear; neither
matched its own table.

**This is the weakest of the three results, and it is a property of
baseball rather than of the method.** Roughly half of a season's score
is durable skill; the rest is that season's variation — form, injury,
age, and luck. Day 16 measured barrel rate as needing 150 batted balls
to stabilise at all, so a single season is not a clean measurement
either.

**Consequence for interpretation: the score describes a player's season,
not his ability.** Using one season's score as a forecast of the next
would be over-reading it.


## Correction (Day 54): wOBA definition

Statcast's `woba_value` credits events that the wOBA definition treats
as outs or excludes: reaching on error, fielder's choice, catcher's
interference, intentional walks, and some bunts and dropped third
strikes. Summed as-is, 2023 league wOBA came out at .331 against .316
on Baseball Savant and .318 on FanGraphs. The excess was traced event
by event. `clean_woba()` in `src/data/validation.py` now applies the
standard definition, and every wOBA in the project goes through it.

The error was not neutral. Reaching on error happens most to hitters
who put the ball on the ground and run well, so it credited them for
fielders' mistakes.

Every figure in this document was recomputed after the fix. The
conclusions did not change. R-squared rose in every season, which is
what removing a source of noise unrelated to skill should do.

Remaining difference from FanGraphs (about .003) comes from Statcast's
rounded event weights (0.9 for a single against 2023's 0.883). It is
close to proportional across hitters and is left as a documented
approximation.
