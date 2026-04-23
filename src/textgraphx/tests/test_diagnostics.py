"""Tests for runtime diagnostics registry and execution helpers."""

from __future__ import annotations

from unittest.mock import MagicMock
from textgraphx.queries.query_pack import load_query

import pytest

from textgraphx.diagnostics import (
    query_edge_type_distribution,
    query_entity_density,
    query_factuality_alignment_violations,
    query_factuality_attribution_violations,
    query_factuality_coverage,
    get_registered_diagnostics,
    get_runtime_metrics,
    query_identity_contract_violations,
    list_diagnostic_queries,
    query_entity_specificity_coverage,
    query_entity_state_coverage,
    query_entity_state_type_distribution,
    query_endpoint_contract_violations,
    query_event_external_ref_coverage,
    query_glink_relation_inventory,
    query_numeric_value_transition_inventory,
    query_orphaned_nodes_detection,
    query_phase_assertion_violations,
    query_phase_execution_summary,
    query_pipeline_bottleneck_analysis,
    query_referential_integrity_violations,
)


pytestmark = [pytest.mark.unit]


def test_registered_diagnostics_contains_expected_queries():
    names = list_diagnostic_queries()
    assert "phase_execution_summary" in names
    assert "phase_assertion_violations" in names
    assert "orphaned_nodes_detection" in names
    assert "pipeline_bottleneck_analysis" in names
    assert "edge_type_distribution" in names
    assert "entity_density" in names
    assert "endpoint_contract_violations" in names
    assert "referential_integrity_violations" in names
    assert "identity_contract_violations" in names
    assert "numeric_value_transition_inventory" in names
    assert "provenance_contract_violations" in names
    assert "entity_state_coverage" in names
    assert "entity_state_type_distribution" in names
    assert "entity_specificity_coverage" in names
    assert "event_external_ref_coverage" in names
    assert "factuality_coverage" in names
    assert "factuality_attribution_violations" in names
    assert "factuality_alignment_violations" in names
    assert "glink_relation_inventory" in names
    assert "tlink_consistency_violations" in names
    assert "tlink_anchor_consistency_inventory" in names
    assert "timexmention_contract_inventory" in names


def test_registered_diagnostics_metadata_shape():
    rows = get_registered_diagnostics()
    assert rows
    assert all("name" in row for row in rows)
    assert all("expected_fields" in row for row in rows)


def test_query_phase_execution_summary_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"phase": "ingestion", "execution_count": 2, "documents_processed": 10, "duration_seconds": 1.5}
    ]
    rows = query_phase_execution_summary(graph)
    assert rows[0]["phase"] == "ingestion"
    assert graph.run.called


def test_query_phase_assertion_violations_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"phase": "temporal", "assertion": "missing_tlinks", "violation_count": 1}
    ]
    rows = query_phase_assertion_violations(graph)
    assert rows[0]["violation_count"] == 1


def test_query_orphaned_nodes_detection_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"label": "TIMEX", "orphan_count": 2}
    ]
    rows = query_orphaned_nodes_detection(graph)
    assert rows[0]["label"] == "TIMEX"


def test_query_pipeline_bottleneck_analysis_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"phase": "temporal", "execution_count": 2, "avg_duration_seconds": 1.8, "max_duration_seconds": 2.1}
    ]
    rows = query_pipeline_bottleneck_analysis(graph)
    assert rows[0]["avg_duration_seconds"] == 1.8


def test_query_edge_type_distribution_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"rel_type": "TLINK", "rel_count": 12}
    ]
    rows = query_edge_type_distribution(graph)
    assert rows[0]["rel_type"] == "TLINK"


def test_query_entity_density_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"document_id": 101, "entity_mentions": 7, "event_mentions": 3, "timex_mentions": 2}
    ]
    rows = query_entity_density(graph)
    assert rows[0]["entity_mentions"] == 7


def test_query_endpoint_contract_violations_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [{"rel_type": "TLINK", "violation_count": 2}]
    rows = query_endpoint_contract_violations(graph)
    assert rows[0]["rel_type"] == "TLINK"


def test_query_referential_integrity_violations_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"contract": "EventMention_REFERS_TO_TEvent", "violation_count": 1}
    ]
    rows = query_referential_integrity_violations(graph)
    assert rows[0]["contract"] == "EventMention_REFERS_TO_TEvent"


def test_query_identity_contract_violations_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"identity_rule": "NamedEntity_token_identity_missing", "violation_count": 3}
    ]
    rows = query_identity_contract_violations(graph)
    assert rows[0]["identity_rule"] == "NamedEntity_token_identity_missing"


def test_query_numeric_value_transition_inventory_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"metric": "namedentity_numeric_labels", "item_count": 3}
    ]
    rows = query_numeric_value_transition_inventory(graph)
    assert rows[0]["metric"] == "namedentity_numeric_labels"


def test_query_entity_state_coverage_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"total_entity_mentions": 10, "entity_mentions_with_state": 4, "coverage_ratio": 0.4}
    ]
    rows = query_entity_state_coverage(graph)
    assert rows[0]["entity_mentions_with_state"] == 4


def test_query_entity_state_type_distribution_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"entity_state_type": "ATTRIBUTE", "mention_count": 3},
        {"entity_state_type": "STATE", "mention_count": 1},
    ]
    rows = query_entity_state_type_distribution(graph)
    assert rows[0]["entity_state_type"] == "ATTRIBUTE"


def test_entity_state_type_distribution_query_avoids_nullif_for_neo4j_compatibility():
    query = load_query("entity_state_type_distribution")
    assert "nullif" not in query.lower()
    assert "case" in query.lower()


def test_query_entity_specificity_coverage_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"total_mentions": 10, "mentions_with_ent_class": 6, "coverage_ratio": 0.6}
    ]
    rows = query_entity_specificity_coverage(graph)
    assert rows[0]["mentions_with_ent_class"] == 6


def test_query_event_external_ref_coverage_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"total_event_nodes": 8, "event_nodes_with_external_ref": 5, "coverage_ratio": 0.625}
    ]
    rows = query_event_external_ref_coverage(graph)
    assert rows[0]["event_nodes_with_external_ref"] == 5


def test_query_factuality_coverage_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"total_event_mentions": 10, "event_mentions_with_factuality": 7, "coverage_ratio": 0.7}
    ]
    rows = query_factuality_coverage(graph)
    assert rows[0]["event_mentions_with_factuality"] == 7


def test_query_factuality_attribution_violations_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"missing_source_count": 2, "missing_confidence_count": 1, "missing_contract_count": 2}
    ]
    rows = query_factuality_attribution_violations(graph)
    assert rows[0]["missing_contract_count"] == 2


def test_query_factuality_alignment_violations_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"mention_factuality": "ASSERTED", "tevent_factuality": "REPORTED", "violation_count": 3}
    ]
    rows = query_factuality_alignment_violations(graph)
    assert rows[0]["violation_count"] == 3


def test_query_glink_relation_inventory_runs_query_pack_entry():
    graph = MagicMock()
    graph.run.return_value.data.return_value = [
        {"reltype": "CONDITIONAL", "glink_count": 2}
    ]
    rows = query_glink_relation_inventory(graph)
    assert rows[0]["glink_count"] == 2


def test_get_runtime_metrics_aggregates_totals_from_queries():
    graph = MagicMock()
    graph.run.return_value.data.side_effect = [
        [{"phase": "temporal", "execution_count": 1, "documents_processed": 5, "duration_seconds": 1.1}],
        [{"phase": "temporal", "assertion": "x", "violation_count": 3}],
        [{"label": "TIMEX", "orphan_count": 2}],
        [{"phase": "temporal", "execution_count": 1, "avg_duration_seconds": 1.1, "max_duration_seconds": 1.1}],
        [{"rel_type": "TLINK", "rel_count": 11}],
        [{"document_id": 42, "entity_mentions": 10, "event_mentions": 4, "timex_mentions": 2}],
        [{"rel_type": "TLINK", "violation_count": 2}],
        [{"contract": "EventMention_REFERS_TO_TEvent", "violation_count": 1}],
        [{"identity_rule": "NamedEntity_token_identity_missing", "violation_count": 2}],
        [
            {"metric": "namedentity_numeric_labels", "item_count": 4},
            {"metric": "namedentity_value_labels", "item_count": 5},
            {"metric": "canonical_value_nodes", "item_count": 6},
            {"metric": "namedentity_value_tagged_history", "item_count": 7},
        ],
        [{"rel_type": "TLINK", "missing_contract_count": 4}],
        [{"rel_type_1": "BEFORE", "rel_type_2": "AFTER", "conflict_count": 1}],
        [
            {"metric": "inconsistent_tlinks", "item_count": 2},
            {"metric": "self_link_tlinks", "item_count": 1},
            {"metric": "endpoint_violation_tlinks", "item_count": 1},
            {"metric": "anchor_filter_suppressed_tlinks", "item_count": 2},
            {"metric": "missing_anchor_metadata_tlinks", "item_count": 3},
        ],
        [{"total_entity_mentions": 10, "entity_mentions_with_state": 4, "coverage_ratio": 0.4}],
        [{"entity_state_type": "ATTRIBUTE", "mention_count": 3}, {"entity_state_type": "STATE", "mention_count": 1}],
        [{"total_mentions": 10, "mentions_with_ent_class": 6, "coverage_ratio": 0.6}],
        [{"total_event_nodes": 8, "event_nodes_with_external_ref": 5, "coverage_ratio": 0.625}],
        [{"total_event_mentions": 10, "event_mentions_with_factuality": 7, "coverage_ratio": 0.7}],
        [{"missing_source_count": 1, "missing_confidence_count": 2, "missing_contract_count": 2}],
        [{"mention_factuality": "ASSERTED", "tevent_factuality": "REPORTED", "violation_count": 3}],
        [{"reltype": "CONDITIONAL", "glink_count": 2}],
        [
            {"metric": "in_frame_missing", "item_count": 8},
            {"metric": "in_mention_missing", "item_count": 9},
        ],
        [
            {"metric": "missing_doc_id", "item_count": 1},
            {"metric": "missing_span_coordinates", "item_count": 2},
            {"metric": "broken_refers_to_chain", "item_count": 3},
            {"metric": "dct_timexmention_count", "item_count": 0},
        ],
    ]

    payload = get_runtime_metrics(graph)
    totals = payload["totals"]
    assert totals["assertion_violation_count"] == 3
    assert totals["orphaned_node_count"] == 2
    assert totals["endpoint_violation_count"] == 2
    assert totals["referential_integrity_violation_count"] == 1
    assert totals["identity_contract_violation_count"] == 2
    assert totals["namedentity_numeric_label_count"] == 4
    assert totals["namedentity_value_label_count"] == 5
    assert totals["canonical_value_node_count"] == 6
    assert totals["namedentity_value_tagged_history_count"] == 7
    assert totals["provenance_violation_count"] == 4
    assert totals["entity_mentions_with_state_count"] == 4
    assert totals["entity_state_coverage_ratio"] == 0.4
    assert totals["entity_state_typed_mentions_count"] == 4
    assert totals["mentions_with_ent_class_count"] == 6
    assert totals["entity_specificity_coverage_ratio"] == 0.6
    assert totals["event_nodes_with_external_ref_count"] == 5
    assert totals["event_external_ref_coverage_ratio"] == 0.625
    assert totals["event_mentions_with_factuality_count"] == 7
    assert totals["factuality_coverage_ratio"] == 0.7
    assert totals["factuality_attribution_violation_count"] == 2
    assert totals["factuality_alignment_violation_count"] == 3
    assert totals["glink_count"] == 2
    assert totals["tlink_conflict_count"] == 1
    assert totals["tlink_anchor_inconsistent_count"] == 2
    assert totals["tlink_anchor_self_link_count"] == 1
    assert totals["tlink_anchor_endpoint_violation_count"] == 1
    assert totals["tlink_anchor_filter_suppressed_count"] == 2
    assert totals["tlink_missing_anchor_metadata_count"] == 3
    assert totals["participation_in_frame_missing_count"] == 8
    assert totals["participation_in_mention_missing_count"] == 9
    assert totals["timexmention_missing_doc_id_count"] == 1
    assert totals["timexmention_missing_span_coordinates_count"] == 2
    assert totals["timexmention_broken_refers_to_count"] == 3
    assert totals["dct_timexmention_count"] == 0
    assert payload["pipeline_bottleneck_analysis"][0]["phase"] == "temporal"
    assert payload["edge_type_distribution"][0]["rel_type"] == "TLINK"
    assert payload["entity_density"][0]["document_id"] == 42
