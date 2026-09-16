# Player Similarity

Two lines of scikit-learn produce a plausible-looking list of names.
That is exactly why this needed care.

## Euclidean, not cosine

Cosine measures direction and ignores magnitude. For Aaron Judge it
returned Michael Conforto (0.962), Christian Walker (0.959) and Matt
Chapman (0.957) — players whose barrel rates are 0.118, 0.133 and 0.128
against Judge's **0.270**.

Their profile SHAPE matches: good discipline, slightly below-average
contact, above-average power, elevated launch angle. Their magnitude
does not. **In baseball the magnitude is the point.**

Euclidean returned Ohtani (0.218), O'Neill (0.173), Soto (0.198),
Stanton (0.209) — actual comparables.

### The measurement agrees with the judgment

Predicting each player's wOBA from the mean of his five nearest
neighbours:

| Method | Correlation | MAE |
|---|---|---|
| **Euclidean** | **0.567** | **0.0239** |
| Cosine | 0.538 | 0.0246 |
| League mean | — | 0.0285 |

Both beat the league mean by a wide margin, confirming the similarity
captures something real. Euclidean wins, which is the smaller result but
the one that settles the method choice.

## Feature selection removed three power metrics

Nine candidates contained four pairs above |r| = 0.7:

| Pair | r |
|---|---|
| zone_contact / whiff | **-0.921** |
| hard_hit / avg_exit_velocity | **+0.928** |
| barrel / hard_hit | +0.810 |
| barrel / avg_exit_velocity | +0.769 |

**Three power metrics cluster at 0.77-0.93.** Keeping all of them would
have made three of four dimensions power, and every slugger's
comparables would have been other sluggers by construction.

Final four, one per independent dimension: `chase_pct`,
`zone_contact_pct`, `barrel_pct`, `avg_launch_angle`. Maximum remaining
correlation is -0.54 (contact against power), a genuine trade-off
established on Day 16 rather than redundancy.

## A single player is not evidence about feature importance

Dropping each feature and counting retained neighbours, for Judge:

| Dropped | Neighbours retained |
|---|---|
| avg_launch_angle | **8/8** |
| zone_contact_pct | 7/8 |
| chase_pct | 6/8 |
| **barrel_pct** | **1/8** |

Read alone, this says launch angle is useless and barrel rate is
everything. **Across 20 random batters it reverses:**

| Dropped | Mean retained |
|---|---|
| **avg_launch_angle** | **3.2/8** (most important) |
| chase_pct | 3.9/8 |
| zone_contact_pct | 3.9/8 |
| **barrel_pct** | **5.0/8** (least important) |

**Launch angle is the most important feature league-wide and the least
important for Judge.** It is the most independent dimension (max |r| =
0.33), so it does the most work separating ordinary players.

Removing it on Judge's evidence would have been the worst available
decision.

**This is the second time in this project that a pattern read off
extreme values failed against the full distribution** — Day 20 found the
same with release consistency and arsenal size. Treat it as a rule:
never infer structure from the tail.

## Structural limitation: extreme players

Judge's barrel z-score is **+4.8** against -1.9, -1.2 and +1.3 on the
other axes. Squared, barrel contributes 23 of roughly 30 units — **77%
of the distance**.

For him, "similar players" means "players with extreme barrel rates".
That is not a bug to fix; it is what distance-based similarity does when
one coordinate dominates.

**Mitigation:** `nearest()` returns the z-scores alongside each match,
and `dimension_dominance()` reports the share of squared distance each
feature contributes. A user can see which axis drove the result rather
than trusting the name list.

## Limitations

- One season. Skills change between years.
- No age, position, handedness, or role. A 22-year-old and a 35-year-old
  with identical current skills are rated identical.
- Hitters only. A pitcher equivalent would need a different feature set
  (arsenal shape rather than plate outcomes).
- Similarity has no ground truth. The wOBA-neighbour check is indirect
  evidence, not validation.

---

## Box-score similarity does NOT approximate Statcast similarity

KBO has no pitch tracking (Day 31), so none of the four Statcast
features exist there. The question: can box-score rates — K%, BB%, AVG,
ISO, all computable from a KBO box score — stand in?

**No.** Across 270 batters with 300+ PA in both spaces:

**Mean neighbour overlap: 1.12 of 8.**

| Overlap | Batters |
|---|---|
| 0 | **89 (33%)** |
| 1 | 97 (36%) |
| 2 | 54 |
| 3 | 25 |
| 4+ | 5 (1.9%) |

**69% of players get zero or one shared neighbour.** A third receive
eight entirely different comparables for the same player and season.

### Judge illustrates why

| Space | Neighbours |
|---|---|
| Statcast | Ohtani, O'Neill, Soto, Stanton, Schwarber, Toglia, Ozuna, Rooker |
| Box score | **Tucker**, Ohtani, Soto, Ozuna, Marte, Pederson, Henderson, Rooker |

Kyle Tucker ranks first in box-score space and is distant in Statcast
space. His ISO is 0.296 against Judge's, but his barrel rate is 0.129 —
less than half of Judge's 0.270.

**ISO is an outcome; barrel rate is the process.** Tucker reaches
similar power production by a different route, and only the
process-level features can tell them apart.

AVG is the worst offender: it carries heavy BABIP noise (Day 25 found it
near-unpredictable), and noise in a feature scatters neighbours.

### Consequences for the KBO work (Week 10)

1. **KBO similarity is a separate system**, not a version of this one.
   It must not be presented alongside Statcast-based comparables.
2. **"MLB hitters similar to a KBO player" is low-confidence.** Stated
   with that caveat or not stated at all.
3. **Similarity is context, not method.** The hierarchical translation
   model remains the Week 10 approach; similarity supports intuition.
4. **The comparison is itself a result.** "Box-score data does not
   substitute for tracking data" is now quantified at 1.12/8 rather than
   asserted.
