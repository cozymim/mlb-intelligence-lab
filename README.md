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
| 2 | Ingestion pipeline, DuckDB + SQL, temporal split and leakage utilities |
| 3-4 | Batter and pitcher analytics |
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
