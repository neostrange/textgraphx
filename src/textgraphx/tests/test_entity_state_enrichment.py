"""Regression tests for entity-state situational enrichment in RefinementPhase."""

from pathlib import Path


def _ref_src() -> str:
    return (Path(__file__).parent.parent / "pipeline/phases/refinement.py").read_text()


def _wrapper_src() -> str:
    return (Path(__file__).parent.parent / "pipeline/runtime/phase_wrappers.py").read_text()


def test_entity_state_family_exists_in_rule_families():
    src = _ref_src()
    assert '"entity_state"' in src
    assert '"annotate_entity_state_signals"' in src


def test_entity_state_method_defined():
    src = _ref_src()
    assert "def annotate_entity_state_signals(self):" in src


def test_entity_state_cypher_uses_copular_dependency_patterns():
    src = _ref_src()
    method_start = src.index("def annotate_entity_state_signals(self):")
    method_end = src.index("def diagnostic_report(self):")
    method_src = src[method_start:method_end]

    assert "nsubj" in method_src
    assert "acomp" in method_src
    assert "attr" in method_src
    assert "xcomp" in method_src
    assert "copular_predicate" in method_src


def test_entity_state_sets_mention_and_entity_fields():
    src = _ref_src()
    method_start = src.index("def annotate_entity_state_signals(self):")
    method_end = src.index("def diagnostic_report(self):")
    method_src = src[method_start:method_end]

    assert "mention.entityState" in method_src
    assert "mention.entityStateType" in method_src
    assert "mention.entityStateConfidence" in method_src
    assert "e.entityState" in method_src
    assert "e.entityStateType" in method_src
    assert "e.entityStateConfidence" in method_src


def test_refinement_wrapper_runs_entity_state_family_after_cleanup():
    src = _wrapper_src()
    mention_cleanup = 'refiner.run_rule_family("mention_cleanup")'
    entity_state = 'refiner.run_rule_family("entity_state")'

    assert mention_cleanup in src
    assert entity_state in src
    assert src.index(mention_cleanup) < src.index(entity_state)
