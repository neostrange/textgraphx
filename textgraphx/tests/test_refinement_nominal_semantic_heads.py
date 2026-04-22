from unittest.mock import MagicMock

from textgraphx.phase_assertions import PhaseAssertions


def test_refinement_wrapper_runs_nominal_mentions_family_in_order():
    with open("/home/neo/environments/textgraphx/textgraphx/phase_wrappers.py", "r", encoding="utf-8") as f:
        source = f.read()

    numeric = 'refiner.run_rule_family("numeric_value")'
    nominal = 'refiner.run_rule_family("nominal_mentions")'
    cleanup = 'refiner.run_rule_family("mention_cleanup")'

    assert numeric in source
    assert nominal in source
    assert cleanup in source
    assert source.index(numeric) < source.index(nominal) < source.index(cleanup)


def test_after_refinement_includes_nominal_semantic_head_check():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"c": 1}]

    result = PhaseAssertions(graph).after_refinement()
    labels = [c["label"] for c in result.checks]

    assert "EntityMention nodes with nominal semantic head" in labels
