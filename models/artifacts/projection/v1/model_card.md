# Model Card — Season Projection v1 (K%, BB%)

## What this predicts

A hitter's strikeout rate and walk rate in the coming season, from three
prior seasons of outcomes plus one prior season of plate discipline.

## Baseball question and use

**Question.** What will this hitter's plate approach produce next year?

**Who would use it.** Roster planning and acquisition. K% and BB% are
the two outcomes that do not depend on where a batted ball lands, so
they carry less luck than most rate statistics.

**Decision it supports.** Whether a hitter's recent strikeout or walk
rate reflects a durable change in approach or a one-season fluctuation.

**Prediction timestamp.** The end of the prior season. Nothing from the
projected season is used.

## Why only two metrics

Scope was narrowed at the Week 6 checkpoint. The result that matters is
whether the system beats Marcel, not how many metrics it covers. K% and
BB% stabilise fastest (Day 16), so validation is clean rather than
noise-dominated, and both apply to hitters and pitchers alike.

AVG was excluded on Day 25 as near-unpredictable: BABIP noise dominates
and even Marcel struggles.

The framework extends by configuration. Adding xwOBA is a parameter
change, not new work.

## Data

2021-2024 Statcast, 2,849,203 pitches. Season lines built from plate
appearances.

**Pitchers are excluded from the hitter pool.** In 2021, before the
universal DH, 534 of 1,047 "batters" were pitchers, who strike out at
roughly twice the hitter rate. Marcel regresses toward the league rate,
so an uncorrupted league rate is essential — the unfiltered value was
0.679 against a true 0.225.

Intentional walks are excluded from BB%: they reflect the opposing
manager, not the hitter.

## Models

**Baseline — Marcel.** Tom Tango's system, verified against published
sources: three prior seasons weighted 5/4/3, regressed toward the league
rate by 100 PA.

**Age adjustment deliberately omitted.** Tango's coefficients were
fitted for offensive PRODUCTION, which declines after 29. Strikeout rate
RISES with age. Applying production coefficients to K% would move
projections in the wrong direction. Birth dates are also absent from the
cached Chadwick columns.

**Final model.** Linear regression on the Marcel projection plus two
prior-season skill rates: `chase_pct` and `zone_contact_pct`.

Only two skills. A five-skill version scored better in training and
gained nothing under cross-validation — `whiff_pct` correlates -0.91
with `zone_contact_pct`, and `swing_pct` 0.85-0.88 with the swing rates.
Condition number was 14.2, below the textbook threshold of 30, and the
redundancy still overfit 254 rows.

## Results

Five-fold cross-validated MAE, 254 batters with 200+ PA in 2024:

### K%

| Model | MAE | RMSE | Correlation |
|---|---|---|---|
| League average | 0.0476 | 0.0587 | — |
| Previous season only | 0.0287 | 0.0390 | 0.785 |
| Marcel | 0.0271 | 0.0348 | 0.807 |
| **Marcel + skills** | **0.0265** | **0.0340** | **0.814** |

### BB%

| Model | MAE | RMSE | Correlation |
|---|---|---|---|
| League average | 0.0220 | 0.0272 | — |
| Previous season only | 0.0169 | 0.0221 | 0.723 |
| Marcel | 0.0144 | 0.0180 | 0.760 |
| **Marcel + skills** | **0.0137** | **0.0172** | **0.767** |

**Marcel beats last-season-only by 5.6% (K%) and 15.4% (BB%). Skills
beat Marcel by a further 2.2% and 4.9%.**

The honest summary: a verified implementation of the standard baseline,
improved narrowly by Statcast skill rates.

### BB% gains more at every stage

| Stage | K% gain | BB% gain |
|---|---|---|
| Last season to Marcel | 5.6% | 15.4% |
| Marcel to + skills | 2.2% | 4.9% |

Consistent with Day 16, which measured BB% as the noisier metric.
Noisier outcomes leave more room for both regression and skill
information.

### The gain is concentrated where Marcel fails

Mean improvement by quartile of Marcel's own error:

| Marcel error | Improvement | n |
|---|---|---|
| 0.000-0.010 | **-0.0042** | 64 |
| 0.010-0.022 | -0.0003 | 63 |
| 0.022-0.039 | +0.0025 | 63 |
| 0.039-0.120 | **+0.0045** | 64 |

**Where Marcel is already accurate, skills make it worse.** The overall
gain nets damage to good projections against substantial repair of bad
ones, and which quartile a player falls in is unknowable in advance.

For acquisition work this is favourable: a 2-point miss is tolerable, a
12-point miss changes the decision.

## A coefficient that must not be interpreted

K% coefficients: marcel_k +0.8577, zone_contact_pct -0.2670,
**chase_pct -0.0795**.

The chase coefficient is backwards — chasing more should raise strikeout
rate. Past K% already reflects chase behaviour, so what remains is a
residual, and residuals can carry the opposite sign.

**This model predicts; it does not explain.** Its coefficients are not
statements about baseball.

## Limitations

- **One projection season.** Four seasons with a three-year window
  leaves only 2024 projectable. These are a single snapshot.
- **254 batters.** Small enough that mild collinearity overfits.
- No age adjustment.
- Playing time is not projected; rates are evaluated directly.
- Skills use one prior season, not a weighted window.
- Public data only.

## Reproduction

    from src.models.marcel import season_lines
    from src.models.projection import skill_rates, build_dataset, cross_validated_mae

Seed 42. Seasons pinned explicitly — an unpinned load silently pooled
2021, 2022 and 2024 during a concurrent backfill on 2026-09-08.

## Version history

**v1 (2026-09-08)** — Marcel baseline plus two Statcast skill rates.
Beats Marcel by 2.2% (K%) and 4.9% (BB%) on cross-validated MAE.
