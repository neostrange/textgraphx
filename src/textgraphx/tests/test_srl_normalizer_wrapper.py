"""Focused tests for the moved SRL normalization helpers."""

import textgraphx.srl_normalizer as legacy_srl_normalizer
from textgraphx.reasoning import srl_normalizer as canonical_srl_normalizer


def test_srl_normalizer_wrapper_reexports_canonical_symbols():
    assert legacy_srl_normalizer.SRLRoleNormalizer is canonical_srl_normalizer.SRLRoleNormalizer
    assert legacy_srl_normalizer.normalize_srl_annotation is canonical_srl_normalizer.normalize_srl_annotation


def test_normalize_srl_annotation_maps_core_and_modifier_roles():
    result = canonical_srl_normalizer.normalize_srl_annotation(
        "say",
        {"ARG0": "Alice", "ARG1": "hello", "ARGM-TMP": "today"},
    )

    assert result["canonical_frame"] == "Communication"
    assert result["canonical_roles"]["agent"] == "Alice"
    assert result["canonical_roles"]["patient"] == "hello"
    assert result["canonical_roles"]["temporal"] == "today"
    assert 0.0 < result["annotation_confidence"] <= 1.0