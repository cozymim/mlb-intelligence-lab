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

---

## Plate discipline metric definitions (decided 2026-08-31)

### Swing (denominator)
foul, hit_into_play, swinging_strike, swinging_strike_blocked, foul_tip

### Whiff (numerator)
swinging_strike, swinging_strike_blocked

### Excluded entirely
foul_bunt, missed_bunt

### Rationale — these are judgment calls, not obvious defaults

**foul_tip is a swing but NOT a whiff.** Rule-wise it is a strike (and a
strikeout with two strikes), but the bat made contact. A whiff metric
measures failure to make contact. Including foul tips would overstate a
pitcher's swing-and-miss ability.

**Bunts excluded from both.** Different mechanic entirely — the bat is
placed, not swung. Unrelated to swing decisions or contact ability, and
usually a tactical instruction rather than a hitter choice. Standard
practice in public analysis is to exclude.

**swinging_strike_blocked counts as a whiff.** The batter missed; the
ball merely got past the catcher. Identical from the hitter's side.

These definitions are debatable. What matters is that they are fixed
and documented, not that they match every other analyst.

### Verification
- All 5 non-swing values confirmed: ball, called_strike, blocked_ball,
  automatic_ball, hit_by_pitch
- Subset check passed: whiffs ⊆ swings (0 violations)

### League rates — 2024-04-15, 4,362 pitches
| Metric | Value | Numerator / Denominator |
|---|---|---|
| Swing% | 46.9% | 2044 / 4362 pitches |
| Whiff% | 21.3% | 436 / 2044 swings |
| SwStr% | 10.0% | 436 / 4362 pitches |

**Whiff% and SwStr% are different metrics with different denominators.**
Whiff% = contact ability given a swing. SwStr% also embeds the pitcher's
ability to induce swings. Conflating them is a common error.

### Whiff% by count — lookup baseline for the Week 5 model

| Count | Swings | Whiff% |
|---|---|---|
| 0-2 | 140 | 25.0% |
| 1-0 | 176 | 25.0% |
| 0-1 | 283 | 24.7% |
| 0-0 | 329 | 24.3% |
| 1-2 | 220 | 20.9% |
| 1-1 | 249 | 20.1% |
| 3-0 | 5 | 20.0% |
| 2-2 | 246 | 19.1% |
| 3-1 | 48 | 18.8% |
| 2-1 | 126 | 16.7% |
| 3-2 | 173 | 15.6% |
| 2-0 | 49 | 12.2% |

Any model for P(Whiff | Swing) must beat this table, not just a
constant league rate. A groupby with no ML is a serious baseline.

Sample size warning: 3-0 has 5 swings. One swing moves it 20 points.
Single-day data cannot support count-level conclusions.

---

## Pitch types (2024-04-15)

### Code → name mapping (verified 1:1, no ambiguity)
FF 4-Seam Fastball · SI Sinker · SL Slider · CH Changeup · FC Cutter
CU Curveball · ST Sweeper · KC Knuckle Curve · FS Split-Finger
SV Slurve

### Usage and outcomes

| Type | Pitches | Usage | Swing% | Whiff% | Velo |
|---|---|---|---|---|---|
| FF | 1346 | 30.9% | 46.5% | 16.5% | 94.2 |
| SI | 698 | 16.0% | 45.0% | 10.8% | 92.9 |
| SL | 596 | 13.7% | 51.5% | 32.2% | 85.7 |
| CH | 466 | 10.7% | 50.6% | 31.4% | 86.2 |
| FC | 414 | 9.5% | 51.0% | 18.5% | 89.0 |
| CU | 314 | 7.2% | 40.4% | 22.8% | 80.0 |
| ST | 232 | 5.3% | 42.2% | 20.4% | 81.9 |
| KC | 136 | 3.1% | 44.1% | 36.7% | 82.2 |
| FS | 119 | 2.7% | 47.1% | 28.6% | 85.5 |
| SV | 25 | 0.6% | 36.0% | — | 79.1 |
| NaN | 16 | 0.4% | 0% | — | — |

Minimum threshold applied: 30 swings. Excluded: SV (9 swings),
NaN (0 swings). Excluded rows are reported, not silently dropped.

### Observations

**Velocity and whiff rate are inversely related here.** Sinker (92.9,
10.8%) and four-seam (94.2, 16.5%) sit at the bottom; slider (85.7,
32.2%) and changeup (86.2, 31.4%) at the top. Fastballs have
predictable trajectories and exist to establish counts, not to miss
bats.

**Consequence: whiff rate is the wrong sole metric for a sinker.**
Sinkers are designed to induce ground balls. Evaluating every pitch
type by the same criterion produces false conclusions. Week 4 pitcher
analysis needs pitch-type-specific success criteria.

**Swing% carries separate information.** Slider 51.5% vs curveball
40.4%: sliders look like strikes until late, curveballs are
identifiable out of the hand. SwStr% = Swing% × Whiff% — slider
reaches 16.6%, the highest of any pitch.

### Cautions

**Classification is inference, not measurement.** `pitch_type` is an
algorithmic label derived from trajectory, not the pitcher's stated
intent. Boundary cases (slider vs sweeper) will be misclassified.

**The value set is season-dependent.** ST (Sweeper) and SV (Slurve)
were introduced by MLB in 2023 and do not exist in earlier seasons;
historical data has also been reclassified. This will break pitch-type
aggregation across multi-season joins. Handle explicitly.

**KC at 36.7% is the highest whiff rate but rests on 60 swings.**
Clearing a threshold does not make estimates equally reliable. Five
swings moves it 8 points. Shrinkage / intervals needed (Week 6).

### Missing pitch_type — 16 rows: CONFIRMED as "no pitch thrown"

All 16 rows have description == `automatic_ball` (pitch clock
violation). Exact match, not a coincidence.

Physical evidence confirms it:
- plate_x / plate_z: 100% missing — the ball never crossed the plate
- release_speed / pfx_x / pfx_z: 93.75% missing (15 of 16)

The umpire awarded a ball; no pitch was physically delivered. This is
**"no pitch occurred"**, categorically different from "classification
failed".

**One of the 16 is different (game_pk 746974, 7th, AB 47, pitch 3):**
release_speed 83.0, pfx_x -1.54, pfx_z -0.28 — the ball DID leave the
hand, with a breaking-ball trajectory. But plate_x / plate_z are still
missing and pitch_type is still unclassified.

Two candidate explanations, neither confirmable from this data alone:
(a) the clock expired mid-delivery, so the pitch was voided and plate
crossing was never recorded; (b) partial tracking failure, where
Hawk-Eye caught release but lost the ball before the plate.

Treated the same as the other 15 (excluded — no plate location means no
location features, and no swing means it never enters the whiff model),
but flagged separately.

**Monitoring rule for multi-season work:** count rows with release data
present but plate data absent, as a separate category. A spike in that
rate by park or season is a tracking-system signal, not a rules
artifact.

### Three distinct kinds of missingness — do not conflate

| Kind | Example | Handling |
|---|---|---|
| Structural | launch_speed on a non-batted pitch | Normal. Never impute |
| No pitch | all physics on automatic_ball | Exclude the row entirely |
| Tracking failure | 1 batted ball with no launch_speed | Log it, monitor rate |

Tracking failure is a data-quality signal. If its rate spikes in a
particular park or season, that is itself a finding.

**Practical note:** these 16 rows are already excluded from whiff
modeling by the `is_swing` filter (0 swings). That is a happy accident
until you know why — now we do.

**Cross-season warning:** `automatic_ball` does not exist before 2023.
Missing `pitch_type` in earlier seasons will mean genuine
classification failure instead. The same missingness can have different
causes in different seasons.

---

## Multi-date observations (2024-04-15, 06-15, 08-15; 10,654 pitches)

### Game counts vary widely by date
| Date | Pitches | Games | Pitches/game |
|---|---|---|---|
| 2024-04-15 | 4,362 | 15 | 291 |
| 2024-06-15 | 4,145 | 14 | 296 |
| 2024-08-15 | 2,147 | 7 | 307 |

Aug 15 looks like a data failure at first glance (half the volume) but
is not: only 7 games were played. Per-game rates are normal across all
three dates. **When a total looks wrong, change the denominator before
concluding the pipeline is broken.**

### Pitch-type value set is not stable across dates
`PO` (pitchout) appeared once in the 3-date sample but was absent from
the single-day sample. Combined with ST/SV being 2023 additions, this
confirms that `pitch_type` values must be handled defensively when
pooling dates or seasons.

**Open decision (before Week 5):** policy for rare pitch types —
exclude, bucket as OTHER, or apply a minimum-pitch threshold.

### Selection bias in pitch-type aggregates
| Type | Pitches | Pitchers | Per pitcher | Whiff% |
|---|---|---|---|---|
| FF | 3541 | 199 | 17.8 | 17.5% |
| SL | 1407 | 140 | 10.1 | 31.5% |
| FS | 385 | 36 | 10.7 | 33.8% |
| KC | 217 | 21 | 10.3 | — |

Four-seam whiff rate reflects ~199 pitchers, i.e. close to the league.
Splitter whiff rate reflects only 36 — and those 36 are not a random
sample, they are pitchers who can throw a splitter at all.

Note that `per_pitcher` is similar across non-fastball types (~10), so
the bias does not come from a few pitchers throwing a lot. It comes
from **who throws the pitch at all**.

**Implication for Week 4:** compute whiff rate per pitcher, then average
across pitchers, and compare to the pitch-level pooled rate. The gap
between the two estimates the size of the selection effect.

---

## Full-season load: dtype corruption from empty snapshots (2026-09-01)

**Symptom.** After scaling from 3 dates to a full 2024 season (710,632
pitches, 186 files), `plate_x`, `plate_z`, `sz_top`, `sz_bot`, and
`zone` all loaded as object dtype. `groupby().std()` raised
`TypeError: float() argument must be ... not 'NAType'`, and
`describe()` reported unique/top/freq instead of mean/std — silently
treating pitch coordinates as categories.

**Cause.** 4 of 186 files had 0 rows (days with no games, including the
All-Star break on 2024-07-15). Pandas cannot infer a dtype from zero
rows, so those files stored every column as object. `pd.concat` then
promoted the entire 710k-row dataset to object.

**Four empty files corrupted 182 good ones.**

**Fix — two layers, both applied:**
1. `load_all_snapshots` skips zero-row frames before concatenating
   (removes this cause).
2. `coerce_numeric` forces known-numeric columns with
   `errors="coerce"` (defends against causes not yet seen, e.g.
   partially-null columns).

**Tests added:** `test_coordinate_columns_are_numeric` asserts dtypes
after loading, and `test_numeric_coercion_preserves_values` asserts
coercion did not silently null out data — `errors="coerce"` is a real
risk of quiet data loss.

**Lesson.** This was invisible at 3 dates and appeared immediately at
full season. Scale changes what fails. Integration tests must run
against the real data volume, not a toy sample.

---

## Strike zone definition (decided 2026-09-01)

### Definition used

    in_zone = |plate_x| <= 0.83
              AND plate_z >= sz_bot - 0.121
              AND plate_z <= sz_top + 0.121

Batter-specific vertical bounds from Statcast's `sz_top` / `sz_bot`,
with a ball radius added on every side — a pitch is a strike if any
part of the ball touches the zone.

`HALF_PLATE_FT = 0.83` — half the 17-inch plate plus a ball radius.
Confirmed empirically: Statcast zones 1-9 span exactly ±0.83.

`BALL_RADIUS_FT = 0.121` — 2.9-inch ball diameter / 2.

### The vertical ball radius mattered a great deal

Omitting it (bounds exactly sz_bot to sz_top) was an asymmetry: the
horizontal bound already had the ball radius folded into HALF_PLATE.

| Version | In-zone % | Disagreements with Statcast |
|---|---|---|
| Without vertical ball radius | 45.5% | 28,662 |
| With vertical ball radius | 49.7% | **932 (0.13%)** |

The 932 remaining disagreements are all boundary cases: median distance
from the nearest boundary is 0.005 ft, maximum 0.034 ft — about 14% of
a ball's diameter. Pure floating-point and constant rounding. All 932
have Statcast zone 11-14, meaning our definition is marginally more
generous at the edge.

**We have effectively reconstructed Statcast's `zone` computation.**

### Why not just use the `zone` column

It is a black box: the computation is undocumented and may change
between seasons. Our definition is explicit, versioned, and tested,
which is what reproducibility requires. The `zone` column is retained
as a cross-check.

### Batter-specific bounds matter

Across batters with >=20 pitches, mean `sz_top` ranges from 2.86 to
4.03 ft — a 1.17 ft (36 cm) spread, about five ball diameters. A fixed
rectangle would misclassify tall batters' high strikes as balls and
short batters' high balls as strikes, inflating the shorter batter's
Chase%.

Within-batter standard deviation is 0.06-0.09 ft. Not zero, so the zone
is not purely a function of height — stance and per-pitch measurement
vary.

### Umpires do not call the rulebook zone

Agreement between a geometric definition and actual ball/called-strike
calls, on 2024 taken pitches:

| Definition | Agreement |
|---|---|
| Statcast zone 1-9 | 92.3% |
| Fixed rectangle | 92.1% |
| Batter-specific + ball radius | 92.2% |

All three land near 92%. **No geometric definition exceeds it**, which
means the ~8% gap is not a definitional error — it is framing, count
effects, and umpire tendency.

That gap is a measurement target, not noise. Candidate research
question: how much does the effective called zone shift by count? This
connects to the unexplained count/whiff pattern logged on 2026-08-31.

### Scope

This definition is for **batter evaluation** (Chase%, Zone Swing%,
Zone Contact%), where the question is whether the hitter swung at a
pitch that was not a strike by rule. Framing analysis would need the
umpire's effective zone instead; pitcher command would need intended
location. Different questions, different zones.