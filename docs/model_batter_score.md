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
