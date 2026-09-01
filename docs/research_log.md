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