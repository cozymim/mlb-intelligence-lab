# Pitcher Evaluation Score

Symmetric to the batter score: skills in, production out, weights from
regression rather than judgment.

## Target: wOBA allowed, not whiff rate

Day 22 established that whiff rate inverts the true outcome ordering.
The sinker has the lowest whiff rate in baseball (11.7%) and a better
xwOBA than the four-seam (0.368 vs 0.392). Ranking pitchers on whiffs
penalises the 78 of 445 qualified pitchers who throw 35%+ sinkers for
doing their job.

wOBA allowed captures what actually happened at the plate regardless of
how the out was made.

## Two skills dropped for redundancy

Following the Day 16 rule that r > 0.7 means double-weighting:

| Dropped | Correlation | Kept instead | Why |
|---|---|---|---|
| whiff_pct | **0.82** with k_pct | k_pct | Whiffs are one route to a strikeout, not the whole of it, and whiff rate carries pitch-type bias |
| zone_pct | **-0.54** with bb_pct | bb_pct | Largely the same information about command |

## Learned weights (2024, 368 qualified pitchers)

wOBA allowed per 1 standard deviation:

| Skill | Coefficient | Relative |
|---|---|---|
| K% | **-0.0196** | 100% |
| Barrel% | +0.0106 | 54% |
| BB% | +0.0098 | 50% |
| HardHit% | +0.0052 | 27% |
| GB% | +0.0018 | 9% |
| Chase% | -0.0007 | 4% |

**Strikeouts carry roughly twice the weight of barrel suppression.** A
strikeout is a certain out; a batted ball can become a hit.

All signs are baseball-correct: strikeouts and chases lower wOBA
allowed, walks and hard contact raise it.

### Chase% collapses in the presence of K%

Its individual correlation with wOBA allowed is -0.17, but its
coefficient is -0.0007. Chase% correlates 0.36 with K% — pitchers who
generate chases also generate strikeouts — so K% absorbs the effect.

**Chase% is not useless; it adds nothing once K% is known.** A
coefficient cannot be read in isolation from the other features.

Candidate for removal in a future version, on the same reasoning that
removed 12 rare-pitch parameters from the whiff model.

### GB% is weak for the same structural reason

Coefficient 0.0018 despite Day 22 emphasising ground-ball induction.
GB% correlates -0.48 with Barrel%: inducing grounders suppresses
barrels, and the Barrel% coefficient already carries that. The outcome
(barrels prevented) is more direct than the mechanism (grounders).

## Sensitivity test passes

| | Value |
|---|---|
| Minimum 5-fold rank correlation | **0.985** |
| Coefficient CV, K% | 3% |
| Coefficient CV, Barrel% | 11% |

Coefficient ordering is stable across folds. Chase% and GB% are the
least stable in relative terms, consistent with their near-zero size.

## R-squared 0.524

Close to the batter model's 0.501.

**This was a genuine concern.** K% and BB% enter the model directly and
are themselves components of wOBA, which risked explaining outcomes with
outcomes. R-squared above ~0.8 would have indicated that.

It did not happen because roughly 70% of plate appearances end on a
batted ball, where defence, park and luck dominate — none of which the
model sees.

## Note on sample thresholds

Without qualification thresholds the raw table contains pitchers with
two career pitches showing zone_pct 1.000, whiff_pct 0.500 and bb_pct
0.667. Requirements: 200 swings, 100 batted ball events, 200 plate
appearances. 368 of 855 pitchers qualify.

## Limitations

- One season.
- Defence is not removed. wOBA allowed includes whether fielders
  converted batted balls; a pitcher in front of a good defence looks
  better. xwOBA would isolate this and is a candidate refinement.
- Park effects are not adjusted.
- Role is not controlled. Starters face lineups multiple times;
  relievers do not. The score does not distinguish them.
- Regression coefficients are associations, not causal effects.
