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
- [ ] Player-profile features must be computed from data strictly prior
      to the prediction timestamp — not yet implemented