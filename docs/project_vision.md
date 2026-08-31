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