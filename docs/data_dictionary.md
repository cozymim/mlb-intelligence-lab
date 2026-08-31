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