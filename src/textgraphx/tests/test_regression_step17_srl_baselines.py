"""Tests for Step 17: SRL-profile baseline rotation discipline.

Guards verified:
- SRLProfileBaseline dataclass has all required fields
- SRL_PROFILES constant contains the four canonical profiles
- to_dict/from_dict roundtrip is lossless
- relation_kind_delta computes correct per-kind deltas
- SRLProfileBaselineManager.save + load roundtrip
- rotate() archives old file and writes new one
- rotate() rejects empty reason
- rotate() sets timestamp and rotation_reason on new baseline
- compare() returns 'no_baseline' when no locked baseline exists
- compare() detects regression_kinds and improvement_kinds
- compare() overall event/relation deltas are correct
- build_review_bundle() verdict = PASS / REGRESSION / DETERMINISM_FAIL / CONSISTENCY_FAIL
- build_review_bundle() includes variance dict when supplied
- VarianceReport and BaselineManager still importable (no regressions)

No live Neo4j required.
"""
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from textgraphx.evaluation.regression_detector import (
    SRL_PROFILES,
    SRLProfileBaseline,
    SRLProfileBaselineManager,
    build_review_bundle,
    VarianceReport,
)


@pytest.fixture
def tmp_baseline_dir(tmp_path):
    return tmp_path / "baselines"


@pytest.fixture
def manager(tmp_baseline_dir):
    return SRLProfileBaselineManager(tmp_baseline_dir)


def _make_baseline(profile="verbal_only", **kwargs) -> SRLProfileBaseline:
    defaults = dict(
        profile=profile,
        timestamp="20260501T120000Z",
        rotation_reason="initial",
        event_strict_f1=0.50,
        event_relaxed_f1=0.55,
        relation_strict_f1=0.30,
        relation_relaxed_f1=0.35,
        relation_by_kind={"has_participant": 0.40, "tlink": 0.20, "slink": 0.05},
        determinism_pass=True,
        cross_phase_consistency_pass=True,
    )
    defaults.update(kwargs)
    return SRLProfileBaseline(**defaults)


# ---------------------------------------------------------------------------
# SRL_PROFILES constant
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_srl_profiles_contains_four_entries():
    assert len(SRL_PROFILES) == 4


@pytest.mark.unit
def test_srl_profiles_contains_expected_names():
    names = set(SRL_PROFILES)
    assert "verbal_only" in names
    assert "verbal_plus_nominal_ungated" in names
    assert "verbal_plus_nominal_gated" in names
    assert "verbal_plus_nominal_gated_aligns_with" in names


# ---------------------------------------------------------------------------
# SRLProfileBaseline dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_baseline_has_profile_field():
    b = _make_baseline()
    assert b.profile == "verbal_only"


@pytest.mark.unit
def test_baseline_has_rotation_reason():
    b = _make_baseline(rotation_reason="step 9 improved relation F1")
    assert "step 9" in b.rotation_reason


@pytest.mark.unit
def test_baseline_to_dict_roundtrip():
    b = _make_baseline()
    d = b.to_dict()
    b2 = SRLProfileBaseline.from_dict(d)
    assert b2.profile == b.profile
    assert b2.event_strict_f1 == b.event_strict_f1
    assert b2.relation_by_kind == b.relation_by_kind


@pytest.mark.unit
def test_relation_kind_delta_correct():
    b1 = _make_baseline(relation_by_kind={"has_participant": 0.40, "tlink": 0.20})
    b2 = _make_baseline(relation_by_kind={"has_participant": 0.45, "tlink": 0.18})
    deltas = b2.relation_kind_delta(b1)
    assert abs(deltas["has_participant"] - 0.05) < 1e-9
    assert abs(deltas["tlink"] - (-0.02)) < 1e-9


@pytest.mark.unit
def test_relation_kind_delta_includes_new_kinds():
    b1 = _make_baseline(relation_by_kind={"tlink": 0.20})
    b2 = _make_baseline(relation_by_kind={"tlink": 0.22, "clink": 0.05})
    deltas = b2.relation_kind_delta(b1)
    assert "clink" in deltas
    assert abs(deltas["clink"] - 0.05) < 1e-9


# ---------------------------------------------------------------------------
# SRLProfileBaselineManager — save / load
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_save_and_load_roundtrip(manager):
    b = _make_baseline()
    manager.save(b)
    loaded = manager.load("verbal_only")
    assert loaded is not None
    assert loaded.event_strict_f1 == b.event_strict_f1


@pytest.mark.unit
def test_load_missing_returns_none(manager):
    assert manager.load("verbal_only") is None


@pytest.mark.unit
def test_list_profiles_empty_initially(manager):
    assert manager.list_profiles() == []


@pytest.mark.unit
def test_list_profiles_after_save(manager):
    manager.save(_make_baseline("verbal_only"))
    manager.save(_make_baseline("verbal_plus_nominal_gated"))
    listed = manager.list_profiles()
    assert "verbal_only" in listed
    assert "verbal_plus_nominal_gated" in listed


# ---------------------------------------------------------------------------
# rotate()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rotate_creates_new_file(manager):
    b_old = _make_baseline(event_strict_f1=0.50)
    manager.save(b_old)
    b_new = _make_baseline(event_strict_f1=0.55)
    new_path, archived_path = manager.rotate(b_new, reason="step 9 improved F1")
    assert new_path.exists()


@pytest.mark.unit
def test_rotate_archives_old_file(manager):
    b_old = _make_baseline(timestamp="20260501T120000Z", event_strict_f1=0.50)
    manager.save(b_old)
    b_new = _make_baseline(event_strict_f1=0.55)
    _, archived_path = manager.rotate(b_new, reason="improvement")
    assert archived_path is not None
    assert archived_path.exists()


@pytest.mark.unit
def test_rotate_sets_rotation_reason(manager):
    manager.save(_make_baseline(event_strict_f1=0.50))
    b_new = _make_baseline(event_strict_f1=0.55)
    manager.rotate(b_new, reason="step 11 TLINK recall +0.03")
    loaded = manager.load("verbal_only")
    assert "step 11" in loaded.rotation_reason


@pytest.mark.unit
def test_rotate_sets_timestamp(manager):
    manager.save(_make_baseline())
    b_new = _make_baseline(timestamp="")
    manager.rotate(b_new, reason="any reason")
    loaded = manager.load("verbal_only")
    assert loaded.timestamp  # not empty


@pytest.mark.unit
def test_rotate_rejects_empty_reason(manager):
    manager.save(_make_baseline())
    b_new = _make_baseline()
    with pytest.raises(ValueError, match="non-empty reason"):
        manager.rotate(b_new, reason="")


@pytest.mark.unit
def test_rotate_rejects_whitespace_only_reason(manager):
    manager.save(_make_baseline())
    b_new = _make_baseline()
    with pytest.raises(ValueError, match="non-empty reason"):
        manager.rotate(b_new, reason="   ")


@pytest.mark.unit
def test_rotate_no_prior_baseline_archived_path_is_none(manager):
    b_new = _make_baseline()
    _, archived_path = manager.rotate(b_new, reason="first rotation")
    assert archived_path is None


# ---------------------------------------------------------------------------
# compare()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_compare_no_baseline(manager):
    result = manager.compare("verbal_only", _make_baseline())
    assert result["status"] == "no_baseline"


@pytest.mark.unit
def test_compare_ok_when_no_regression(manager):
    b_locked = _make_baseline(relation_by_kind={"has_participant": 0.40, "tlink": 0.20})
    manager.save(b_locked)
    b_candidate = _make_baseline(relation_by_kind={"has_participant": 0.42, "tlink": 0.22})
    result = manager.compare("verbal_only", b_candidate)
    assert result["status"] == "ok"
    assert not result["regression_kinds"]


@pytest.mark.unit
def test_compare_regression_detected(manager):
    b_locked = _make_baseline(relation_by_kind={"has_participant": 0.40, "tlink": 0.20})
    manager.save(b_locked)
    b_candidate = _make_baseline(relation_by_kind={"has_participant": 0.35, "tlink": 0.20})
    result = manager.compare("verbal_only", b_candidate)
    assert result["status"] == "regression"
    assert "has_participant" in result["regression_kinds"]


@pytest.mark.unit
def test_compare_deltas_correct(manager):
    b_locked = _make_baseline(
        event_strict_f1=0.50,
        relation_strict_f1=0.30,
        relation_by_kind={"tlink": 0.20},
    )
    manager.save(b_locked)
    b_candidate = _make_baseline(
        event_strict_f1=0.53,
        relation_strict_f1=0.32,
        relation_by_kind={"tlink": 0.22},
    )
    result = manager.compare("verbal_only", b_candidate)
    assert abs(result["event_strict_f1_delta"] - 0.03) < 1e-9
    assert abs(result["relation_strict_f1_delta"] - 0.02) < 1e-9


@pytest.mark.unit
def test_compare_includes_improvement_kinds(manager):
    b_locked = _make_baseline(relation_by_kind={"tlink": 0.20, "clink": 0.0})
    manager.save(b_locked)
    b_candidate = _make_baseline(relation_by_kind={"tlink": 0.20, "clink": 0.05})
    result = manager.compare("verbal_only", b_candidate)
    assert "clink" in result["improvement_kinds"]


# ---------------------------------------------------------------------------
# build_review_bundle()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_review_bundle_pass():
    comparisons = [
        {"status": "ok", "determinism_pass": True},
        {"status": "ok", "determinism_pass": True},
    ]
    bundle = build_review_bundle(comparisons)
    assert bundle["verdict"] == "PASS"


@pytest.mark.unit
def test_review_bundle_regression():
    comparisons = [
        {"status": "regression", "determinism_pass": True},
    ]
    bundle = build_review_bundle(comparisons)
    assert bundle["verdict"] == "REGRESSION"


@pytest.mark.unit
def test_review_bundle_determinism_fail():
    comparisons = [
        {"status": "ok", "determinism_pass": False},
    ]
    bundle = build_review_bundle(comparisons)
    assert bundle["verdict"] == "DETERMINISM_FAIL"


@pytest.mark.unit
def test_review_bundle_consistency_fail():
    comparisons = [{"status": "ok", "determinism_pass": True}]
    bundle = build_review_bundle(comparisons, consistency_issues=["orphaned event e123"])
    assert bundle["verdict"] == "CONSISTENCY_FAIL"
    assert "orphaned event e123" in bundle["consistency_issues"]


@pytest.mark.unit
def test_review_bundle_includes_variance():
    vr = VarianceReport(run_count=3, quality_scores=[0.5, 0.5, 0.5], mean_quality=0.5, is_deterministic=True)
    bundle = build_review_bundle([], variance_report=vr)
    assert "variance" in bundle
    assert bundle["variance"]["run_count"] == 3


@pytest.mark.unit
def test_review_bundle_regression_takes_precedence_over_det_fail():
    comparisons = [
        {"status": "regression", "determinism_pass": False},
    ]
    bundle = build_review_bundle(comparisons)
    assert bundle["verdict"] == "REGRESSION"
