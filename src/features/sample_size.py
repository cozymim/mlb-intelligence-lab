"""Measured stabilization thresholds for batter metrics.

Thresholds are not chosen by intuition. Each was measured by split-half
correlation on 2024 data: give each batter two disjoint random samples
of n opportunities, compute the rate in each half, correlate across
batters. The threshold is where r reaches ~0.7 — the point at which the
number reflects the player rather than the draw.

Measured curves (r by sample size):

    Chase%          25:0.36  50:0.49  100:0.61  200:0.75  300:0.80
    Zone Swing%     25:0.21  50:0.38  100:0.57  200:0.73  300:0.82
    Zone Contact%   25:0.26  50:0.45  100:0.65  200:0.78  300:0.84
    HardHit%        25:0.33  50:0.53  100:0.72  150:0.80
    Barrel%         25:0.23  50:0.47  100:0.65  150:0.74

Barrel% stabilises slowest because barrels are rare (7.8% of BBE).
HardHit% stabilises fastest because the event is common (39%).
"""

from __future__ import annotations

# Minimum opportunities in the metric's own denominator for r ~ 0.7.
STABILIZATION: dict[str, tuple[str, int]] = {
    "chase_pct":        ("n_out_of_zone", 200),
    "zone_swing_pct":   ("n_in_zone", 200),
    "zone_contact_pct": ("n_zone_swings", 200),
    "contact_pct":      ("n_swings", 200),
    "whiff_pct":        ("n_swings", 200),
    "hard_hit_pct":     ("bbe", 100),
    "barrel_pct":       ("bbe", 150),
    "sweet_spot_pct":   ("bbe", 150),
    "avg_exit_velocity": ("bbe", 100),
}

INSUFFICIENT = "INSUFFICIENT SAMPLE"


def is_reliable(profile: dict, metric: str) -> bool:
    """Does this profile have enough opportunities for `metric`?

    Unknown metrics return False rather than True: an unmeasured
    threshold is not evidence of reliability.
    """
    if metric not in STABILIZATION:
        return False
    denom_key, minimum = STABILIZATION[metric]
    return profile.get(denom_key, 0) >= minimum


def guarded(profile: dict, metric: str):
    """The metric's value, or INSUFFICIENT SAMPLE.

    CLAUDE.md requires reporting INSUFFICIENT SAMPLE rather than a
    number the data cannot support.
    """
    if not is_reliable(profile, metric):
        return INSUFFICIENT
    return profile.get(metric)


def reliability_report(profile: dict) -> dict[str, bool]:
    """Which metrics in this profile clear their own threshold."""
    return {m: is_reliable(profile, m) for m in STABILIZATION}
