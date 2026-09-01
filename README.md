# MLB Intelligence Lab

A public-data approximation of a Baseball Operations analytics workflow.

Built with MLB Statcast data via Baseball Savant. The goal is to move from
raw pitch-level data to validated metrics, defensible models, and baseball
decisions — with every modeling choice documented and defendable.

**Status: Week 1 of 12 — data foundation.** No models yet by design.

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
    pip install -r requirements.txt
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
| 4 | Pitcher analytics |
| 5 | Pitch quality model, P(Whiff given Swing) |
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
