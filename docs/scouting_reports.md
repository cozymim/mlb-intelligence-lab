# Scouting Reports

Where metrics become recommendations. This is the point at which
unsupported claims most easily enter, so every statement is bound to a
number that cleared a sample threshold.

## Rules

1. **Every sentence traces to a measured gap.** "Vulnerable to sliders"
   is emitted only when slider whiff rate exceeds league by a stated
   margin, with the swing count attached.
2. **Silence below threshold.** 50 swings per pitch type, 40 per zone
   band. Below that, `INSUFFICIENT SAMPLE`.
3. **Everything is expressed against league.** "Chase 32%" means
   nothing; "3.8 points above league" does.
4. **Nothing notable is a valid answer.**

## Why rule 4 matters most

Most automated reports always say something. If a hitter has no
weakness, they name the least-bad thing as one.

**Juan Soto's 2024 report contains no pitch to attack** — only pitches
to avoid (curveball -15.8%, slider -9.2%). Nothing he faced exceeded the
+5 point notability threshold.

That is the correct output. Inventing a weakness there would misdirect a
real pitching plan.

## Worked examples (2024)

**Aaron Judge**
- Attack with CH: whiffs +16.5% above league (45.8% on 118 swings)
- Attack with CU: whiffs +14.7% above league (44.3% on 61 swings)
- Work below: whiffs +20.0% above league (153 swings)

Pitch type and location agree: he struggles with breaking balls, and
breaking balls finish below the zone. Fastballs are league-average
against him (FF +1.1%, SI +0.9%) — and his 27.0% barrel rate is the
league's highest, so mistakes in the zone are severely punished.

**Juan Soto**
- Avoid CU: whiffs -15.8% below league (13.7% on 51 swings)
- Avoid SL: whiffs -9.2% below league (23.1% on 134 swings)

**Shohei Ohtani**
- Attack with FF: whiffs +5.0% above league (24.0% on 384 swings)
- Avoid FS: whiffs -4.1% below league (28.6% on 63 swings)
- Work below: whiffs +18.5% above league (138 swings)

Similar location profile to Judge but a different entry point: the
fastball rather than breaking balls.

## League reference values (2024)

Whiff rate by vertical band, relative to each batter's own zone:

| Band | Whiff% |
|---|---|
| below | **53.2%** |
| low | 19.8% |
| middle | **12.3%** |
| high | 18.1% |
| above | 35.2% |

A U-curve, and an asymmetric one: below the zone (53.2%) generates far
more misses than above it (35.2%). Falling pitches beat rising ones.

This is why `plate_z` was the strongest single feature in the whiff
model (Day 25, permutation importance 0.145, 3.3x the next feature).

## Coverage

486 batters have at least one pitch type with 50+ swings.

| Qualifying pitch types | Batters |
|---|---|
| 1 | 84 |
| 2-3 | 79 |
| 4-5 | 116 |
| 6 | 103 |
| 7-8 | 104 |

Mean 4.5. The 84 batters with a single qualifying type get a thin
report, which is the honest outcome for a part-time player rather than a
failure of the system.

## Limitations

- One season. Approach changes between years are not captured.
- Thresholds are judgment calls informed by Day 16's stabilization work,
  not separately measured for these specific splits.
- Pitch type and location are treated independently. "Sliders below the
  zone" as a joint split would need larger samples than a season
  provides for most hitters.
- No count context. A hitter's vulnerability likely differs at 0-2 and
  3-1 (Day 21 measured large count effects on whiff rate), but splitting
  three ways exhausts the sample.
- Recommendations describe whiff vulnerability only, not damage. A
  pitch a hitter rarely misses but destroys when he connects would not
  appear here.
