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
| Barrel% | **+0.0289** | 100% |
| Zone Contact% | +0.0184 | 64% |
| Chase% | -0.0075 | 26% |
| Zone Swing% | +0.0067 | 23% |

**Power carries roughly four times the weight of plate discipline.**
The equal weighting assumed a day earlier was not close.

All signs are baseball-correct: chasing hurts, the rest help.

**Zone Swing% is the weakest input**, which confirms the Day 14 finding
that it measures aggression rather than plate skill. It contributes
almost nothing to production once the other three are known.

## The sensitivity test now passes

5-fold resampling:

| | Arbitrary weights | Learned weights |
|---|---|---|
| Minimum rank correlation | **0.053** | **0.990** |

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

## R-squared is 0.50, and that is the honest number

Four skill rates explain half the variance in wOBA. The remainder
includes speed, batted-ball direction, opposing pitcher quality, and
luck — wOBA depends on whether batted balls found gaps, which skill
does not fully determine.

An R-squared near 0.9 would be a warning sign, not a triumph: it would
suggest outcome information had leaked into the features.

### The clearest miss is explainable

| Player | Predicted | Actual wOBA | Gap |
|---|---|---|---|
| Judge | 0.453 | 0.497 | -0.044 |
| Stanton | 0.381 | 0.341 | **+0.040** |
| Seager | 0.406 | 0.379 | +0.027 |

**Stanton has a 20.9% barrel rate and a 0.341 wOBA.** He is slow: no
infield hits, and well-struck balls are caught. The model has no speed
input and cannot see this. That is a concrete example of what the
missing 50% contains.

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
