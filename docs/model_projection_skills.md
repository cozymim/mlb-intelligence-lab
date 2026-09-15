# Projection System — Marcel plus Statcast skills

Marcel sees only past K% and BB%. Statcast measures the skills that
PRODUCE those outcomes. The question: does knowing a hitter's chase and
contact rates add anything to knowing his strikeout history?

## Answer: yes, but narrowly

Five-fold cross-validated MAE, 254 batters, projecting 2024 from
2021-2023 with skills from 2023 only:

| Metric | Marcel | Rescaled | **+ skills** | Gain |
|---|---|---|---|---|
| K% | 0.0271 | 0.0269 | **0.0265** | 2.2% |
| BB% | 0.0144 | 0.0142 | **0.0137** | 4.9% |

"Rescaled" is a linear transform of the Marcel projection alone, so the
skill contribution is measured net of that.

**BB% gains more than twice as much as K%.** Third confirmation of the
same pattern: Day 16 measured BB% as the noisier metric, Day 35 found
Marcel's edge over last-season-only three times larger for BB%, and
skills help more there too. **Noisier outcomes leave more room for skill
information.**

## Fewer features scored better

| Features | K% CV MAE | BB% CV MAE |
|---|---|---|
| 5 skills | 0.0269 (no gain) | 0.0139 |
| **2 skills** | **0.0265** | **0.0137** |

The five-feature version scored 0.0261 in TRAINING — apparently a 3.7%
gain — and 0.0269 under cross-validation, identical to Marcel rescaled.
**All of the apparent gain was overfitting.**

### Collinearity, below the usual threshold

| Pair | r |
|---|---|
| whiff_pct / zone_contact_pct | **-0.91** |
| swing_pct / chase_pct | **+0.88** |
| swing_pct / zone_swing_pct | **+0.85** |

`zone_contact_pct` is nearly the complement of in-zone whiff rate;
`swing_pct` is a weighted average of the two swing rates.

**Condition number was 14.2, below the textbook threshold of 30**, and
the redundancy still caused overfitting on 254 rows. A diagnostic
calibrated for large samples does not transfer to small ones.

Same lesson as Day 16 (Barrel% and HardHit% at r = 0.78 → keep one) and
Day 29 (12 rare-pitch parameters removed with no loss).

## The gain is concentrated where Marcel fails

Mean improvement over Marcel, by quartile of Marcel's own error:

| Marcel error | Mean improvement | n |
|---|---|---|
| 0.000-0.010 | **-0.0042** | 64 |
| 0.010-0.022 | -0.0003 | 63 |
| 0.022-0.039 | +0.0025 | 63 |
| 0.039-0.120 | **+0.0045** | 64 |

Monotonic. **Where Marcel is already accurate, adding skills makes the
projection worse.**

The overall 2.2% is a net of damaging good projections slightly and
fixing bad ones substantially. Which players fall in which quartile is
only knowable after the fact.

**For scouting this is a favourable trade.** A projection of 22% K%
against an actual 24% is tolerable; 22% against 34% changes an
acquisition decision. RMSE improves slightly more than MAE, consistent
with large errors shrinking.

## A coefficient that must not be interpreted

Fitted coefficients for K%:

| Feature | Coefficient |
|---|---|
| marcel_k | +0.8577 |
| zone_contact_pct | -0.2670 |
| **chase_pct** | **-0.0795** |

**The chase coefficient is negative, which is backwards.** Chasing more
should raise strikeout rate, not lower it.

The cause is that `marcel_k` is in the model. Past K% already reflects
chase behaviour, so the coefficient describes the residual after Marcel
has absorbed the main effect — and a residual can carry the opposite
sign.

**This model predicts; it does not explain.** Its coefficients are not
statements about baseball. The BB% coefficients happen to be
interpretable (-0.0977 for chase, correctly negative), but that is not a
property to rely on.

`zone_contact_pct` at -0.2670 is the larger contributor and is
correctly signed: making contact in the zone reduces strikeouts.

## Limitations

- **One projection season.** 2024 only.
- **254 batters.** Small enough that mild collinearity overfits.
- Skills come from one prior season, not a weighted window like Marcel's
  own inputs. A weighted skill history is untested.
- No age adjustment (inherited from the Marcel baseline).
- Playing time is not projected.
