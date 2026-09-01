# Modeling Policy

## Temporal splitting is mandatory

Baseball data is a time series. Random train/test splits let a model
learn from the future. This inflates validation scores and produces a
model that cannot work in deployment.

**Demonstrated on the current 3-date sample:**

| Split | Train dates | Test dates |
|---|---|---|
| Random (80/20) | 04-15, 06-15, 08-15 | 04-15, 06-15, 08-15 |
| Temporal | 04-15 | 08-15 |

The random split trains on August to predict April. It raises no error
and scores *better* than an honest split, because pitches from the same
game, pitcher, and batter appear on both sides.

## Enforcement

All splitting goes through `src/utils/temporal.py`. Models do not
implement their own.

`assert_chronological()` runs automatically inside `split_by_date()` —
the check cannot be forgotten. It raises when the training window
extends to or past the start of a later partition. Same-day overlap
also raises: at the time an afternoon game is played, that day's
earlier results may not yet be available.

## Splitting is by date, never by row index

Statcast rows do not arrive in chronological order (verified Day 3), so
`df[:8000]` assumes an ordering that does not exist. Date-based
splitting also guarantees a plate appearance cannot land in two
partitions, since a PA never spans two dates.

## Every model documents its windows

`TemporalSplit.summary()` returns row counts and date boundaries for
each partition. This goes into the model card. Documentation is carried
by the data structure so it cannot be skipped.

## Walk-forward evaluation

`expanding_window_splits()` produces (train, test) pairs where each
model trains only on data preceding its test date. This mirrors
deployment and gives multiple evaluation points instead of one.

## Open items
- [ ] Feature-level leakage checks (Day 11)
- [ ] Banned-column list for pre-pitch models (Day 11)
- [ ] Player-profile features must be computed from data strictly prior to the prediction timestamp — not yet implemented

## Feature-level leakage guards

Temporal splitting prevents learning from the future. Feature guards
prevent learning from the answer. Both are required.

### The prediction timestamp decides everything

A column is banned if its value is only knowable after the moment a
prediction must be made. The same column can be legal or illegal
depending on the problem: `launch_speed` is leakage for pitch-outcome
prediction (the ball has already been hit) but a legitimate feature for
next-season projection (it summarises last season's contact quality).

Guards are therefore defined per problem in `src/utils/leakage.py`,
never as one global blocklist.

### Pitch-outcome guard — measured on the 3-date sample

41 of 119 columns excluded:

| Reason | Count |
|---|---|
| Post-outcome (leakage) | 26 |
| Identifier / bookkeeping | 9 |
| Empty in all seasons | 6 |

78 columns remain available, and they match the pre-pitch feature list
in CLAUDE.md: release_speed, pfx_x/pfx_z, plate_x/plate_z, balls,
strikes, pitch_type, stand, p_throws, release_spin_rate,
release_extension, base state, inning, outs.

### Leaks that look harmless

- **`type`** — the B/S/X summary. Innocuous name, but it is the answer.
- **`estimated_woba_using_speedangle`** — "expected" does not mean
  "pre-pitch". It is MLB's own model output, computed from exit velocity
  and launch angle, i.e. entirely post-contact.
- **`delta_run_exp` / `delta_home_win_exp`** — the outcome expressed as
  a run/win value.
- **`post_*_score`** — state after the pitch resolved.

### Enforcement

`check_features()` runs on the feature matrix immediately before
fitting and raises `LeakageError` naming every offender.
`safe_features()` drops banned columns and re-verifies, which catches
the case where the ban list is extended but a cached feature matrix is
not rebuilt.

`describe_exclusions()` produces the excluded-column table with reasons,
which goes directly into the model card.

### NOT yet handled: derived-feature leakage

Column-level guards cannot catch this. A feature named
`batter_slider_whiff_rate` looks harmless, but if it is computed over
the full dataset then the pitch being predicted is inside its own
average.

**Rule for Week 3 onward:** any player-profile aggregate must be
computed strictly from data preceding the prediction timestamp.
`expanding_window_splits()` is the basis for this. Not yet implemented —
this is the highest-priority open item.