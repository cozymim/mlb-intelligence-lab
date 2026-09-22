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

---

## 2026-09-01 — Does fastball velocity separation improve offspeed whiff rate?

**Question.** One of the original research candidates in CLAUDE.md.

**Data.** 2024 season, 1,216 (pitcher, pitch type) pairs with 50+ swings.
For each secondary pitch: velo_gap and move_gap from the pitcher's
primary fastball, plus that fastball's velocity as a control.

### The naive answer is badly wrong

Pooled across pitch types: **r = 0.552**.

Within pitch type: **r = 0.07 to 0.50**, varying by pitch.

More than half the pooled correlation is pitch-type composition.
Curveballs separate more AND whiff more, so pooling makes separation
look causal when it is partly just "which pitch is this". Same structure
as the count/location composition effect from Day 21.

### Fastball velocity is a genuine confound

velo_gap correlates with fastball velocity at r = 0.19 to 0.60,
strongest for fastball-family pitches (SI 0.598, FF 0.544, ST 0.467).
Harder throwers separate more by construction.

### Result after controlling for fastball velocity

| Pitch | n | raw r | controlled r |
|---|---|---|---|
| FS splitter | 58 | +0.498 | **+0.487** |
| FC cutter | 121 | +0.423 | **+0.361** |
| SL slider | 299 | +0.306 | +0.242 |
| CH changeup | 216 | +0.279 | +0.215 |
| ST sweeper | 151 | +0.128 | +0.006 |
| CU curveball | 117 | +0.070 | +0.011 |
| FF four-seam | 78 | +0.074 | -0.042 |
| SI sinker | 134 | -0.058 | **-0.205** |

**The premise is half true.** Velocity separation helps splitters,
cutters, sliders and changeups. It does nothing for sweepers,
curveballs or four-seams, and is mildly negative for sinkers.

### Hypothesis for the split (untested)

Pitches that benefit (FS, CH, SL, FC) look like the fastball out of the
hand and deceive with speed. Pitches that do not (CU, ST) are visually
distinct immediately — Day 19 measured curveball pfx_z at -0.84 and
sweeper pfx_x at +1.16, both extreme. If the hitter identifies the pitch
at release, adding velocity separation has nothing left to hide.

**Testable prediction:** the velo_gap effect should shrink as a pitch
type's typical move_gap from the fastball grows. Measurable with Day 19
data.

### The sinker result is a measurement artifact, not an effect

Sinkers are fastballs; velo_gap from the primary fastball is normally
1-2 mph. A large gap means the sinker is SLOW, and a slow sinker is a
worse sinker. In this pitch type velo_gap measures stuff decay rather
than separation. **The same variable means different things for
different pitch types** — a caution for any model that treats it as one
feature.

### Movement separation matters less than velocity

move_gap correlations are weak everywhere except FC (0.339) and FS
(0.310); elsewhere 0.03-0.12. Day 19 established that velo_gap and
move_gap are independent dimensions; this establishes that they are not
equally useful.

### Limitations

Correlational, single season, no causal claim. Partial correlation
removes only the linear effect of fastball velocity. Pitch-type sample
sizes vary widely (SL 299 vs FS 58), so the splitter estimate is the
least stable of the strong results. Usage rate and pitcher role are not
controlled.

**Status.** Original research question answered with a qualified yes.
Candidate section for the Week 12 writeup.

---

## 2026-09-03 — KBO data availability: investigation results

Moved forward from Week 7 because the answer reshapes the Week 10
flagship.

### Pitch tracking data is NOT publicly available — settled

Trackman is installed in nearly all Korean professional parks, so the
data exists. It is club property and is not published.

The decisive evidence: Ben Howell built the KBO Wizard, an R Shiny app
for KBO pitch analysis, by **manually charting 28,000+ pitches** because
no public pitch-by-pitch data existed. He does not release the charted
data itself.

If an analyst had to hand-chart, there is nothing to find.

**Consequence.** No plate_x/plate_z, no pfx, no release_speed, no
spin. Every pitch-level technique built in Weeks 3-5 is inapplicable to
KBO. The research is restricted to season-level rates.

**This confirms the assumption already logged on 2026-08-31**, so the
planned approach (wRC+, K%, BB%, ISO with hierarchical shrinkage) does
not change. What is lost is the optional extension into pitch shape.

### KBO adopted ABS in 2024 — a discontinuity we did not anticipate

The KBO became the first professional league to implement an Automated
Ball-Strike system, in the 2024 season.

**This matters directly.** Day 13 measured human umpires agreeing with
a geometric zone only ~92% of the time; that 8% is framing, count
effects and umpire tendency. KBO from 2024 has removed it.

A changed strike zone changes K% and BB% — precisely the two metrics the
projection system will target.

**Rule: KBO data before and after 2024 cannot be pooled without an
explicit era control.** Structurally identical to the MLB 2020 Hawk-Eye
transition and 2023 rule changes already handled in the data dictionary.

Whether ABS moved K%/BB% materially, and in which direction, is an open
question — and arguably a research question in its own right.

### Available sources

**Baseball-Reference KBO register.** Season-level batting and pitching,
player pages with gamelogs and splits. **Key advantage: our cached
`data/external/player_ids.csv` already carries `key_bbref`**, and
Baseball-Reference hosts both KBO and MLB records, so the crosswalk for
transitioning players is much simpler than expected.

**MyKBO Stats (mykbostats.com).** Unofficial, English, updated daily.

**`kbodata` on PyPI.** Scrapes koreabaseball.com. Requires
chromedriver/Selenium — slow, heavy, and not an official API. Several
similar GitHub projects exist, all Selenium-based.

**There is no official KBO API.** Everything is scraping.

### Open items before Week 10

- [ ] Terms of service and robots.txt for each source. Baseball-Reference
      is known to restrict automated access; this must be checked, not
      assumed. CLAUDE.md forbids scraping without checking terms.
- [ ] Count the actual KBO to MLB transition sample. The ~20-30 estimate
      is from memory and needs verifying.
- [ ] Decide the ABS era boundary treatment: restrict to pre-2024, add
      an era term, or treat 2024+ separately.
- [ ] Check whether NPB transitions can be pooled to increase sample, and
      whether that is methodologically defensible given different league
      environments.

### Status

**The Week 10 research survives**, with its scope confirmed rather than
reduced: season-level translation factors with hierarchical shrinkage,
as originally planned. The pitch-shape extension is off the table.

ABS is a new complication and possibly a new opportunity.

### Terms of service — Baseball-Reference is RULED OUT

Sports Reference's data use policy states plainly that you should not
create websites or tools based on data scraped from their sites without
permission. Their Terms of Use separately prohibit using automated means
(scripts, bots, scrapers, data miners) without express written
permission.

They also note that for some datasets their own licenses preclude any
redistribution at all, since most of their data is purchased from third
parties.

**"Do not create tools based on scraped data" describes this project
exactly.** This is an explicit prohibition, not a grey area.
Baseball-Reference is excluded as a source.

### This turns out not to matter

The KBO-to-MLB transition sample is roughly 20-30 players. Season-level
records for 30 players across a few seasons is **100-200 rows** — a
trivial dataset next to the 710,632 pitches already handled.

**Plan: compile the KBO side by hand from public records**, one row at a
time, with the source and verification date recorded for each. Manual
transcription of publicly displayed statistics is not automated
scraping.

This is arguably better than scraping: every value is eyeballed, so
parsing errors cannot slip through silently.

**The MLB side requires no external source at all.** K% and BB% for
Kim Ha-seong, Lee Jung-hoo and the rest can be computed directly from
the Statcast data already held, using the plate-appearance logic built
on Day 3.

| Side | Source | Method |
|---|---|---|
| MLB | our own Statcast snapshots | computed |
| KBO | public records | manual entry |

Target artifact: `data/external/kbo_mlb_transitions.csv`, with a
`source` and `verified_on` column per row.

### Remaining open items

- [ ] Terms for MyKBO Stats and koreabaseball.com, if either is used
      beyond manual reading
- [ ] Enumerate the actual transition list and confirm the sample size
- [ ] ABS era boundary treatment (2024+)
- [ ] Whether to pool NPB transitions for sample size

The Week 10 research is unblocked. Data volume was never the
constraint; the constraint is sample size, and that was known from the
start — it is why hierarchical shrinkage is the method.

### 2026-09-03 — Research question corrected: this is a SCOUTING tool

The question was initially framed too narrowly as "estimate KBO-to-MLB
translation factors" — descriptive, and only informative about players
who already made the move.

**The actual question is prospective:** given a KBO player who has never
played in MLB, what would he do if he did?

That is a two-stage structure:

1. **Learn** translation factors from the ~15-20 hitters who played in
   both leagues.
2. **Apply** them to current KBO players to produce projected MLB
   performance with credible intervals.

**Stage 2 was missing from the original plan**, and it changes the data
requirements: current KBO players are the prediction targets, so their
records are needed too.

### Revised data plan

| Dataset | Rows | Purpose |
|---|---|---|
| Historical transitions | 50-100 | learn translation factors |
| Current KBO candidates | 100-150 | prediction targets |
| KBO league season averages | 10-15 | reference point, shrinkage |

Prediction targets are scoped to **players plausibly of MLB interest** —
posting-eligible, young with strong production, or actually discussed —
roughly 30-50 per season over 2023-2025. Not all ~1,800 KBO players;
most are not acquisition candidates and would only add transcription
hours.

Total around 250 manually entered rows. Feasible in a day.

### Why this is the better project

Descriptive output ("K% rises by a factor of about 1.4 in transition")
is something informed observers already know.

Prospective output ("projected MLB wRC+ 105, 80% credible interval
[82, 128]") supports an acquisition decision. This is the "Potential
Player Acquisition Analysis" listed in the original project spec.

**Uncertainty becomes the point, not a caveat.** Factors learned from
15 players applied to a new player must produce wide intervals. Showing
that honestly is the contribution — a stated "73% chance of success"
from this sample size would be false precision.

The hierarchical Bayesian approach fits this structure directly:
league-level factor learned from transitions, applied per player, with
the posterior carrying the uncertainty through to the projection.

### 2026-09-08 — The projection system is the KBO research's engine

Week 7 built a season projection system for MLB. It is also the
machinery the Week 10 KBO work needs, which was not obvious when the
scope was set.

**Shared:**
- Season-line aggregation from plate appearances
- The pitcher-exclusion filter (KBO had no DH until 2022 either, so the
  same contamination applies)
- Regression toward a league mean with an explicit weight
- Evaluation protocol: MAE, RMSE, correlation against stated baselines
- The discipline that a projection must beat a named baseline

**Not shared:**
- KBO has no pitch tracking, so `chase_pct` and `zone_contact_pct` are
  unavailable. The KBO side runs on season rates alone — effectively
  Marcel without the skill correction.
- The KBO question is cross-league, not next-season. The regression
  target is a translated league mean, not the same league's mean.

**A finding that transfers directly.** Day 36 showed that the gain from
skill features concentrates where the baseline fails badly, and that
adding features HURTS where the baseline is already accurate. With ~15
transition players, the KBO model will be in the "baseline fails badly"
regime everywhere. That argues for keeping it simple and letting the
credible intervals carry the uncertainty, rather than adding predictors.

**And a warning.** Day 36's five-feature model overfit 254 rows at a
condition number of 14.2. The KBO model will have roughly 15 rows.
Anything beyond one or two parameters is not estimable, which is the
argument for hierarchical shrinkage rather than more structure.

### 2026-09-15 — Pitchers added back; sample count corrected

**The Day 31 decision to exclude pitchers rested on a wrong number.**
It assumed ~30 transitions split 15/15. Verified count of KBO-to-MLB
POSITION PLAYERS over 11 years:

Posted (all Kiwoom Heroes): Kang Jung-ho (2015), Park Byung-ho (2016),
Ha-seong Kim (2021), Jung-hoo Lee (2024), Hye-seong Kim (2025).
Via free agency: Kim Hyun-soo (2016), Hwang Jae-gyun (2017).

**Seven.** Not enough for any model, hierarchical or otherwise.

### The reverse direction is the real sample

KBO foreign players almost all carry MLB or Triple-A records. The 2020
KBO home run leaderboard alone featured Mel Rojas Jr., Preston Tucker,
Jamie Romak and Aaron Altherr, all former MLB players.

**KBO roster rules allow two foreign pitchers and one foreign hitter per
club**, so foreign pitchers outnumber foreign hitters roughly 2:1.
Across ten seasons: perhaps 40-60 hitters and 80-150 pitchers with
MLB history.

Excluding pitchers therefore does not halve the sample — it removes the
larger half.

### Selection bias runs in opposite directions

Forward: only the best KBO players are posted.
Reverse: only MLB players who could not hold a job sign in KBO.

Both are selected, oppositely. Combining them may partially cancel the
bias or may not. **Addressing this explicitly is a methodological
contribution rather than a caveat.**

### The role objection is solved by metric choice

The original worry was that Kim Kwang-hyun started in KBO and moved
between starting and relieving in MLB, confounding role change with
translation.

**K% and BB% are per-batter-faced rates**, so they carry the same
meaning for a starter and a reliever. Innings-based metrics (ERA, WHIP)
do not. The projection system already narrowed to K% and BB% on Day 31
precisely because they apply to both hitters and pitchers.

Starter/reliever can additionally be controlled via games started over
games appeared.

### Revised plan

| Group | Forward | Reverse |
|---|---|---|
| Hitters | 7 | 40-60 |
| Pitchers | Ryu, Kim Kwang-hyun, Oh Seung-hwan, Yang Hyeon-jong, others | 80-150 |

**Separate models for hitters and pitchers** — translation factors may
differ — but shared methodology and code.

Pitcher rows record batters faced, not innings: K% = SO / BF.

---

## 2026-09-21 — First KBO/MLB translation measurements

77 of 81 KBO foreign hitters have MLB records in the 2014-2024 holdings
(261 player-seasons). The four missing finished in MLB before 2014.

Rates are computed from career totals per player, with BB% excluding
intentional walks **on both sides** — KBO box scores fold IBB into BB,
so an unmatched definition would corrupt the ratio.

### Translation factors, 40 players with 200+ KBO PA and 100+ MLB PA

| Metric | MLB | KBO | Ratio | Correlation across players |
|---|---|---|---|---|
| K% | 0.242 | 0.166 | **0.69** | **0.77** |
| BB% | 0.069 | 0.085 | 1.24 | **0.32** |
| ISO | 0.157 | 0.202 | 1.29 | **0.28** |

PA-weighted means, so a 100-PA stint does not count as much as 1,000.

**Only K% translates predictably.** A correlation of 0.77 means the
ordering of players survives the league change: a hitter who struck out
more in MLB strikes out more in KBO. That is what makes a projection
possible.

**BB% and ISO do not.** Both league means shift (1.24x, 1.29x) but
individual differences barely carry over at r = 0.28-0.32. The league
gets easier for everyone; who benefits most is not predictable from the
KBO line.

This matches Day 16, which measured K% as the fastest-stabilising rate.
Noisy metrics do not transmit across leagues, because most of what they
measure is noise.

**Scouting consequence:** projecting a KBO home run leader's MLB power
from his ISO is weakly supported. Projecting his strikeout rate is far
better supported.

### Players who returned to MLB after KBO — the "refined in Korea"
### narrative is NOT supported

Eleven players went MLB to KBO to MLB. K% before, during, and after:

| Player | MLB before | KBO | MLB after | PA after |
|---|---|---|---|---|
| Mike Tauchman | 0.270 | 0.160 | **0.207** | 753 |
| Nick Martini | 0.216 | 0.149 | 0.218 | 243 |
| Christian Bethancourt | 0.241 | 0.228 | 0.254 | 815 |
| Darin Ruf | 0.250 | 0.171 | **0.270** | 854 |
| Jim Adduci | 0.237 | 0.204 | 0.265 | 283 |
| Niko Goodrum | 0.313 | 0.229 | 0.294 | 34 |
| Dixon Machado | 0.180 | 0.114 | 0.294 | 17 |

**Nine of eleven returned with a K% at or worse than before.** Only
Tauchman clearly improved, and his is the best-powered comparison in the
group (667 PA before, 753 after).

**But a confound is unresolved: age.** A KBO stint costs two to four
years, and K% rises with age — the reason Marcel's age adjustment was
deliberately omitted on Day 35 (its coefficients were fitted for
production, which declines, while strikeouts increase).

**KBO effect and ageing effect are not separable without birth dates,
which the cached Chadwick columns do not include.** Recorded as an open
question, not a finding.

### Sample warnings

Post-KBO MLB samples include 17, 15 and 34 PA. Andy Burns' 0.067 is one
strikeout in fifteen. **Any analysis must impose a minimum of ~100 PA**,
and even then several of these comparisons rest on a few hundred.

The full 77-player set has median 354 KBO PA and 322 MLB PA, with
minimums of 11 and 9. Shrinkage is not optional here.
