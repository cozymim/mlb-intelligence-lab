# Project Vision — Revisions

## 2026-08-31 — Flagship components and roadmap adjustment

Two components elevated to flagship status:
1. Performance projection system (Week 6-8)
2. KBO ↔ MLB translation research (Week 7 investigation, Week 11-12 build)

**Game Win Probability demoted to stretch.**
Reason: hundreds of public win-probability projects exist; it does not
differentiate. KBO translation is work almost no other candidate can
do. Resources go to the differentiated component.

Elo team strength follows Game Prediction into stretch.

## Revised roadmap

| Week | Focus |
|---|---|
| 1 | Foundation, environment, first Statcast pull |
| 2 | Ingestion pipeline, DuckDB + SQL, temporal/leakage utilities |
| 3 | Batter analytics |
| 4 | Pitcher analytics |
| 5 | Pitch quality model — P(Whiff \| Swing) |
| 6 | Player evaluation · projection system begins · **scope checkpoint** |
| 7 | Projection validation · **KBO data availability investigation** |
| 8 | Projection system completion |
| 9 | Scouting intelligence |
| 10 | Player similarity |
| 11 | Dashboard · KBO research begins |
| 12 | KBO research completion · portfolio · interview prep |

Stretch (only if core finishes): game win probability, Elo,
batter-vs-pitcher matchup, pitch sequencing, undervalued player finder.

## Third baseline requirement (extends CLAUDE.md §6)

For the projection system, three baselines are required:
1. Constant (league average)
2. Lookup (previous season + age adjustment)
3. Marcel-style projection (weighted 3-year average, regression to
   mean, age adjustment)

A model that does not beat Marcel is not a result. Report it honestly.

## 2026-09-01 — Dashboard scope decision

**System first, app as a thin window.**

Every analysis function returns a DataFrame or dict. The dashboard calls
those functions and displays results — no calculation logic lives in
dashboard code. The system must be complete and defensible without the
app; the app exists so a reader who will never open a notebook can see
the work in 30 seconds.

**Scope: 4-5 pages, not 12.** Batter profile, pitcher profile,
projection, model performance, KBO research. Filled pages beat empty
ones.

**Model Performance page is mandatory and must not be sanitized.**
Baselines, our model, calibration curve, train/val/test windows,
feature list, limitations, and failures. This is where an R&D
interviewer actually spends time. "XGBoost beat the lookup baseline by
3%" told honestly is stronger than ten polished heatmaps.

**Deploy it.** Streamlit Community Cloud. A link on a résumé is not the
same as "clone and run locally." Constraint to design for now:
deployment cannot carry full Statcast data, so the app must read small
pre-aggregated Parquet files, not raw pitch data.
## 2026-09-03 — Week 6 scope checkpoint

30 of 72 days complete (42%). Six components remain for 42 days, and
Week 5 took six days for a single model.

**Considered cutting player similarity and scouting reports. Rejected.**

Scouting is the dashboard's reason to exist. A front-office user asks
"how do I attack this hitter", not "show me a metric table". Splitting
scouting out into standalone markdown reports would break the flow that
makes the dashboard useful — select a player, see the profile, generate
the report — and would leave the dashboard as a viewer with no decision
attached to it.

**Cut instead: the projection system's metric coverage.**

Originally intended to project several outcomes. Narrowed to **K% and
BB% only**.

Rationale:
- The result that matters is whether the system beats a Marcel-style
  baseline, not how many metrics it covers. Projecting five metrics and
  losing to Marcel on all five is not a result.
- K% and BB% stabilise fastest of any rate (Day 16), so validation is
  clean rather than dominated by noise.
- Both apply to hitters AND pitchers, so one methodology covers two
  domains.
- The framework extends cheaply. Adding xwOBA later is a configuration
  change, not new work.
- AVG was already flagged as near-unpredictable (BABIP noise), so
  excluding it costs nothing.

## Revised roadmap

| Week | Focus |
|---|---|
| 6 | Batter/pitcher evaluation scores · **KBO data investigation** |
| 7 | Projection system — Marcel baseline, K% and BB% |
| 8 | Projection validation · scouting report logic |
| 9 | Player similarity |
| 10 | KBO translation research |
| 11 | Dashboard (batter, pitcher, scouting, similarity, model performance) |
| 12 | Portfolio, README, interview preparation |

**KBO data investigation moved forward from Week 7 to Week 6.** If the
data does not exist, the Week 10 flagship disappears and the plan needs
rebuilding. That risk is worth surfacing now rather than in six weeks.
The investigation itself is a day's work and its outcome reshapes
everything after it.

**Next checkpoint: end of Week 9.** If the projection system or KBO
research is behind, similarity is the first thing to go — it is the most
replaceable component and the least differentiated.
