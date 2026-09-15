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

---

## Damage assessment (added 2026-09-15)

The original report had a dangerous omission: it measured only whether a
hitter MISSES a pitch, never what happens when he connects.

**Aaron Judge's four-seam whiffs at +1.1% above league — apparently
unremarkable — and barrels at +20.1%.** 34 barrels on 113 batted balls,
against a league rate of 10.0%. A whiff-only report marks the most
expensive pitch in the matchup as safe.

### The two dimensions are largely independent

Across 1,661 (batter, pitch type) pairs with adequate samples, whiff gap
and barrel gap correlate at **0.318**. Roughly 90% of the variance is
separate information.

**109 pairs (6.6%) are "low whiff, high damage"** — the most costly
quadrant available. Top of that list: Soto's four-seam (+19.6% barrels,
-1.4% whiffs), Seager's slider (+16.0%), Ohtani's changeup (+14.6%).

### Four verdicts

| Verdict | Condition |
|---|---|
| ATTACK | whiffs above league, damage at or below |
| chase pitch ONLY | whiffs above league BUT punishes contact |
| AVOID | damage above league without the whiffs |
| DAMAGE NOT MEASURED | below 25 batted balls |

### The fourth verdict is the important one

"Not measured" is not "safe", and conflating them produced a genuinely
harmful recommendation.

**Judge's curveball had the largest whiff gap of any pitch he faced
(+14.7%) and was the only ATTACK recommendation** in an intermediate
version. On 17 batted balls it barrels at **23.5%** — more than three
times league — but 17 is below the threshold, so the risk was simply
absent from the report.

Silence about an unmeasured risk reads as an absence of risk.

**Sample thresholds cut both ways.** Day 16 established them as
protection against noise. They are equally a reason a warning may be
missing, and that must be stated rather than left implicit.

### How the recommendations changed

| Player | Whiff-only version | With damage |
|---|---|---|
| Judge | "Attack with CH" | **CH: chase pitch ONLY** (+21.5% barrels) |
| Soto | "No significant deviations" | **Four pitches AVOID** |
| Ohtani | "Attack with FF" | **FF: chase pitch ONLY** (+16.2% barrels) |

**Soto's case is the sharpest.** "No weakness found" invites the reading
"anything works". In fact every pitch he sees in adequate volume is one
to keep out of the zone.

**None of these three hitters has a single ATTACK pitch.** For elite
hitters there is no safe offering — only chase pitches and pitches to
avoid. That is a realistic output, not a failure of the method.

### Sinkers against elite hitters

All three show sinker as AVOID: Judge +20.9%, Soto +18.9%, Ohtani +6.0%.

Day 22 found the sinker to be a strong pitch by league xwOBA (0.368,
better than the four-seam's 0.392). It is thrown in the zone more than
any other pitch and induces weak contact.

**Against ordinary hitters that produces ground balls. Against these
three it produces home runs.** League averages do not transfer to
individual matchups, which is the entire reason scouting reports exist.
