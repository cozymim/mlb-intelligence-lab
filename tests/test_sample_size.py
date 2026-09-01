from src.features.sample_size import (
    INSUFFICIENT,
    STABILIZATION,
    guarded,
    is_reliable,
    reliability_report,
)


def test_each_metric_is_guarded_by_its_own_denominator():
    """Barrel% and HardHit% share a denominator but need different amounts."""
    assert STABILIZATION["barrel_pct"][0] == "bbe"
    assert STABILIZATION["hard_hit_pct"][0] == "bbe"
    assert STABILIZATION["barrel_pct"][1] > STABILIZATION["hard_hit_pct"][1]


def test_reliable_above_threshold():
    p = {"bbe": 200, "hard_hit_pct": 0.42}
    assert is_reliable(p, "hard_hit_pct")
    assert guarded(p, "hard_hit_pct") == 0.42


def test_insufficient_below_threshold():
    p = {"bbe": 120, "barrel_pct": 0.30}
    assert not is_reliable(p, "barrel_pct")
    assert guarded(p, "barrel_pct") == INSUFFICIENT


def test_same_sample_can_be_enough_for_one_metric_and_not_another():
    p = {"bbe": 120, "hard_hit_pct": 0.5, "barrel_pct": 0.5}
    assert guarded(p, "hard_hit_pct") == 0.5
    assert guarded(p, "barrel_pct") == INSUFFICIENT


def test_unknown_metric_is_never_reliable():
    """An unmeasured threshold is not evidence of reliability."""
    assert not is_reliable({"bbe": 10_000}, "made_up_metric")
    assert guarded({"bbe": 10_000}, "made_up_metric") == INSUFFICIENT


def test_missing_denominator_is_treated_as_zero():
    assert not is_reliable({}, "barrel_pct")


def test_reliability_report_covers_every_known_metric():
    report = reliability_report({"bbe": 150, "n_swings": 50})
    assert set(report) == set(STABILIZATION)
    assert report["barrel_pct"] is True
    assert report["whiff_pct"] is False
