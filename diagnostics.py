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
    "glink_relation_inventory": DiagnosticQuery(
        name="glink_relation_inventory",
        query_pack_name="glink_relation_inventory",
        description="Distribution of GLINK relationships by relType.",
        expected_fields=["reltype", "glink_count"],
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


def query_glink_relation_inventory(graph: Any) -> List[Dict[str, Any]]:
    """Return GLINK relation distribution by relType."""
    return _execute_registered_query(graph, "glink_relation_inventory")


def get_runtime_metrics(graph: Any) -> Dict[str, Any]:
    """Collect runtime diagnostics in one payload.

    Includes phase duration metrics, assertion violations, endpoint contract
    violations, provenance contract gaps, entity-state coverage/type stats,
    and TLINK consistency alerts.
    """
    phase_summary = query_phase_execution_summary(graph)
    assertion_violations = query_phase_assertion_violations(graph)
    endpoint_violations = query_endpoint_contract_violations(graph)
    provenance_violations = _execute_registered_query(graph, "provenance_contract_violations")
    tlink_violations = _execute_registered_query(graph, "tlink_consistency_violations")
    entity_state_coverage = query_entity_state_coverage(graph)
    entity_state_type_distribution = query_entity_state_type_distribution(graph)
    entity_specificity_coverage = query_entity_specificity_coverage(graph)
    event_external_ref_coverage = query_event_external_ref_coverage(graph)
    glink_relation_inventory = query_glink_relation_inventory(graph)

    total_endpoint_violations = sum(int(row.get("violation_count", 0) or 0) for row in endpoint_violations)
    total_assertion_violations = sum(int(row.get("violation_count", 0) or 0) for row in assertion_violations)
    total_provenance_violations = sum(
        int(row.get("missing_contract_count", 0) or 0) for row in provenance_violations
    )
    total_tlink_conflicts = sum(int(row.get("conflict_count", 0) or 0) for row in tlink_violations)
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
    total_glinks = sum(int(row.get("glink_count", 0) or 0) for row in glink_relation_inventory)

    return {
        "diagnostics": get_registered_diagnostics(),
        "phase_execution_summary": phase_summary,
        "phase_assertion_violations": assertion_violations,
        "endpoint_contract_violations": endpoint_violations,
        "provenance_contract_violations": provenance_violations,
        "entity_state_coverage": entity_state_coverage,
        "entity_state_type_distribution": entity_state_type_distribution,
        "entity_specificity_coverage": entity_specificity_coverage,
        "event_external_ref_coverage": event_external_ref_coverage,
        "glink_relation_inventory": glink_relation_inventory,
        "tlink_consistency_violations": tlink_violations,
        "totals": {
            "endpoint_violation_count": total_endpoint_violations,
            "assertion_violation_count": total_assertion_violations,
            "provenance_violation_count": total_provenance_violations,
            "entity_mentions_with_state_count": total_entity_mentions_with_state,
            "entity_state_coverage_ratio": entity_state_coverage_ratio,
            "entity_state_typed_mentions_count": total_entity_state_typed_mentions,
            "mentions_with_ent_class_count": total_mentions_with_ent_class,
            "entity_specificity_coverage_ratio": entity_specificity_coverage_ratio,
            "event_nodes_with_external_ref_count": total_event_nodes_with_external_ref,
            "event_external_ref_coverage_ratio": event_external_ref_coverage_ratio,
            "glink_count": total_glinks,
            "tlink_conflict_count": total_tlink_conflicts,
        },
    }
