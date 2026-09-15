"""Season projection: Marcel plus Statcast skill rates.

Marcel (src/models/marcel.py) is the baseline. This adds prior-season
plate discipline, on the theory that K% and BB% are OUTCOMES of skills
Marcel cannot see.

Result: it beats Marcel, but narrowly.

| Metric | Marcel | + skills | Gain |
|---|---|---|---|
| K%  | 0.0271 | **0.0265** | 2.2% |
| BB% | 0.0144 | **0.0137** | 4.9% |

Five-fold cross-validated MAE, 254 batters, projecting 2024 from
2021-2023 with skills measured in 2023 only.

**Only two skill features are used.** A five-feature version scored
0.0269 on K% — identical to Marcel rescaled, i.e. no gain at all —
while scoring better in training. Dropping three features IMPROVED
cross-validated performance.

The cause is collinearity: whiff_pct and zone_contact_pct correlate at
-0.91 (one is nearly the complement of the other), and swing_pct
correlates 0.85-0.88 with both chase and zone-swing rates because it is
a weighted average of them. The condition number was 14.2, below the
textbook threshold of 30, yet the redundancy still caused overfitting on
254 rows. **Condition number alone is not a sufficient check at small
sample sizes.**

Skills are taken from the season BEFORE the target only. Using
target-season skills would be leakage — they are not knowable when the
projection is made.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.models.marcel import project

# Two features, not five. See the module docstring.
SKILL_FEATURES = ["chase_pct", "zone_contact_pct"]


def skill_rates(df: pd.DataFrame, pitcher_ids: set | None = None) -> pd.DataFrame:
    """Plate discipline rates per (batter, season)."""
    from src.features.plate_discipline import add_discipline_flags

    work = df.copy()
    work["season"] = pd.to_datetime(work["game_date"]).dt.year

    f = add_discipline_flags(work)
    if pitcher_ids is not None:
        f = f[~f["batter"].isin(pitcher_ids)]

    oz = f[~f["in_zone"]]
    zone_swings = f[f["is_swing"] & f["in_zone"]]

    return pd.DataFrame({
        "chase_pct": oz.groupby(["batter", "season"])["is_swing"].mean(),
        "zone_contact_pct": 1 - zone_swings.groupby(["batter", "season"])["is_whiff"].mean(),
        "n_oz": oz.groupby(["batter", "season"]).size(),
        "n_zone_swings": zone_swings.groupby(["batter", "season"]).size(),
    }).reset_index()


def build_dataset(
    lines: pd.DataFrame,
    skills: pd.DataFrame,
    target_season: int,
    min_pa: int = 200,
    min_weighted_pa: int = 100,
) -> pd.DataFrame:
    """Marcel projections, prior-season skills, and realised outcomes."""
    marcel_k = project(lines, target_season, "k")
    marcel_bb = project(lines, target_season, "bb")

    prior = skills[skills["season"] == target_season - 1].set_index("batter")

    actual = lines[lines["season"] == target_season].set_index("batter")
    actual = actual.assign(
        k_pct=actual["k"] / actual["pa_count"],
        bb_pct=actual["bb"] / actual["pa_count"],
    )

    data = (
        marcel_k[["projection", "weighted_pa"]].rename(columns={"projection": "marcel_k"})
        .join(marcel_bb["projection"].rename("marcel_bb"))
        .join(prior[SKILL_FEATURES])
        .join(actual[["k_pct", "bb_pct", "pa_count"]])
    )

    mask = (data["pa_count"] >= min_pa) & (data["weighted_pa"] >= min_weighted_pa)
    for col in SKILL_FEATURES:
        mask &= data[col].notna()
    return data[mask]


def fit(data: pd.DataFrame, metric: str) -> LinearRegression:
    """metric is 'k' or 'bb'."""
    cols = [f"marcel_{metric}"] + SKILL_FEATURES
    return LinearRegression().fit(data[cols], data[f"{metric}_pct"])


def cross_validated_mae(data: pd.DataFrame, metric: str, n_splits: int = 5,
                        seed: int = 42) -> dict:
    """Honest comparison against Marcel. Training-set scores are
    optimistic: the five-feature version looked 3.7% better in training
    and gained nothing under cross-validation."""
    from sklearn.model_selection import KFold, cross_val_predict

    y = data[f"{metric}_pct"]
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)

    out = {"marcel": float((data[f"marcel_{metric}"] - y).abs().mean())}
    for name, cols in [
        ("marcel_rescaled", [f"marcel_{metric}"]),
        ("marcel_plus_skills", [f"marcel_{metric}"] + SKILL_FEATURES),
    ]:
        pred = cross_val_predict(LinearRegression(), data[cols], y, cv=kf)
        out[name] = float(np.abs(pred - y).mean())
    return out
