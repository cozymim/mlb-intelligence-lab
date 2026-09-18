# MLB Intelligence Lab

A public-data approximation of a Baseball Operations analytics workflow.

Built with MLB Statcast data via Baseball Savant. The goal is to move from
raw pitch-level data to validated metrics, defensible models, and baseball
decisions — with every modeling choice documented and defendable.

**[Live dashboard](https://mlb-intelligence-lab.streamlit.app)** — batter and pitcher profiles, scouting reports, and model performance including where the models failed.

**Status: Week 6 of 12.** Data foundation, batter and pitcher analytics, and a first validated model complete.

---

## Why data foundation first

Most public baseball projects jump to modeling and quietly compute the wrong
thing. This project spends its first week verifying what the data actually
is. Every claim below was confirmed in code, not assumed:

- **Count semantics.** `balls` / `strikes` are the state *before* the pitch.
  Confirmed: all 1,111 first pitches of the sample day are 0-0. This makes
  count a legitimate pre-pitch feature, with no leakage.
- **Plate appearance identity.** `at_bat_number` is unique only within a
  game. The composite key `(game_pk, at_bat_number)` is required; grouping
  on `at_bat_number` alone silently merges different games.
- **Three kinds of missingness**, which must not be conflated: structural
  (no batted ball, so no `launch_speed`), no-pitch (pitch clock violations
  have no physics at all), and genuine tracking failure.
- **Incomplete plate appearances.** 4 of 1,111. Root-caused one to a third
  out recorded against a *runner* mid-PA. Only 0.36%, but not random —
  concentrated in two-out situations with runners on — and it fails
  silently through `groupby().last()`.
- **`pitch_type` is inference, not measurement.** An algorithmic label from
  trajectory. Its value set changes between seasons (Sweeper and Slurve
  were added in 2023), which breaks naive multi-season joins.

Details and evidence: [docs/data_dictionary.md](docs/data_dictionary.md)

---

## Metric definitions

Plate discipline metrics live in one module and are covered by tests, so
notebooks cannot drift into competing definitions.

| Metric | Numerator | Denominator |
|---|---|---|
| Swing% | swings | all pitches |
| Whiff% | swings and misses | swings |
| SwStr% | swings and misses | all pitches |

Judgment calls, documented rather than assumed:

- **`foul_tip` is a swing but not a whiff** — the bat made contact.
  Counting it as a miss would overstate swing-and-miss ability.
- **Bunts are excluded from both** — a different mechanic, usually a
  tactical instruction rather than a hitter's swing decision.
- **`swinging_strike_blocked` is a whiff** — the batter missed; the ball
  merely got past the catcher.

Whiff% and SwStr% have different denominators and different meanings.
Conflating them is a common error.

---

## Leakage prevention

Two independent guards, both enforced in code rather than by discipline.

**Temporal.** All splitting goes through `src/utils/temporal.py`, which
splits by date and refuses any split where training data reaches the
start of a later partition. Demonstrated on the current sample: a random
80/20 split puts all three dates on both sides — training on August to
predict April — while the temporal split shares no date at all.

**Feature-level.** `src/utils/leakage.py` bans columns that are not
knowable at the prediction timestamp. For pitch-outcome prediction that
removes 41 of 119 columns: 26 post-outcome, 9 identifiers, 6 empty. The
guard runs on the feature matrix immediately before fitting and names
every offender.

The same column can be legal or illegal depending on the problem —
`launch_speed` is leakage for pitch-outcome prediction but a legitimate
feature for next-season projection — so bans are defined per problem,
not globally.

Known gap, documented rather than hidden: column-level guards cannot
catch derived-feature leakage. A feature named `batter_slider_whiff_rate`
looks harmless but leaks if computed over the full dataset. Rolling,
as-of-date aggregation is the highest-priority open item.

See [`docs/modeling_policy.md`](docs/modeling_policy.md).

## Batter analytics

Metrics are defined once in `src/features/`, covered by tests, and
validated against published league values.

**Strike zone.** Batter-specific vertical bounds from `sz_top`/`sz_bot`
plus a ball radius on every side. Validated against Statcast's own
`zone` column on 710,632 pitches: 932 disagreements (0.13%), all within
0.034 ft of a boundary. Omitting the vertical ball radius produced
28,662 disagreements — the asymmetry mattered.

**League values, 2024 season.** Chase% 28.2, Zone Swing% 67.4,
Contact% 76.8, Zone Contact% 84.7, Barrel% 7.8, HardHit% 39.0,
average exit velocity 88.3 mph. All within about a point of published
figures, which validates the swing and zone definitions independently.

**Sample thresholds are measured, not guessed.** Split-half correlation
gives the point where each metric reaches r ~ 0.7: HardHit% at 100
batted balls, Barrel% at 150, Chase% and Zone Contact% at 200
opportunities. Barrel% stabilises slowest because barrels are rare.
Rates below their threshold return INSUFFICIENT SAMPLE rather than a
number the data cannot support.

**Correlation structure drives evaluation design.** Barrel% and
HardHit% correlate at 0.78 — including both would double-weight power.
Contact and power trade off at -0.49 and must stay separate axes.
Plate discipline is orthogonal to contact quality (|r| <= 0.11). This
is the evidence base for weighting a batter score, rather than picking
weights by feel.

## As-of-date features

Column-level guards cannot catch derived-feature leakage: a feature
named `batter_chase_pct` looks harmless but contains the pitch being
predicted if computed over the full season.

`src/features/rolling.py` aggregates by game date using strictly
earlier dates, and shrinks toward the league mean with a regression
constant set to each metric's measured stabilization threshold.

Verified on 2024: a player's first game date returns exactly one value,
the league mean — no same-day leakage. Cross-player spread grows from
0.023 in April to 0.042 in September as evidence accumulates.

The feature earns its place: predicting September Chase% using only
data through August gives MAE 0.0377 against 0.0554 for a league-mean
baseline, a 32% improvement. **Baselines apply to features, not just
models.**

---

## Pitcher analytics

**Movement is measured from the catcher's perspective**, so `pfx_x`
flips sign with handedness. Verified across 2024: changeup +1.18 for
lefties and -1.18 for righties, sinker +1.26 vs -1.24. Vertical movement
does not flip. `src/features/arsenal.py` normalises to arm-side so both
hands can be pooled.

**Velocity separation and movement separation are independent.** Cole
Ragans' changeup separates 10.6 mph from his fastball but only 0.51 in
movement — a tunnelling pitch. Dylan Cease's slider separates 9.2 mph
and 1.43 in movement — a contrast pitch. Combining them into one
"separation" number would erase the distinction.

**Whiff rate is the wrong sole criterion for a pitch.** The sinker has
the lowest whiff rate in baseball (11.7%) and the highest ground-ball
rate (57.0%), and produces a better xwOBA (0.368) than the four-seam
(0.392), which whiffs 1.6x more often. Ranking pitches by whiff rate
reverses the true outcome order.

Standardising outcomes across pitch types reveals four success paths:
ground balls (SI), pop-ups (FF, FC, ST), swing-and-miss (SL, KC, CU),
and chase (CH, FS). 78 of 445 qualified pitchers throw 35%+ sinkers and
sit below league whiff rate while sitting 10 points above in ground-ball
rate. A whiff-based ranking penalises 17.5% of pitchers for doing their
job.

## First model: P(Whiff | Swing)

**Baselines were built before any model was fitted.** Building them
afterwards invites choosing one the model can beat.

| Model | Log Loss | AUC | ECE |
|---|---|---|---|
| Constant (league rate) | 0.55294 | — | 0.01121 |
| Lookup + zone (baseline) | 0.49466 | 0.71292 | 0.01382 |
| **Gradient boosting** | **0.44690** | **0.77741** | **0.00954** |

Test set: 54,137 September swings, evaluated once after every modelling
decision was locked on validation. 9.7% better log loss than the
baseline, and better calibrated.

Full documentation: [model card](models/artifacts/whiff_boosting/v1/model_card.md).

### A linear model lost to a two-line groupby

Logistic regression with the same features scored 0.51151 against the
baseline's 0.48524 on validation — worse than no machine learning at
all. `plate_z` correlates +0.21 with whiff for four-seams and -0.50 for
knuckle curves, and one coefficient cannot represent both.

Adding a `pitch_type x plate_z` interaction recovered it (0.47650), and
that single change was worth four times the model's eventual margin over
the baseline. **Most of the value came from finding the sign reversal,
not from the choice of algorithm.**

Without a baseline, "logistic regression, AUC 0.65" would have looked
like a result.

### Calibration is diagnosed, not assumed

The logistic model ranked well but under-predicted both tails: a 6%
prediction whiffed 12% of the time. Isotonic regression cut its ECE by
68%. Platt scaling made it worse — the output of a logistic regression
is already a sigmoid, so there was no shape left to correct.

Boosting needed no calibration at all. Applying isotonic regression to
it degraded both log loss and ECE. **The Day 27 conclusion that
calibration was essential turned out to be model-specific.**

### The error analysis changed what was tried next

Overall log loss said the model beat the baseline. Splitting by pitch
type showed it losing on three: cutters and sinkers, which have no
height effect to model, and knuckle curves, which have the strongest
height effect but too few swings to estimate it.

Two hypotheses followed. Raising the rare-pitch threshold: **wrong** —
knuckle curves are 1.8% of swings, so a 0.033 group-level loss costs
0.0006 overall, and thresholds from 500 to 6,000 spanned 0.00007.
Gradient boosting: **right** — trees split only where a split helps, so
the interaction that was noise on cutters simply is not made. Boosting
beats the logistic model on every pitch type.

### What matters, and what does not

Permutation importance: `plate_z_rel` 0.145, `plate_x_bat` 0.045,
`strikes` 0.018, `release_speed` 0.006, `release_spin_rate` 0.003.

**Location is nearly everything.** Velocity and spin — the measurements
Statcast is best known for — contribute almost nothing once pitch type
is controlled. Hyperparameters spanned 0.0012 in log loss across a wide
grid, so no tuning budget was warranted.

---

## Research findings

Three questions answered, recorded in
[docs/research_log.md](docs/research_log.md) with methods and
limitations.

**Why whiff rate falls as balls accumulate — solved.** Within two-strike
counts, whiff rate drops from 25.7% at 0-2 to 17.2% at 3-2. The cause is
composition, not pitch quality: zone rate rises from 32.5% to 58.1%, and
whiff rate differs roughly 3x between in-zone (14%) and out-of-zone
(40%) swings. Splitting by location shrinks the in-zone effect to 2.1
points. A Simpson's-paradox-shaped result, and a caution for every
aggregate in this project.

**Does velocity separation improve offspeed whiff rate — half true.**
Pooled across pitch types the correlation is 0.552; within pitch type
and controlling for fastball velocity it ranges from +0.49 (splitter)
to -0.21 (sinker). More than half the pooled figure was pitch-type
composition. The effect is real for splitters, cutters, sliders and
changeups, absent for sweepers, curveballs and four-seams. For sinkers
the variable measures stuff decay rather than separation — the same
feature means different things for different pitch types.

**Does release-point consistency predict whiff rate — no.** Across 473
pitchers, three different formulations all correlate at r < 0.02 with
whiff rate. A suspected arsenal-size confound was tested and ruled out.
The most concrete explanation is that within-pitch-type release scatter
(0.223) exceeds between-pitch-type separation (0.146): for most
pitchers there may be nothing for a hitter to read. Reported as a null
result rather than discarded.

---

## Findings so far

**Whiff rate falls as balls accumulate in two-strike counts.**
0-2: 25.0%, 1-2: 20.9%, 2-2: 19.1%, 3-2: 15.6%. This contradicted the
initial prediction that two-strike counts would uniformly raise whiff
rates. Untested hypothesis: at 3-2 the pitcher must throw a strike and the
hitter can take anything off the plate, so both sides push toward the zone.
Testable in Week 4 with `plate_x` / `plate_z`.

**Velocity and whiff rate are inversely related by pitch type.**
Sinker 92.9 mph / 10.8% whiff, four-seam 94.2 / 16.5%, versus slider
85.7 / 32.2% and changeup 86.2 / 31.4%. Consequence: whiff rate is the
wrong sole criterion for a sinker, which exists to induce ground balls.
Pitch-type-specific success criteria are needed.

Both entries, including the failed prediction, are in
[docs/research_log.md](docs/research_log.md).

---

## Repository layout

    data/raw/          immutable Statcast snapshots (gitignored)
    docs/              data dictionary, research log, project vision
    notebooks/         exploratory analysis
    src/features/      metric definitions (single source of truth)
    src/data/          validation and invariant checks
    tests/             pytest suite
    CLAUDE.md          governing specification

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    python -m pytest tests/ -v

`requirements.lock.txt` pins exact installed versions for reproducibility.

## Data handling

Raw pulls are written to Parquet with both the game date and the
**ingestion date** in the filename. Statcast is revised retroactively —
pitch classifications change and metrics are corrected — so a 2024 pull
made today is not necessarily identical to one made next year. Raw files
are never edited or overwritten.

## Roadmap

| Weeks | Focus |
|---|---|
| 1 | Data foundation (done) |
| 2 | Ingestion pipeline, DuckDB + SQL, temporal split and leakage utilities (done) |
| 3 | Batter analytics (done) |
| 4 | Pitcher analytics (done) |
| 5 | Pitch quality model, P(Whiff given Swing) (done) |
| 6-8 | Player evaluation and a performance projection system |
| 9-10 | Scouting reports, player similarity |
| 11-12 | Dashboard, KBO/MLB translation research, portfolio |

Two flagship components: a projection system benchmarked against a
Marcel-style baseline, and hierarchical Bayesian research on KBO/MLB league
translation. See [docs/project_vision.md](docs/project_vision.md).

## Limitations

MLB organizations hold proprietary data unavailable here: full
biomechanics, minor league tracking, internal medical and player
development data. This project is a public-data approximation of a Baseball
Operations analytics workflow, not a recreation of a proprietary club
system.
