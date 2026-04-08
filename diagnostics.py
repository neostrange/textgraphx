"""Runtime diagnostics query registry and execution helpers.

The registry provides stable query names and result schemas so CI and
operator tooling can consume diagnostics safely across refactors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from textgraphx.queries.query_pack import load_query


@dataclass(frozen=True)
class DiagnosticQuery:
    """Metadata describing a registered runtime diagnostic query."""

    name: str
    query_pack_name: str
    description: str
    expected_fields: List[str]


DIAGNOSTIC_QUERY_REGISTRY: Dict[str, DiagnosticQuery] = {
    "phase_execution_summary": DiagnosticQuery(
        name="phase_execution_summary",
        query_pack_name="phase_execution_summary",
        description="Aggregates phase execution counts and duration metrics.",
        expected_fields=["phase", "execution_count", "documents_processed", "duration_seconds"],
    ),
    "phase_assertion_violations": DiagnosticQuery(
        name="phase_assertion_violations",
        query_pack_name="phase_assertion_violations",
        description="Summarizes failed phase assertions by phase and assertion label.",
        expected_fields=["phase", "assertion", "violation_count"],
    ),
    "endpoint_contract_violations": DiagnosticQuery(
        name="endpoint_contract_violations",
        query_pack_name="endpoint_contract_violations",
        description="Counts relationship endpoint contract violations by relation type.",
        expected_fields=["rel_type", "violation_count"],
    ),
    "referential_integrity_violations": DiagnosticQuery(
        name="referential_integrity_violations",
        query_pack_name="referential_integrity_violations",
        description="Counts missing canonical mention/event referential chains.",
        expected_fields=["contract", "violation_count"],
    ),
    "identity_contract_violations": DiagnosticQuery(
        name="identity_contract_violations",
        query_pack_name="identity_contract_violations",
        description="Counts missing or incomplete identity fields on canonical span-bearing nodes.",
        expected_fields=["identity_rule", "violation_count"],
    ),
    "numeric_value_transition_inventory": DiagnosticQuery(
        name="numeric_value_transition_inventory",
        query_pack_name="numeric_value_transition_inventory",
        description="Inventories transitional NUMERIC/VALUE label usage versus canonical VALUE nodes.",
        expected_fields=["metric", "item_count"],
    ),
    "provenance_contract_violations": DiagnosticQuery(
        name="provenance_contract_violations",
        query_pack_name="provenance_contract_violations",
        description="Counts missing provenance contract fields for inferred edges.",
        expected_fields=["rel_type", "missing_contract_count"],
    ),
    "tlink_consistency_violations": DiagnosticQuery(
        name="tlink_consistency_violations",
        query_pack_name="tlink_consistency_violations",
        description="Detects contradictory unsuppressed TLINK pairs.",
        expected_fields=["rel_type_1", "rel_type_2", "conflict_count"],
    ),
    "tlink_anchor_consistency_inventory": DiagnosticQuery(
        name="tlink_anchor_consistency_inventory",
        query_pack_name="tlink_anchor_consistency_inventory",
        description="Inventories TLINK anchor consistency flags and anchor-filter suppression counts.",
        expected_fields=["metric", "item_count"],
    ),
    "entity_state_coverage": DiagnosticQuery(
        name="entity_state_coverage",
        query_pack_name="entity_state_coverage",
        description="Tracks coverage of entity mentions enriched with situational state signals.",
        expected_fields=["total_entity_mentions", "entity_mentions_with_state", "coverage_ratio"],
    ),
    "entity_state_type_distribution": DiagnosticQuery(
        name="entity_state_type_distribution",
        query_pack_name="entity_state_type_distribution",
        description="Distribution of normalized entityStateType values on enriched mentions.",
        expected_fields=["entity_state_type", "mention_count"],
    ),
    "entity_specificity_coverage": DiagnosticQuery(
        name="entity_specificity_coverage",
        query_pack_name="entity_specificity_coverage",
        description="Coverage of entity mentions with ent_class specificity labels.",
        expected_fields=["total_mentions", "mentions_with_ent_class", "coverage_ratio"],
    ),
    "event_external_ref_coverage": DiagnosticQuery(
        name="event_external_ref_coverage",
        query_pack_name="event_external_ref_coverage",
        description="Coverage of event nodes carrying external_ref identifiers.",
        expected_fields=["total_event_nodes", "event_nodes_with_external_ref", "coverage_ratio"],
    ),
    "factuality_coverage": DiagnosticQuery(
        name="factuality_coverage",
        query_pack_name="factuality_coverage",
        description="Coverage of EventMention nodes with factuality labels.",
        expected_fields=["total_event_mentions", "event_mentions_with_factuality", "coverage_ratio"],
    ),
    "factuality_attribution_violations": DiagnosticQuery(
        name="factuality_attribution_violations",
        query_pack_name="factuality_attribution_violations",
        description="Counts EventMention factuality records missing attribution contract fields.",
        expected_fields=["missing_source_count", "missing_confidence_count", "missing_contract_count"],
    ),
    "factuality_alignment_violations": DiagnosticQuery(
        name="factuality_alignment_violations",
        query_pack_name="factuality_alignment_violations",
        description="Counts factuality drift between EventMention and canonical TEvent.",
        expected_fields=["mention_factuality", "tevent_factuality", "violation_count"],
    ),
    "glink_relation_inventory": DiagnosticQuery(
        name="glink_relation_inventory",
        query_pack_name="glink_relation_inventory",
        description="Distribution of GLINK relationships by relType.",
        expected_fields=["reltype", "glink_count"],
    ),
    "participation_edge_migration_inventory": DiagnosticQuery(
        name="participation_edge_migration_inventory",
        query_pack_name="participation_edge_migration_inventory",
        description="Counts PARTICIPATES_IN edges missing their IN_FRAME or IN_MENTION dual-write alias.",
        expected_fields=["metric", "item_count"],
    ),
}


def list_diagnostic_queries() -> List[str]:
    """Return stable diagnostic query names sorted alphabetically."""
    return sorted(DIAGNOSTIC_QUERY_REGISTRY.keys())


def get_registered_diagnostics() -> List[Dict[str, Any]]:
    """Return registry metadata for API/CLI discovery endpoints."""
    items = []
    for name in list_diagnostic_queries():
        entry = DIAGNOSTIC_QUERY_REGISTRY[name]
        items.append(
            {
                "name": entry.name,
                "query_pack_name": entry.query_pack_name,
                "description": entry.description,
                "expected_fields": list(entry.expected_fields),
            }
        )
    return items


def _execute_registered_query(
    graph: Any,
    query_name: str,
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if query_name not in DIAGNOSTIC_QUERY_REGISTRY:
        raise KeyError(f"Unknown diagnostics query: {query_name}")
    query = load_query(DIAGNOSTIC_QUERY_REGISTRY[query_name].query_pack_name)
    return graph.run(query, params or {}).data()


def query_phase_execution_summary(graph: Any) -> List[Dict[str, Any]]:
    """Return phase-level execution_time/duration and volume metrics."""
    return _execute_registered_query(graph, "phase_execution_summary")


def query_phase_assertion_violations(graph: Any) -> List[Dict[str, Any]]:
    """Return assertion violation counts by phase and assertion label."""
    return _execute_registered_query(graph, "phase_assertion_violations")


def query_endpoint_contract_violations(graph: Any) -> List[Dict[str, Any]]:
    """Return endpoint contract violation counts grouped by edge type."""
    return _execute_registered_query(graph, "endpoint_contract_violations")


def query_referential_integrity_violations(graph: Any) -> List[Dict[str, Any]]:
    """Return missing canonical referential chain counts."""
    return _execute_registered_query(graph, "referential_integrity_violations")


def query_identity_contract_violations(graph: Any) -> List[Dict[str, Any]]:
    """Return missing identity field counts for canonical nodes."""
    return _execute_registered_query(graph, "identity_contract_violations")


def query_numeric_value_transition_inventory(graph: Any) -> List[Dict[str, Any]]:
    """Return transitional NUMERIC/VALUE inventory counts."""
    return _execute_registered_query(graph, "numeric_value_transition_inventory")


def query_entity_state_coverage(graph: Any) -> List[Dict[str, Any]]:
    """Return entity-state enrichment coverage metrics."""
    return _execute_registered_query(graph, "entity_state_coverage")


def query_entity_state_type_distribution(graph: Any) -> List[Dict[str, Any]]:
    """Return distribution of entity-state type labels."""
    return _execute_registered_query(graph, "entity_state_type_distribution")


def query_entity_specificity_coverage(graph: Any) -> List[Dict[str, Any]]:
    """Return coverage of entity specificity class labels."""
    return _execute_registered_query(graph, "entity_specificity_coverage")


def query_event_external_ref_coverage(graph: Any) -> List[Dict[str, Any]]:
    """Return coverage of external_ref annotation on event nodes."""
    return _execute_registered_query(graph, "event_external_ref_coverage")


def query_factuality_coverage(graph: Any) -> List[Dict[str, Any]]:
    """Return coverage of factuality labels on EventMention nodes."""
    return _execute_registered_query(graph, "factuality_coverage")


def query_factuality_attribution_violations(graph: Any) -> List[Dict[str, Any]]:
    """Return counts of factuality attribution contract gaps on EventMention nodes."""
    return _execute_registered_query(graph, "factuality_attribution_violations")


def query_factuality_alignment_violations(graph: Any) -> List[Dict[str, Any]]:
    """Return factuality mismatches between EventMention and canonical TEvent."""
    return _execute_registered_query(graph, "factuality_alignment_violations")


def query_glink_relation_inventory(graph: Any) -> List[Dict[str, Any]]:
    """Return GLINK relation distribution by relType."""
    return _execute_registered_query(graph, "glink_relation_inventory")


def query_participation_edge_migration_inventory(graph: Any) -> List[Dict[str, Any]]:
    """Return counts of PARTICIPATES_IN edges missing IN_FRAME or IN_MENTION aliases."""
    return _execute_registered_query(graph, "participation_edge_migration_inventory")


def get_runtime_metrics(graph: Any) -> Dict[str, Any]:
    """Collect runtime diagnostics in one payload.

    Includes phase duration metrics, assertion violations, endpoint contract
    violations, provenance contract gaps, entity-state coverage/type stats,
    and TLINK consistency alerts.
    """
    phase_summary = query_phase_execution_summary(graph)
    assertion_violations = query_phase_assertion_violations(graph)
    endpoint_violations = query_endpoint_contract_violations(graph)
    referential_violations = query_referential_integrity_violations(graph)
    identity_violations = query_identity_contract_violations(graph)
    numeric_value_transition = query_numeric_value_transition_inventory(graph)
    provenance_violations = _execute_registered_query(graph, "provenance_contract_violations")
    tlink_violations = _execute_registered_query(graph, "tlink_consistency_violations")
    tlink_anchor_inventory = _execute_registered_query(graph, "tlink_anchor_consistency_inventory")
    entity_state_coverage = query_entity_state_coverage(graph)
    entity_state_type_distribution = query_entity_state_type_distribution(graph)
    entity_specificity_coverage = query_entity_specificity_coverage(graph)
    event_external_ref_coverage = query_event_external_ref_coverage(graph)
    factuality_coverage = query_factuality_coverage(graph)
    factuality_attribution_violations = query_factuality_attribution_violations(graph)
    factuality_alignment_violations = query_factuality_alignment_violations(graph)
    glink_relation_inventory = query_glink_relation_inventory(graph)
    participation_edge_inventory = query_participation_edge_migration_inventory(graph)

    total_endpoint_violations = sum(int(row.get("violation_count", 0) or 0) for row in endpoint_violations)
    total_referential_violations = sum(int(row.get("violation_count", 0) or 0) for row in referential_violations)
    total_identity_violations = sum(int(row.get("violation_count", 0) or 0) for row in identity_violations)
    numeric_value_transition_counts = {
        str(row.get("metric", "")): int(row.get("item_count", 0) or 0)
        for row in numeric_value_transition
    }
    total_assertion_violations = sum(int(row.get("violation_count", 0) or 0) for row in assertion_violations)
    total_provenance_violations = sum(
        int(row.get("missing_contract_count", 0) or 0) for row in provenance_violations
    )
    total_tlink_conflicts = sum(int(row.get("conflict_count", 0) or 0) for row in tlink_violations)
    tlink_anchor_counts = {
        str(row.get("metric", "")): int(row.get("item_count", 0) or 0)
        for row in tlink_anchor_inventory
    }
    state_row = entity_state_coverage[0] if entity_state_coverage else {}
    total_entity_mentions_with_state = int(state_row.get("entity_mentions_with_state", 0) or 0)
    entity_state_coverage_ratio = float(state_row.get("coverage_ratio", 0.0) or 0.0)
    total_entity_state_typed_mentions = sum(
        int(row.get("mention_count", 0) or 0) for row in entity_state_type_distribution
    )
    specificity_row = entity_specificity_coverage[0] if entity_specificity_coverage else {}
    external_ref_row = event_external_ref_coverage[0] if event_external_ref_coverage else {}
    total_mentions_with_ent_class = int(specificity_row.get("mentions_with_ent_class", 0) or 0)
    entity_specificity_coverage_ratio = float(specificity_row.get("coverage_ratio", 0.0) or 0.0)
    total_event_nodes_with_external_ref = int(external_ref_row.get("event_nodes_with_external_ref", 0) or 0)
    event_external_ref_coverage_ratio = float(external_ref_row.get("coverage_ratio", 0.0) or 0.0)
    factuality_row = factuality_coverage[0] if factuality_coverage else {}
    total_mentions_with_factuality = int(factuality_row.get("event_mentions_with_factuality", 0) or 0)
    factuality_coverage_ratio = float(factuality_row.get("coverage_ratio", 0.0) or 0.0)
    attribution_row = factuality_attribution_violations[0] if factuality_attribution_violations else {}
    total_factuality_attribution_violations = int(attribution_row.get("missing_contract_count", 0) or 0)
    total_factuality_alignment_violations = sum(
        int(row.get("violation_count", 0) or 0) for row in factuality_alignment_violations
    )
    total_glinks = sum(int(row.get("glink_count", 0) or 0) for row in glink_relation_inventory)
    participation_edge_counts = {
        str(row.get("metric", "")): int(row.get("item_count", 0) or 0)
        for row in participation_edge_inventory
    }

    return {
        "diagnostics": get_registered_diagnostics(),
        "phase_execution_summary": phase_summary,
        "phase_assertion_violations": assertion_violations,
        "endpoint_contract_violations": endpoint_violations,
        "referential_integrity_violations": referential_violations,
        "identity_contract_violations": identity_violations,
        "numeric_value_transition_inventory": numeric_value_transition,
        "provenance_contract_violations": provenance_violations,
        "entity_state_coverage": entity_state_coverage,
        "entity_state_type_distribution": entity_state_type_distribution,
        "entity_specificity_coverage": entity_specificity_coverage,
        "event_external_ref_coverage": event_external_ref_coverage,
        "factuality_coverage": factuality_coverage,
        "factuality_attribution_violations": factuality_attribution_violations,
        "factuality_alignment_violations": factuality_alignment_violations,
        "glink_relation_inventory": glink_relation_inventory,
        "participation_edge_migration_inventory": participation_edge_inventory,
        "tlink_consistency_violations": tlink_violations,
        "tlink_anchor_consistency_inventory": tlink_anchor_inventory,
        "totals": {
            "endpoint_violation_count": total_endpoint_violations,
            "referential_integrity_violation_count": total_referential_violations,
            "identity_contract_violation_count": total_identity_violations,
            "namedentity_numeric_label_count": numeric_value_transition_counts.get("namedentity_numeric_labels", 0),
            "namedentity_value_label_count": numeric_value_transition_counts.get("namedentity_value_labels", 0),
            "canonical_value_node_count": numeric_value_transition_counts.get("canonical_value_nodes", 0),
            "namedentity_value_tagged_history_count": numeric_value_transition_counts.get("namedentity_value_tagged_history", 0),
            "assertion_violation_count": total_assertion_violations,
            "provenance_violation_count": total_provenance_violations,
            "entity_mentions_with_state_count": total_entity_mentions_with_state,
            "entity_state_coverage_ratio": entity_state_coverage_ratio,
            "entity_state_typed_mentions_count": total_entity_state_typed_mentions,
            "mentions_with_ent_class_count": total_mentions_with_ent_class,
            "entity_specificity_coverage_ratio": entity_specificity_coverage_ratio,
            "event_nodes_with_external_ref_count": total_event_nodes_with_external_ref,
            "event_external_ref_coverage_ratio": event_external_ref_coverage_ratio,
            "event_mentions_with_factuality_count": total_mentions_with_factuality,
            "factuality_coverage_ratio": factuality_coverage_ratio,
            "factuality_attribution_violation_count": total_factuality_attribution_violations,
            "factuality_alignment_violation_count": total_factuality_alignment_violations,
            "glink_count": total_glinks,
            "tlink_conflict_count": total_tlink_conflicts,
            "tlink_anchor_inconsistent_count": tlink_anchor_counts.get("inconsistent_tlinks", 0),
            "tlink_anchor_self_link_count": tlink_anchor_counts.get("self_link_tlinks", 0),
            "tlink_anchor_endpoint_violation_count": tlink_anchor_counts.get("endpoint_violation_tlinks", 0),
            "tlink_anchor_filter_suppressed_count": tlink_anchor_counts.get("anchor_filter_suppressed_tlinks", 0),
            "tlink_missing_anchor_metadata_count": tlink_anchor_counts.get("missing_anchor_metadata_tlinks", 0),
            "participation_in_frame_missing_count": participation_edge_counts.get("in_frame_missing", 0),
            "participation_in_mention_missing_count": participation_edge_counts.get("in_mention_missing", 0),
        },
    }
