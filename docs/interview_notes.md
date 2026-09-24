# Interview notes

Numbers and answers for the questions this project invites. Written so
they do not have to be recalled under pressure.

## The 30-second version

A public-data approximation of a Baseball Operations analytics workflow:
710,632 pitches from 2024 turned into metrics, four models, and scouting
recommendations, plus a hierarchical Bayesian study of KBO-to-MLB
translation built on data transcribed by hand.

Every modelling decision is documented, including the ones that failed.

## Headline results

| Model | Result |
|---|---|
| P(Whiff given Swing) | log loss 0.44690 on a held-out September test set, **9.7% better** than a lookup baseline, AUC 0.777 |
| Season projection | K% MAE 0.0265, BB% 0.0137 — beats Marcel by 2.2% and 4.9% |
| Batter evaluation | weights learned from wOBA; rank correlation 0.990 under resampling |
| KBO translation | mu = -0.427, tau = 0.229 across 47 transition players |

## "What went wrong?"

The most useful question, and there are real answers.

**A linear logistic regression lost to a two-line groupby.** 0.51151
against the baseline's 0.48524. The cause: plate_z correlates +0.21 with
whiff for four-seams and -0.50 for knuckle curves, and one coefficient
cannot represent both. Adding a pitch-type interaction recovered it, and
that single change was worth four times the model's eventual margin over
the baseline. **Most of the value came from finding the sign reversal,
not from choosing an algorithm.**

**The first evaluation score failed its own sensitivity test.**
Power-heavy and contact-heavy rankings correlated at Spearman 0.053 and
shared two names in their top tens. The score measured my weighting
choice, not the batter. Rebuilt with weights regressed on observed wOBA:
0.053 becomes 0.990.

**A five-feature projection model gained nothing.** It scored 3.7%
better in training and identical to the baseline under cross-validation.
All of it was overfitting, at a condition number of 14.2 — below the
textbook threshold of 30. Dropping three features improved the result.

**A concurrent backfill silently corrupted an analysis.** Identical code
returned different numbers because a background download had added 2021
and 2022 files to a directory the loader read wholesale. The only signal
was remembering a value from the previous day. Every load now states its
seasons explicitly.

**Deployment found a bug nothing else could.** requirements.txt contained
"pytestscikit-learn" — one package name run into another by an echo
append against a file with no trailing newline. Invisible locally,
because both were already installed.

## "Why only hitters in the KBO work?"

Because pitchers were attempted and the data said no.

Cross-league correlation is 0.77 for hitter K% and **0.08** for pitcher
K%. Pitcher BB% looked usable at 0.64 with p = 0.001 — until the sample
floor rose from 200 to 400 batters faced, where it collapsed to 0.02.
Raising a floor removes noise and should strengthen a real relationship.

The explanation that fits: a hitter's contact ability is his own and
survives the move, while a pitcher's strikeout rate depends on who he
faces, and KBO hitters strike out far less.

The negative result earns its place twice: it prevents a bad model, and
it shows the hitter result is a property of hitters rather than of the
method.

## "How do you know your numbers are right?"

**Baselines were fixed before any model was fitted**, every time.
Building one afterwards invites choosing something beatable.

**174 tests**, several of which encode a specific bug that occurred.
test_season_filter_restricts_the_load exists because of the backfill
incident. test_unmeasured_damage_is_not_reported_as_safe exists because
an intermediate scouting report recommended attacking Aaron Judge's
curveball — the pitch he barrels at 23.5% on a sample too small to
trigger a warning.

**The test set was evaluated once**, after every decision was locked on
validation. September turned out to be a different environment — whiff
rate a full point higher — and both the model and its baseline degraded
by almost exactly the same amount, with AUC unchanged. A random split
would have hidden that entirely.

**Hand-entered data was validated against baseball identities**: hits
cannot exceed at-bats, strikeouts cannot exceed plate appearances,
intentional walks cannot exceed walks. 193 batting lines and 73 pitching
lines passed.

## "What would you do differently?"

**Measure the size of an effect before chasing it.** Knuckle curves cost
the whiff model 0.033 in log loss, which looked alarming until it turned
out they are 1.8% of swings — 0.0006 overall. A day went into a
hypothesis that thresholds would help. They changed log loss by 0.00007.

**Never read structure off extreme values.** Twice: release consistency
against arsenal size, and feature importance for similarity. Dropping
launch angle looked obviously correct from Aaron Judge's numbers and was
the worst available decision league-wide.

**Get birth dates early.** Age confounds the most interesting KBO
finding — nine of eleven players returned from Korea with a worse
strikeout rate, but a KBO stint costs two to four years and K% rises with
age. The two effects cannot be separated without dates the cached player
register does not carry.

## Things I can defend in detail

- Why whiff rate is the wrong way to rank a sinker: 11.7% whiff, worst in
  baseball; 57.0% ground balls, best; xwOBA better than a four-seam.
  Ranking on whiffs penalises 78 of 445 qualified pitchers.
- Why the count/whiff relationship inverts — Simpson's paradox: zone rate
  rises from 32.5% at 0-2 to 58.1% at 3-2, and within location the effect
  nearly vanishes.
- Why tau matters more than mu in the KBO model, and why that means the
  intervals stay wide no matter how many KBO plate appearances a prospect
  accumulates.
- Why boosting needed no calibration while the logistic model did.
