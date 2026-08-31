# CLAUDE.md — MLB Intelligence Lab

Governing instructions for this repository. Read this file before any task.
If a request conflicts with this file, say so before acting.

---

## 1. Project Identity

**MLB Intelligence Lab** is a public-data approximation of a professional Baseball
Operations analytics workflow. It is a serious portfolio project targeting roles in
Baseball Operations, Baseball Analytics, Baseball R&D, player evaluation, player
development, quantitative scouting, and sports data science.

It is **not** a tutorial, not a Kaggle-style notebook dump, and not a gambling system.

The owner is building this to **learn and to be able to defend every decision in a
technical interview**. Code that the owner cannot explain has negative value here.

### Prime directive

```
DATA → MODEL → BASEBALL INSIGHT → BASEBALL DECISION
```

### The Ten-Question Gate

No model, metric, or feature set enters the repository until all ten are answered in
writing (in the relevant `docs/` file or the research log):

1. What baseball question does this solve?
2. Who in a front office would use it?
3. What decision does it support?
4. What information is actually available at prediction time?
5. What baseline are we trying to beat?
6. Why this model class?
7. How are we validating it?
8. Where could leakage exist?
9. How reliable is the result (uncertainty, sample size)?
10. What are the limitations?

If a question cannot be answered, the work is not ready. Stop and discuss.

---

## 2. How We Work Together

**Teaching is a deliverable, not a courtesy.** For every meaningful task:

1. What we are building
2. Why it matters to baseball
3. The relevant baseball concept
4. The relevant Python / SQL / statistics / ML concept
5. Which files change
6. The implementation
7. Explanation of the non-obvious sections
8. How to run it
9. Expected output
10. How to verify correctness
11. Likely errors and fixes
12. Conceptual checkpoint before moving on

**Do not do everything automatically.** When a step is the learning point — running the
first Statcast pull, initializing Git, inspecting a schema, interpreting a calibration
curve — guide the owner through doing it rather than doing it silently.

**Incremental development.** One coherent unit of work at a time. Do not scaffold the
entire repository, do not generate a thousand lines across ten new files, and do not
advance to the next day/week without an explicit go-ahead.

**Push back.** If an approach is statistically unsound, leaky, or unnecessarily complex,
say so directly before implementing it.

---

## 3. Data Source Policy

Primary source: **MLB Baseball Savant / Statcast**.

- https://baseballsavant.mlb.com/
- https://baseballsavant.mlb.com/statcast_search
- https://baseballsavant.mlb.com/csv-docs
- https://www.mlb.com/glossary/statcast

Access via `pybaseball` where appropriate (`statcast`, `statcast_pitcher`,
`statcast_batter`, `playerid_lookup`).

### Rules

- **Never invent library functions, arguments, Statcast column names, or metric
  definitions.** Verify against installed package source (`help()`, `inspect`) or
  official docs before writing code that depends on them.
- **All external data access goes through one adapter module**
  (`src/data/ingestion/statcast_client.py`). No notebook or model calls `pybaseball`
  directly. If the upstream library breaks or changes, exactly one file changes.
- **Cache aggressively; download once.** Every pull is written to
  `data/raw/` as Parquet before anything else touches it. Re-running a pipeline must
  not re-download.
- **Incremental ingestion.** Pull by date range, skip ranges already present, respect
  rate limits, and back off politely. Savant is a free public service — do not hammer it.
- **Raw data is immutable.** Never edit, clean, or overwrite a file in `data/raw/`.
- **Snapshots are dated.** Statcast is retroactively revised (pitch reclassification,
  metric corrections). Record ingestion date in the filename or a sidecar manifest, so
  results are reproducible and re-pulls are detectable.
- **Never commit raw data to Git.** `data/` is gitignored except `.gitkeep` and small
  reference tables in `data/external/`.
- Check terms of service before scraping any non-Savant source. No restricted scraping.

---

## 4. Data Integrity Rules

Before modeling anything, inspect: schema, dtypes, row counts, missingness by column,
per-season availability, and distribution shifts across seasons.

### Known discontinuities — treat these as first-class modeling concerns

Verify each against documentation before relying on it, but be aware:

| Break | Why it matters |
|---|---|
| Tracking hardware changed to Hawk-Eye around 2020 | Spin, extension, and movement measurements are not perfectly comparable to earlier seasons |
| 2020 was a shortened season | Sample sizes, roster/usage patterns, no fans |
| Pitch classification changes (e.g. sweeper/slurve added in 2023) | `pitch_type` is not a stable category across years; earlier data was reclassified |
| 2023 rule changes (pitch timer, shift restrictions, larger bases) | BABIP, running game, and run environment shift — affects win probability and batted-ball models |

Any model spanning these boundaries must either restrict its window or include an era
control, and must document the choice.

### Field-level rules

- **Do not assume a field exists for every season.** Check, then handle.
- **Missingness is not random.** Distinguish *structural* missingness (`launch_speed`
  is absent because no ball was hit) from *tracking failure*. Never `fillna(0)` or
  mean-impute without documenting why in `docs/data_dictionary.md`.
- **Player identity:** MLBAM IDs (`batter`, `pitcher`) are the canonical keys. Player
  names are display fields only, never join keys or database keys.
- **Handedness is per plate appearance.** `stand` reflects the stance used in that PA.
  Never collapse a switch hitter into a single handedness.
- **`pitch_type` needs a mapping table** with deprecated codes handled explicitly, and a
  documented policy for `NaN` / rare / unclassified pitches.

### Core fields we expect to use

`pitch_type, game_date, game_year, game_pk, at_bat_number, pitch_number, player_name,
batter, pitcher, stand, p_throws, events, description, zone, balls, strikes,
release_speed, release_pos_x, release_pos_z, release_spin_rate, release_extension,
effective_speed, spin_axis, pfx_x, pfx_z, plate_x, plate_z, launch_speed, launch_angle,
launch_speed_angle, estimated_ba_using_speedangle, estimated_woba_using_speedangle,
woba_value, on_1b, on_2b, on_3b, outs_when_up, inning, inning_topbot, home_team,
away_team, home_score, away_score`

---

## 5. Metric Definition Policy

Every metric in this repository falls into exactly one of three tiers, and must be
labeled as such in `docs/data_dictionary.md`:

1. **Official Statcast/MLB metrics** (Barrel%, HardHit%, xwOBA, Sweet Spot%, …) — use
   MLB's published definition verbatim, cite the glossary URL, and do not modify it.
   **Note that xBA / xSLG / xwOBA are themselves MLB model outputs**, not raw
   observations. Never present them as our own modeling work.
2. **Standard derived metrics** (Chase%, Zone Contact%, Whiff%, K%, BB%, run value) —
   the exact numerator, denominator, and filter conditions must be written down. "Run
   value" in particular must state which run expectancy table is used and its source.
3. **Our original metrics** (Batter Impact Score, Pitcher Impact Score, pitch quality
   outputs) — clearly labeled as ours, with methodology documented.

**Never invent a definition.** If unsure, verify or flag it.

---

## 6. Modeling Policy

### Mandatory ladder

```
BASELINE → SIMPLE MODEL → VALIDATION → ERROR ANALYSIS → ADVANCED MODEL → INTERPRETATION
```

**Two baselines are required, not one:**

- a *constant* baseline (league average rate), and
- a *lookup baseline* — a grouped mean over obvious categories (e.g. whiff rate by
  `pitch_type` × count × handedness).

A machine-learning model that does not beat the lookup baseline is not a result. Report
that honestly rather than hiding it.

Complexity is earned. Logistic regression before trees, trees before boosting. Every
step up in complexity requires a measured improvement on the validation set.

Fixed random seeds everywhere. Every trained model gets a version and a **model card**
in `models/artifacts/<model_name>/<version>/model_card.md` containing: target, features,
training/validation/test windows, baselines, metrics, calibration, feature importance,
leakage analysis, and limitations.

### Evaluation

For probability models: **Log Loss, Brier Score, calibration (reliability diagram +
expected calibration error)**, ROC-AUC, PR-AUC where class imbalance warrants it.

Accuracy alone is never sufficient. Calibration is the metric that matters most for a
front office — a 30% whiff probability must actually whiff about 30% of the time.

Always report performance **relative to baseline**, not just in absolute terms.

---

## 7. Temporal Validation Policy

Baseball data are chronological. **Random train/test splits are prohibited** unless a
specific, documented reason exists.

Default: train on earlier seasons, validate on a later season, test on the latest
(e.g. train 2021–2023, validate 2024, test 2025). Rolling or expanding windows where
appropriate.

Split logic lives in **one tested module** (`src/utils/temporal.py`). Models do not
implement their own splitting.

Every model documents: prediction timestamp, training period, validation period, test
period, features available at prediction time, excluded features, leakage risks.

---

## 8. Data Leakage Policy

Leakage is the single most likely way this project fails an interview. Treat it as a
blocking concern.

**Leakage checklist — run before every model:**

- [ ] Does any feature encode the outcome, or a consequence of the outcome?
- [ ] For pitch-level prediction: are any post-release / post-contact fields present?
      (`launch_speed`, `launch_angle`, `events`, `description`, `woba_value`,
      `estimated_*_using_speedangle`, `zone` if outcome-derived)
- [ ] For pregame prediction: does anything from that game appear in the features?
- [ ] For future-performance prediction: does any future-season statistic appear?
- [ ] Are aggregates (season rates, player profiles) computed **only** from data before
      the prediction timestamp?
- [ ] Was scaling / encoding / imputation fit on training data only?
- [ ] Do the same player-seasons appear in both train and test in a way that leaks?

Player-profile features are the most dangerous case: a batter's "chase rate" must be
computed from pitches strictly prior to the pitch being predicted, or from a prior
season — never from the full dataset.

Leakage prevention must be covered by tests in `tests/`.

---

## 9. Sample Size Policy

Baseball is dominated by small-sample noise. Rules:

- Every leaderboard, ranking, or scouting statement carries a **minimum threshold**
  (pitches, PA, batted balls, or pitches per pitch type) and states it.
- Apply regression to the mean / shrinkage / Empirical Bayes where rates are being
  compared across players.
- Report uncertainty (confidence or credible intervals) alongside point estimates.
- If a sample is inadequate for a scouting claim, output **`INSUFFICIENT SAMPLE`**.
  Never generate a recommendation the data does not support.
- Head-to-head batter-vs-pitcher history is almost always too small to model directly.
  Compare underlying skill profiles instead.

---

## 10. Explainability Policy

Tools: feature importance, permutation importance, SHAP.

- Clearly separate **global** model behavior from **individual** prediction explanations.
- Feature importance is **not causal evidence**. Never write causal language about it.
- Do not draw biomechanical or mechanical conclusions from public tracking data.

Every matchup or scouting statement must trace to a computed number. Example:
"elevated whiff rate against sliders below the zone" is acceptable **only** if that rate
was calculated, meets the sample threshold, and can be pointed to in a table.

---

## 11. LLM Role and Anti-Fabrication Rule

**Claude is never the statistical model.**

```
STATCAST → PYTHON / SQL → STATISTICAL ANALYSIS → ML MODEL
         → STRUCTURED RESULTS → CLAUDE API → SCOUTING NARRATIVE
```

If the Claude API is integrated later, its only job is translating structured numeric
output into readable scouting language. It receives numbers; it never produces them.

**Absolute prohibition: no fabricated statistics.** Not in code, not in comments, not in
documentation, not in README examples, not in placeholder text, not in conversation.
If a number is not computed from data in this repository, it does not get stated. When
illustrating a format before real data exists, mark values explicitly as
`<PLACEHOLDER — NOT REAL>`.

---

## 12. Repository Structure

Grow the tree as needed. **Do not create empty directories in advance.**

```
mlb-intelligence-lab/
  README.md  CLAUDE.md  .gitignore  .env.example
  pyproject.toml  requirements.txt
  config/
  data/                      # gitignored
    raw/  processed/  features/  external/
  docs/
    project_vision.md  architecture.md  data_sources.md
    data_dictionary.md  database_schema.md  feature_dictionary.md
    modeling_policy.md  data_leakage_policy.md
    research_log.md  interview_notes.md
  notebooks/
    01_data_exploration/  02_batter_analysis/
    03_pitcher_analysis/  04_model_research/
  src/
    data/ (ingestion, validation, preprocessing, schemas)
    features/ (batter, pitcher, team, matchup)
    models/ (pitch_quality, player_evaluation, matchup, game_prediction)
    scouting/  visualization/  database/  utils/
  dashboard/
  reports/ (scouting, research)
  models/artifacts/
  sql/ (schema, queries, marts)
  tests/  scripts/  logs/
```

`data/external/` holds small committed reference tables: run expectancy matrix, pitch
type mapping, park identifiers, player ID crosswalk.

---

## 13. Code Quality Standards

- Python 3.12. Clear names, small modular functions, docstrings, type hints where they
  help, structured logging (never bare `print` in `src/`), explicit error handling.
- Configuration in `config/` + `.env`, never hardcoded. `pathlib` for all paths, never
  absolute strings.
- **Secrets never enter Git.** `.env` is gitignored; `.env.example` documents keys.
- Add a dependency only when it solves a real problem. Pin versions.
- **Notebook policy:** notebooks are for EDA, experimentation, and visual research.
  Once logic is reused, it moves into `src/` and the notebook imports it. The finished
  project must not be a pile of notebooks. Strip notebook outputs before committing.

Likely stack: pandas, NumPy, SciPy, scikit-learn, XGBoost, pybaseball, DuckDB (see §14),
SQLAlchemy, Matplotlib, Plotly, Streamlit, SHAP, pytest.

---

## 14. SQL and Database Policy

SQL is a graded component of this project — write real analytical SQL, not ORM calls.

**Start with DuckDB, not PostgreSQL.** DuckDB queries Parquet files directly with full
analytical SQL and zero server administration, which fits a single-user analytical
workload. The SQL skill transfers unchanged. A PostgreSQL deployment can be added late
in the project to demonstrate that capability, if there is time.

Target tables: `players, teams, games, pitches, plate_appearances, batted_balls,
player_season_stats, pitcher_pitch_types, batter_features, pitcher_features,
team_features, model_predictions`.

Keys are MLBAM IDs. Schema documented in `docs/database_schema.md`. Representative
queries live in `sql/queries/` as real `.sql` files: pitcher performance by pitch type,
batter xwOBA by pitcher handedness, pitch usage by count, chase rate by zone, bullpen
workload over prior N games.

---

## 15. Testing Policy

`pytest`. Priority targets:

- Metric calculations (verified against a hand-computed or Savant-published value)
- Data validation and schema contracts
- Feature generation correctness
- **Temporal splitting** — no train row may postdate any test row
- **Leakage prevention** — banned columns cannot reach a model's feature matrix
- Player filtering and sample-size thresholds

A metric without a test is not trustworthy enough to put in a scouting report.

---

## 16. Documentation and Research Log

Documentation is written **as work happens**, not retroactively.

`docs/research_log.md` — every substantive analysis gets an entry:
`DATE / QUESTION / HYPOTHESIS / DATA / METHOD / RESULT / INTERPRETATION / LIMITATIONS /
NEXT STEP`. **Record failures and dead ends** — those are the most interview-valuable
entries.

`docs/interview_notes.md` — for every major model, the owner must be able to answer:
what problem, why this target, why these features, why this model, what baseline, how
split, how leakage was prevented, which metric matters, what failed, what the limits
are, how a front office would use it, what proprietary data would improve.

### Definition of Done

A component is done only when it has: code in `src/`, tests, a `docs/` entry, a research
log entry, and a git commit with a meaningful message.

---

## 17. Git Policy

Small, focused, meaningfully-messaged commits. No large commits mixing unrelated work.

```
feat: add statcast ingestion pipeline
feat: add batter plate discipline metrics
model: add whiff probability baseline
test: add temporal split tests
docs: document leakage policy
fix: handle missing statcast pitch types
```

---

## 18. Scope Management

The full vision is larger than 12 weeks of part-time work. **A deep, well-validated
subset beats a shallow full sweep** for hiring purposes. Components are therefore tiered:

**Core (must ship, fully validated):**
data platform · batter analytics · pitcher analytics · pitch quality model
(`P(Whiff | Swing)`) · player evaluation scores · scouting reports · dashboard ·
one original research question

**Stretch (ship only if core is genuinely finished):**
batter-vs-pitcher matchup model · game win probability + Elo · player similarity ·
pitch sequencing · undervalued player finder

**Week 6 checkpoint:** assess progress honestly. If behind, cut stretch scope rather
than reducing rigor on core components. Depth is the product.

---

## 19. Roadmap

| Week | Focus |
|---|---|
| 1 | Project foundation, environment, Git, first Statcast pull, field literacy |
| 2 | Ingestion pipeline, validation, DuckDB + SQL, **temporal split + leakage utilities with tests** |
| 3 | Batter analytics (plate discipline, contact quality, pitch-type, zone) |
| 4 | Pitcher analytics (arsenal, movement, release, location) |
| 5 | Pitch quality model — `P(Whiff \| Swing)`, baseline ladder, calibration |
| 6 | Player evaluation scores · **scope checkpoint** · original research question defined |
| 7 | Matchup modeling (or core deepening) · research data collection begins |
| 8 | Game prediction / Elo (stretch — cut first if behind) |
| 9 | Scouting intelligence and report generation |
| 10 | Player similarity · research analysis |
| 11 | Dashboard integration |
| 12 | Validation sweep, research writeup, README, portfolio, interview prep |

Deviations from this order require a stated technical reason.

Note: leakage/temporal tooling moved to Week 2 (before the first model, not alongside
it), and original research starts in Week 6 rather than being compressed into Week 12,
because original research is the highest-value differentiator for R&D roles.

---

## 20. Success Criteria

By completion the owner can: analyze a batter's strengths and weaknesses; analyze a
pitcher's arsenal and pitch quality; evaluate hitters and pitchers quantitatively;
compare a specific matchup; generate quantitative scouting reports; estimate pregame win
probability; find similar players; explain why models predict what they predict; show
validation and calibration; explain the pipeline and database architecture; present
original research; and defend every modeling choice in an interview.

---

## 21. Hard Prohibitions

1. No fabricated statistics, metrics, field names, or library functions — ever.
2. No random train/test splits on chronological data.
3. No post-outcome information in pre-outcome predictions.
4. No recommendations from inadequate samples — output `INSUFFICIENT SAMPLE`.
5. No invented metric definitions where official ones exist.
6. No arbitrary, unjustified weights in composite scores.
7. No hiding poor model performance.
8. No causal claims from feature importance.
9. No secrets, no large raw data in Git.
10. No betting/gambling optimization or profitability framing.
11. No scraping restricted sources without checking terms.
12. No bulk code generation without teaching.

---

## 22. Public Data Limitation

Professional clubs hold proprietary data unavailable here: full biomechanics, bat
tracking history, minor league tracking, internal medical and player development data,
and proprietary defensive positioning inputs.

This project must always be described as a **public-data approximation of a Baseball
Operations analytics workflow** — never as a recreation of a proprietary MLB system.
State this in the README. Honest framing is a strength in front-office interviews.
