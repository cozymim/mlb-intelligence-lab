# P(Whiff | Swing) — Error Analysis

Overall log loss says the model beats the baseline by 0.0165. It does
not say where, and "where" determines what to try next.

Evaluated on the second half of validation (41,746 swings), model
0.46449 vs baseline 0.48102.

## The model loses on three pitch types

| Pitch | n | Improvement | Height corr (train) |
|---|---|---|---|
| KC | 769 | **-0.0325** | -0.501 |
| FC | 3,661 | **-0.0250** | -0.084 |
| SI | 5,966 | -0.0077 | +0.006 |
| FF | 13,391 | +0.0197 | +0.207 |
| ST | 2,973 | +0.0213 | -0.326 |
| SL | 5,990 | +0.0246 | -0.377 |
| CH | 4,735 | +0.0349 | -0.317 |
| FS | 1,464 | +0.0440 | -0.413 |
| CU | 2,428 | **+0.0543** | -0.446 |

**FC and SI lose because they have no height effect to model.** Their
`plate_z_rel` correlations are -0.084 and +0.006 — essentially zero.
Forcing an interaction term onto a pitch with no interaction adds
variance and nothing else.

**KC breaks the pattern and is the more interesting case.** It has the
strongest height correlation of any pitch (-0.501) yet the worst
performance. The difference is sample size: 769 swings in evaluation,
3,052 in training — a fifth to a twentieth of the other types. The
effect is real but the coefficient cannot be estimated stably.

Correlation between improvement and |height correlation| is +0.385.
Excluding KC the relationship is clean; KC alone drags it down.

**Two conditions are required, not one:** a real height effect AND
enough swings to estimate it.

### Consequence for the rare-pitch threshold

Day 26 set the bucketing threshold at 500 training swings, chosen from
the gap between SV (847) and KN (312). That was a count-based judgment
with no performance evidence. KC at 3,052 clears it comfortably and
still hurts the model.

**Raising the threshold to ~3,000 is worth testing.** This is the kind
of decision that should be made on measured performance, not on where a
histogram happens to have a gap.

## Pitcher identity: real but small headroom

145 pitchers with 100+ swings in the evaluation set. Residual bias
(actual minus predicted whiff rate):

| | |
|---|---|
| mean | -0.0123 |
| std | **0.0431** |
| min | -0.1426 |
| max | +0.1044 |

Against a league whiff rate of 0.23, a per-pitcher bias of +/-0.10 is
substantial. The same pitch at the same location genuinely produces
different results depending on who threw it — the model has no player
information at all.

**But the headroom is small.** Applying each pitcher's own bias as an
offset improves log loss from 0.46449 to 0.46024, a gain of 0.00425.

**That figure is an optimistic ceiling, not an achievable result.** The
offsets were computed on the same rows they were applied to, which is
leakage. A legitimate as-of-date rolling feature (Day 17) estimates the
bias from prior data only and would capture some fraction of it.

For context, the model's entire margin over the baseline is 0.0165.
Pitcher features could add at most a quarter of that, realistically
much less.

**The mean bias of -0.0123 is worth noting**: the model over-predicts
whiffs slightly among frequently-seen pitchers. Possibly a sample
artifact of the 100-swing filter; not yet investigated.

## What this implies for the next model

1. **Re-test the rare-pitch threshold at ~3,000.** One line, directly
   motivated by the KC result.
2. **Gradient boosting.** Trees learn interactions and can modulate them
   by available sample, which is structurally the right answer to the KC
   problem — a fixed interaction term cannot.
3. **Pitcher rolling features.** Ceiling of 0.004 makes this the lowest
   priority despite being the most obvious idea.

Without this analysis the natural next step would have been "try
XGBoost". It still is, but now for a stated reason and with a specific
failure mode to check.
