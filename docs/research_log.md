# Research Log

Format: DATE / QUESTION / HYPOTHESIS / DATA / METHOD / RESULT /
INTERPRETATION / LIMITATIONS / NEXT STEP

Failures and dead ends are recorded here too — they are the most
valuable entries for interviews.

---

## 2026-08-31 — Project differentiation strategy

**Context**
Public Statcast analysis is crowded. MLB clubs hold proprietary data
(full biomechanics, minor league tracking, medical) that cannot be
matched. Technical superiority on the same public data is not a viable
differentiation path.

**Decision**
Differentiate on (a) questions others cannot easily ask, and (b) rigor
that public portfolios usually skip.

Two flagship components chosen:

**A. Performance projection system**
Predict next-season outcomes (K%, BB%, batted-ball quality, xwOBA, AVG).
Differentiator: implement a Marcel-style projection as a third baseline
alongside the constant and lookup baselines required by CLAUDE.md.
Beating a real published projection system is a meaningful bar; most
public portfolios never attempt it.

**B. KBO ↔ MLB translation research**
Rationale: owner reads Korean and understands KBO context. Very few
public analysts can do this work. MLB clubs actively scout KBO/NPB.

**Rejected framing (important)**
"Predict P(success in MLB | KBO stats)" as a direct classification task.
Reason: only ~20-30 KBO→MLB direct transitions exist. Fitting a binary
classifier on n≈30 is overfitting, and R&D interviewers will recognize
it immediately. Recording this rejection because the reasoning matters
more than the conclusion.

**Adopted framing**
Estimate league translation factors as a continuous quantity with
explicit uncertainty. Success probability is then *derived* from the
posterior distribution, not learned directly.

Method direction: hierarchical Bayesian model.
  league-level factor μ
    → player-level factor θᵢ ~ Normal(μ, τ)
      → observed performance change
Small-sample players shrink toward the league mean automatically.
Output is a posterior distribution, not a point estimate — the form a
front office can actually act on.

**Define "success" before modeling**
Candidate: ≥2 MLB seasons at ≥100 wRC+ (hitters). Must be fixed and
documented before any modeling, not chosen after seeing results.

---

## Open questions — to resolve before Week 6

### Data availability (blocking)
- [ ] What KBO data is publicly available? (KBO official records,
      Statiz, other sources)
- [ ] Terms of service for each source — scraping permitted?
- [ ] Is KBO pitch tracking data public at all? Assume NO until proven.
      If unavailable, the analysis is limited to season-level rates
      (wRC+, K%, BB%, ISO) and pitch-shape work is impossible.
- [ ] Player ID crosswalk: how to link a KBO player to their MLB record?
- [ ] NPB as a comparison case — same questions.

### Methodological
- [ ] KBO run environment changed across seasons (2019 ball
      deadening is the well-known case; verify specifics against
      sources before relying on it). This is the same era-discontinuity
      problem already handled for MLB — reuse that framework.
- [ ] Park factors in KBO — available? Needed for fair comparison.
- [ ] Selection bias: only players good enough to be posted make the
      transition. The sample is not random. Must be addressed explicitly,
      not ignored.
- [ ] Reverse direction (MLB/AAA → KBO foreign players) adds sample.
      Is it methodologically sound to pool both directions?

### Projection system
- [ ] Marcel algorithm specifics — verify against original source
      before implementing. Do not reconstruct from memory.
- [ ] Which target metrics stabilize fast enough to be worth predicting?
      Expect AVG to be near-unpredictable due to BABIP noise. If so,
      report that finding rather than hiding it.
- [ ] Leakage audit is especially critical here: age must be as-of
      prediction time, playing time (PA) is an outcome and cannot be a
      feature, team/park only if known at prediction time.

**Next step:** none of this is actionable yet. Continue the data
foundation. Revisit at the Week 6 scope checkpoint.

## 2026-08-31 — Unexpected count effect on whiff rate

**Prediction (mine, before looking):** whiff rate would be highest in
two-strike counts, since hitters defend and pitchers throw putaway
pitches.

**Result: wrong.** Within two-strike counts, whiff rate DECREASES as
balls accumulate: 0-2 25.0% → 1-2 20.9% → 2-2 19.1% → 3-2 15.6%.
3-2 is near the bottom of all twelve counts.

**Hypotheses (untested):**
- Pitcher freedom: at 0-2 a pitcher can chase out of the zone at no
  cost. At 3-2 he must throw a strike or walk the batter, and in-zone
  pitches generate less swing-and-miss.
- Batter selectivity: at 3-2 the hitter can take anything off the
  plate. At 0-2 he must protect and swings at worse pitches.

**Testable version (Week 4):** is the in-zone rate of pitches
significantly higher at 3-2 than at 0-2? Use plate_x / plate_z.

**Why this is recorded:** the prediction was wrong and the data won.
This is exactly the kind of entry that belongs in a research log.
---

## 2026-09-01 — Release point consistency does NOT predict whiff rate

**Question.** Does inconsistent release point across pitch types cost a
pitcher swing-and-miss? The intuition: if a hitter can read the pitch
type from the release, he stops being fooled.

**Method.** For 473 pitchers with 500+ pitches, normalise release_pos_x
for handedness, then decompose release scatter into:
  between = spread of pitch-type mean release points
  within  = typical scatter inside a single pitch type
  ratio   = between / within  (signal-to-noise)

Correlate each against whiff rate (200+ swings).

**Result — no relationship whatsoever.**

| Measure | r with whiff rate |
|---|---|
| ratio | 0.018 |
| between | 0.014 |
| within | 0.007 |

Three different formulations, all essentially zero. This was not the
expected direction; a weak negative correlation was anticipated.

**Candidate explanations (untested):**
- Reaction time. A 90 mph pitch arrives in ~0.4 s. Detecting a 0.15 ft
  (4.5 cm) release difference and acting on it may be below human
  perceptual limits in that window.
- Offsetting effects. Pitchers whose release separates may also separate
  more in velocity and movement, cancelling the tell.
- Intent. High-ratio pitchers include Tyler Anderson and Drew Smyly, who
  are known for varying arm slots deliberately. Variation is a strategy,
  not a flaw.
- **Signal below noise.** Mean `within` (0.223) exceeds mean `between`
  (0.146); median ratio is 0.612. For most pitchers the between-pitch
  difference is smaller than the ordinary scatter of a single pitch
  type. There may be nothing for a hitter to read.

The last explanation is the most concrete and is directly measurable in
the numbers above.

**Confound identified.** The lowest-ratio pitchers are almost all
relievers (Helsley, Iglesias, Yates, Robertson, Brebbia, Green) and the
highest are mostly starters (Musgrove, Imanaga, Stripling). Relievers
carry 2-3 pitch types, so `between` has fewer centres to spread. The
ratio may be measuring arsenal size rather than release consistency.
Tested by correlating ratio against arsenal depth — see follow-up.

**Limitations.** Correlation only; no causal claim. Release position is
measured, not pitching mechanics — public tracking data does not support
biomechanical conclusions. Single season.

**Status.** Recorded as a null result. Reported rather than discarded:
the absence of an effect that the sport widely assumes is itself
informative, and hiding it would violate the project's modelling policy.

**Follow-up: the arsenal-size confound was NOT real.**

| Measure | r with arsenal size |
|---|---|
| ratio | 0.059 |
| between | 0.077 |

Mean ratio by arsenal size is flat: 0.62 (2 types), 0.69 (3), 0.69 (4),
0.71 (5), 0.73 (6). No meaningful gradient.

The reliever/starter split visible in the top-10 lists did not survive
contact with the full distribution. **Reading a pattern off extreme
values is unreliable** — in 473 pitchers, ten will be extreme for any
measure, and a plausible story can be told about any of them.

Ruling out this confound strengthens the null result rather than
weakening it.

---

## 2026-09-01 — Why whiff rate falls as balls accumulate: SOLVED

**Background.** On 2026-08-31 (single-day sample) whiff rate was found to
decrease within two-strike counts: 0-2 25.0%, 1-2 20.9%, 2-2 19.1%,
3-2 15.6%. This contradicted the prediction that two-strike counts would
uniformly raise whiff rates. A hypothesis was logged: at 3-2 the pitcher
must throw a strike and the hitter can take anything off the plate, so
both sides push toward the zone.

**Now testable** with 710,632 pitches and a validated zone definition.

**Confirmed on the full season.** Within two-strike counts:

| Count | Zone% | Whiff% |
|---|---|---|
| 0-2 | 32.5% | 25.7% |
| 1-2 | 38.1% | 24.3% |
| 2-2 | 46.8% | 21.1% |
| 3-2 | **58.1%** | 17.2% |

Zone rate rises 25.6 points and whiff rate falls monotonically against
it. At 0-2 a pitcher throws two-thirds of pitches out of the zone — a
ball costs nothing. At 3-2 he must put more than half in the zone.

**The mechanism is composition, not a change in pitch quality.**
Splitting swings by location largely dissolves the count effect:

| Count | Whiff% out of zone | Whiff% in zone |
|---|---|---|
| 0-2 | 40.4% | 14.1% |
| 1-2 | 38.9% | 13.9% |
| 2-2 | 36.6% | 12.8% |
| 3-2 | 31.8% | 12.0% |

In-zone whiff rate moves only 2.1 points (14.1 to 12.0) while the
overall rate moves 8.5. Whiff rate differs roughly 3x between the two
regions (40% vs 14%), so shifting the mix between them dominates the
aggregate.

**This is a Simpson's-paradox-shaped result:** the effect inside each
subgroup is small, but a change in subgroup composition moves the
headline number substantially. A caution for every aggregate metric in
this project.

**A second, smaller effect is also present.** Mean distance from the
centre of the zone (in-zone pitches only) falls with ball count:

| | 0 strikes | 1 | 2 |
|---|---|---|---|
| 0 balls | 0.643 | 0.666 | 0.693 |
| 3 balls | 0.623 | 0.627 | 0.632 |

At 3-2 pitchers not only throw in the zone more often, they throw closer
to the middle of it. That explains part of the residual 8.6-point drop
in out-of-zone whiff rate as well: pitchers are attacking rather than
expanding.

**Aside — 3-0 is a distinct regime.** Swing rate 9.2% despite a 59.5%
zone rate: one more ball is a walk, so hitters take even strikes. Whiff
rate 12.7% rests on roughly 670 swings, far fewer than any other count.

**Limitations.** Single season. Descriptive, not causal — this describes
what pitchers and hitters do, not why. The centre-distance measure uses
the midpoint of each batter's own zone, so it is comparable across
batter heights, but it does not distinguish horizontal from vertical
positioning.

**Status.** Original hypothesis confirmed and mechanism identified. This
is a candidate section for the Week 12 research writeup.
