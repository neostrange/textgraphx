"""Unit tests for the SRL role-label normalizer.

Tests cover the ``normalize_role`` function in
``textgraphx.adapters.srl_role_normalizer``.
"""
from __future__ import annotations

import pytest
from textgraphx.adapters.srl_role_normalizer import normalize_role, RoleNormalization


@pytest.mark.unit
class TestNormalizeRoleBasic:
    def test_plain_arg_unchanged(self):
        n = normalize_role("ARG0")
        assert n.canonical == "ARG0"
        assert n.raw == "ARG0"
        assert n.flags == {}

    def test_argm_unchanged(self):
        n = normalize_role("ARGM-TMP")
        assert n.canonical == "ARGM-TMP"
        assert n.raw == "ARGM-TMP"
        assert n.flags == {}

    def test_continuation_prefix_stripped(self):
        n = normalize_role("C-ARG1")
        assert n.canonical == "ARG1"
        assert n.raw == "C-ARG1"
        assert n.flags.get("is_continuation") is True
        assert "is_relative" not in n.flags
        assert "predicative" not in n.flags

    def test_relative_prefix_stripped(self):
        n = normalize_role("R-ARG0")
        assert n.canonical == "ARG0"
        assert n.raw == "R-ARG0"
        assert n.flags.get("is_relative") is True
        assert "is_continuation" not in n.flags

    def test_predicative_suffix_stripped(self):
        n = normalize_role("ARG1-PRD")
        assert n.canonical == "ARG1"
        assert n.raw == "ARG1-PRD"
        assert n.flags.get("predicative") is True

    def test_argm_prd_suffix_stripped(self):
        # Edge case: ARGM-PRD is not the same as ARG1-PRD; the suffix -PRD only
        # applies when the suffix is literally "-PRD" at the end.
        n = normalize_role("ARGM-PRD")
        # "ARGM-PRD" ends with "-PRD" → predicative=True, canonical="ARGM"
        assert n.canonical == "ARGM"
        assert n.flags.get("predicative") is True

    def test_raw_always_preserved(self):
        for label in ("C-ARG1", "R-ARG0", "ARG1-PRD", "ARG2", "ARGM-TMP", "C-ARGM-TMP"):
            n = normalize_role(label)
            assert n.raw == label

    def test_returns_role_normalization_namedtuple(self):
        n = normalize_role("ARG2")
        assert isinstance(n, RoleNormalization)

    def test_c_argm_tmp_continuation(self):
        n = normalize_role("C-ARGM-TMP")
        assert n.canonical == "ARGM-TMP"
        assert n.flags.get("is_continuation") is True


@pytest.mark.unit
@pytest.mark.contract
class TestNormalizeRoleContract:
    """Contract: raw label is always preserved; flags are booleans."""

    @pytest.mark.parametrize("label", [
        "ARG0", "ARG1", "ARG2", "ARGM-TMP", "ARGM-LOC", "ARGM-MNR",
        "C-ARG0", "C-ARG1", "R-ARG0", "R-ARG1", "ARG1-PRD",
    ])
    def test_raw_preserved(self, label):
        assert normalize_role(label).raw == label

    @pytest.mark.parametrize("label,expected_canonical", [
        ("C-ARG1", "ARG1"),
        ("R-ARG0", "ARG0"),
        ("ARG1-PRD", "ARG1"),
        ("ARG2", "ARG2"),
        ("ARGM-TMP", "ARGM-TMP"),
    ])
    def test_canonical(self, label, expected_canonical):
        assert normalize_role(label).canonical == expected_canonical
