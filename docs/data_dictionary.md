# Data Dictionary

## Source
MLB Baseball Savant / Statcast via pybaseball 2.2.7
API: `statcast(start_dt, end_dt, team=None, verbose=True, parallel=True)`
Dates as "YYYY-MM-DD" strings.

## First inspection — 2024-04-15 (single day)
- Rows (pitches): 4,362
- Columns: 119
- Ingested: 2026-08-31
- File: data/raw/statcast_2024-04-15_ingested_2026-08-31.parquet (0.82 MB)

## Missingness

### Fully empty (100%) — do not use
tfs_deprecated, tfs_zulu_deprecated, spin_dir, spin_rate_deprecated,
break_length_deprecated, break_angle_deprecated, sv_id, umpire

Column existence does not imply data availability. Use release_spin_rate
and spin_axis for spin instead.

### Structural missingness — expected, do not impute
- launch_speed 66.3%, launch_angle 66.2% — most pitches are not batted
- events / woba_value / babip_value / des — all exactly 74.55%: recorded
  only on the final pitch of a plate appearance. Implies ~3.9 pitches/PA.
- on_1b 70.4% / on_2b 81.3% / on_3b 90.8% — missing means base empty.
  Convert with .notna() before use; never fillna(0).

### Tracking failure — different from the above
launch_speed missing on 1 of 773 batted balls (0.13%).

## Pitch outcome columns

`type` has 3 values (B / S / X) and is too coarse: `foul` is bucketed into
S, which is why 34% of S rows have a launch_speed.

`description` is the precise column (12 values on this date):
ball 1436, foul 798, hit_into_play 773, called_strike 758,
swinging_strike 416, blocked_ball 92, foul_tip 37,
swinging_strike_blocked 20, automatic_ball 16, foul_bunt 8,
hit_by_pitch 7, missed_bunt 1

Verified: the 7 swing-related values sum to 2,038 = type 'S' count.

### Open questions for the whiff model (Week 5)
- Is `foul_tip` a whiff? Bat contact occurred, so likely not.
- Are bunts (`foul_bunt`, `missed_bunt`) swings? Different mechanic;
  common practice is to exclude.
- These must be decided and documented before defining Swing% / Whiff%.

## Notes
- `automatic_ball` reflects the 2023 pitch timer rules; will not exist
  in pre-2023 seasons.
- Always start from `description`, aggregate up if needed. Never the reverse.

---

## Data hierarchy (verified 2024-04-15)

game_pk > at_bat_number > pitch_number

- games: 15, plate appearances: 1,111, pitches: 4,362
- 3.93 pitches per PA — matches the 74.55% events-missing rate observed
  earlier. Two independent paths agree, which is a good pipeline signal.
- `at_bat_number` is unique only WITHIN a game (max 86 here).
  Composite key (game_pk, at_bat_number) is required to identify a PA.
  Grouping on at_bat_number alone silently merges different games.

### Sort order (mandatory before any temporal operation)

```python
df.sort_values(["game_pk", "at_bat_number", "pitch_number"])
```

Statcast does not arrive in chronological order. Unsorted `shift()` or
cumulative operations leak future information into the past.

### Count semantics — verified

`balls` / `strikes` are the count BEFORE the pitch is thrown, not the
result of it. Confirmed two ways: all 1,111 first pitches are 0-0, and
counts advance consistently with the previous pitch's description.

=> Count is a legitimate pre-pitch feature for the whiff model.

### Incomplete plate appearances — 4 of 1,111 (0.36%)

**Type 1 — no `events` at all (1 PA)**
Verified: game_pk 746080, top 6th, at_bat_number 44.
Count 0-2, 2 outs, runner on 1B, description `blocked_ball`.
The third out was recorded against the RUNNER, not the batter, so the
PA disappeared with no outcome.

**Type 2 — events == `truncated_pa` (3 PAs)**
PA cut short for game-level reasons.

**Why 0.36% still matters:**
- Scales to hundreds of PAs across a full season
- NOT random — concentrated in 2-out situations with runners on base,
  so a specific game state is removed systematically
- Fails silently: `groupby(...).last()` returns NaN rather than raising

**Rule:** always filter with `events.notna()` for PA-level aggregation,
and log how many rows were dropped. Never drop silently.

### events values (18 on this date)

field_out 494, strikeout 234, single 153, walk 87, double 47,
force_out 22, grounded_into_double_play 20, home_run 20,
hit_by_pitch 7, sac_fly 6, sac_bunt 5, truncated_pa 3,
intent_walk 3, catcher_interf 3, triple 2, fielders_choice 2,
field_error 1, double_play 1

K% = 234/1111 = 21.1%
BB% (including intentional) = 90/1111 = 8.1%
Both consistent with 2024 league averages.

**Open decision (Week 3):** `intent_walk` is a separate value from
`walk`. Intentional walks reflect managerial strategy rather than
batter skill, so standard practice excludes them from batter BB%.
Must be fixed and documented before computing rate stats.

**Also note:** computing AVG requires classifying all 18 event values
into hits / at-bats / non-at-bats. Sacrifices, HBP, catcher
interference, and truncated PAs are excluded from at-bats. This is
more involved than it first appears — handle it in Week 3, not ad hoc.