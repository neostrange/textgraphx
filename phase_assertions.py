"""Phase-level assertions and run markers for the textgraphx pipeline.

Each phase emits structured timing data and optional graph-node-count assertions.
Assertions are designed to be non-fatal by default (log warnings) but can be
configured to raise ``AssertionError`` for hard failures in CI.

Public surface
--------------
* ``PhaseThresholds``   – dataclass holding per-phase minimum counts.
* ``AssertionResult``   – dataclass returned by every check method.
* ``PhaseAssertions``   – one method per phase; queries Neo4j.
* ``record_phase_run``  – write a ``PhaseRun`` marker node to the graph.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from math import inf
from typing import Any, Dict, List, Optional

from textgraphx.time_utils import utc_iso_now
from textgraphx.provenance import validate_inferred_relationship_provenance
from textgraphx.reasoning_contracts import count_endpoint_violations

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PhaseThresholds:
    """Minimum expected node/relationship counts for each phase.

    All values default to 0 so that unrun phases are treated as unchecked.
    Override any field to tighten assertions for your dataset.
    """

    # --- ingestion ---
    min_annotated_text: int = 1
    min_sentences: int = 1
    min_tag_occurrences: int = 10

    # --- refinement ---
    min_named_entities_with_head: int = 0     # NamedEntity nodes that have head assigned
    min_refers_to_rels: int = 0               # REFERS_TO relationships created
    min_nominal_semantic_heads: int = 0       # EntityMention nominal semantic heads populated

    # --- temporal ---
    min_tevents: int = 0                      # TEvent nodes (0: temporal service optional)
    min_timex: int = 0                        # TIMEX nodes
    min_signals: int = 0                      # Signal nodes
    max_tevents_missing_timeml_core: int = 10**9   # TEvent nodes missing core TimeML fields
    max_timex_missing_timeml_core: int = 10**9     # TIMEX nodes missing core TimeML fields
    max_signals_missing_text_span: int = 10**9     # Signal nodes missing text/span fields
    max_tlinks_missing_reltype_canonical: int = 10**9  # TLINK rels missing relTypeCanonical

    # --- event_enrichment ---
    min_describes_rels: int = 0              # DESCRIBES relationships (Frame->TEvent)
    min_participant_rels: int = 0            # PARTICIPANT relationships
    min_frame_describes_event_rels: int = 0  # FRAME_DESCRIBES_EVENT relationships
    min_has_frame_argument_rels: int = 0     # HAS_FRAME_ARGUMENT relationships
    min_event_participant_rels: int = 0      # EVENT_PARTICIPANT relationships
    min_clink_rels: int = 0                  # CLINK relationships
    min_slink_rels: int = 0                  # SLINK relationships
    max_legacy_to_canonical_describes_ratio: float = inf
    max_legacy_to_canonical_participant_ratio: float = inf
    max_event_participants_per_described_event: float = inf
    max_frame_arguments_per_described_event: float = inf

    # --- tlinks ---
    min_tlink_rels: int = 0                  # TLINK relationships
    max_tlink_rels: int = 10**9              # TLINK absolute upper bound (cost-model)
    max_tlink_consistency_violations: int = 10**9  # Contradictory unsuppressed TLINK pairs
    max_event_endpoint_contract_violations: int = 10**9
    max_tlink_endpoint_contract_violations: int = 10**9


@dataclass
class AssertionResult:
    """Result of a single phase assertion check."""

    phase: str
    passed: bool
    checks: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_check(
        self,
        label: str,
        actual: int,
        minimum: int,
    ) -> None:
        ok = actual >= minimum
        self.checks.append(
            {
                "label": label,
                "actual": actual,
                "minimum": minimum,
                "passed": ok,
            }
        )
        if not ok:
            msg = (
                f"[{self.phase}] {label}: got {actual}, expected >= {minimum}"
            )
            self.errors.append(msg)
            self.passed = False

    def log_summary(self) -> None:
        status = "PASS" if self.passed else "FAIL"
        logger.info("[phase-assert] %s phase assertions: %s", self.phase, status)
        for c in self.checks:
            sym = "✓" if c["passed"] else "✗"
            if "minimum" in c:
                logger.debug(
                    "  %s %s: %s (min %s)",
                    sym,
                    c["label"],
                    c["actual"],
                    c["minimum"],
                )
            elif "maximum" in c:
                logger.debug(
                    "  %s %s: %s (max %s)",
                    sym,
                    c["label"],
                    c["actual"],
                    c["maximum"],
                )
            else:
                logger.debug("  %s %s: %s", sym, c.get("label", "check"), c.get("actual"))
        for err in self.errors:
            logger.warning(err)


# ---------------------------------------------------------------------------
# Phase assertions
# ---------------------------------------------------------------------------


class PhaseAssertions:
    """Run graph-count assertions after each pipeline phase.

    Parameters
    ----------
    graph :
        A Neo4j graph connection (``neo4j_client`` compatible – must expose
        ``.run(query, params).data()``).
    thresholds :
        Optional ``PhaseThresholds`` instance; defaults are used if omitted.
    hard_fail :
        When ``True``, an ``AssertionError`` is raised on the first violated
        threshold.  When ``False`` (default) violations are only logged.
    strict_transition_gate :
        When ``True``, canonical transition telemetry checks in
        ``after_event_enrichment`` are promoted from warning-only signals
        to assertion failures when legacy edges outnumber canonical edges.
    """

    def __init__(
        self,
        graph: Any,
        thresholds: Optional[PhaseThresholds] = None,
        hard_fail: bool = False,
        strict_transition_gate: bool = False,
        enforce_provenance_contracts: bool = False,
    ) -> None:
        self._graph = graph
        self._thresholds = thresholds or PhaseThresholds()
        self._hard_fail = hard_fail
        self._strict_transition_gate = strict_transition_gate
        self._enforce_provenance_contracts = enforce_provenance_contracts

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _count(self, cypher: str, params: Optional[Dict] = None) -> int:
        rows = self._graph.run(cypher, params or {}).data()
        if rows:
            return rows[0].get("c", 0)
        return 0

    def _finalize(self, result: AssertionResult) -> AssertionResult:
        result.log_summary()
        if self._hard_fail and not result.passed:
            raise AssertionError(
                f"Phase assertions failed for '{result.phase}': "
                + "; ".join(result.errors)
            )
        return result

    def _add_provenance_contract_check(
        self,
        result: AssertionResult,
        rel_type: str,
        label: str,
    ) -> None:
        missing = validate_inferred_relationship_provenance(self._graph, rel_type)
        result.checks.append(
            {
                "label": label,
                "actual": missing,
                "minimum": 0,
                "passed": missing == 0,
            }
        )
        if missing != 0:
            result.errors.append(
                f"[{result.phase}] {label}: got {missing}, expected == 0"
            )
            result.passed = False

    def _add_upper_bound_check(
        self,
        result: AssertionResult,
        label: str,
        actual: int,
        maximum: int,
    ) -> None:
        ok = actual <= maximum
        result.checks.append(
            {
                "label": label,
                "actual": actual,
                "maximum": maximum,
                "passed": ok,
            }
        )
        if not ok:
            result.errors.append(
                f"[{result.phase}] {label}: got {actual}, expected <= {maximum}"
            )
            result.passed = False

    # ------------------------------------------------------------------
    # Per-phase assertion methods (Item 5)
    # ------------------------------------------------------------------

    def after_ingestion(self) -> AssertionResult:
        """Assert minimum node counts expected after the ingestion phase."""
        t = self._thresholds
        result = AssertionResult(phase="ingestion", passed=True)

        result.add_check(
            "AnnotatedText nodes",
            self._count("MATCH (n:AnnotatedText) RETURN count(n) AS c"),
            t.min_annotated_text,
        )
        result.add_check(
            "Sentence nodes",
            self._count("MATCH (n:Sentence) RETURN count(n) AS c"),
            t.min_sentences,
        )
        result.add_check(
            "TagOccurrence nodes",
            self._count("MATCH (n:TagOccurrence) RETURN count(n) AS c"),
            t.min_tag_occurrences,
        )

        return self._finalize(result)

    def after_refinement(self) -> AssertionResult:
        """Assert graph state expected after the refinement phase."""
        t = self._thresholds
        result = AssertionResult(phase="refinement", passed=True)

        result.add_check(
            "NamedEntity nodes with head assigned",
            self._count(
                "MATCH (n:NamedEntity) WHERE n.head IS NOT NULL RETURN count(n) AS c"
            ),
            t.min_named_entities_with_head,
        )
        result.add_check(
            "REFERS_TO relationships",
            self._count(
                "MATCH ()-[r:REFERS_TO]->() RETURN count(r) AS c"
            ),
            t.min_refers_to_rels,
        )
        result.add_check(
            "EntityMention nodes with nominal semantic head",
            self._count(
                """
                MATCH (m:EntityMention)
                WHERE m.nominalSemanticHead IS NOT NULL
                   OR m.nominalSemanticHeadTokenIndex IS NOT NULL
                RETURN count(m) AS c
                """
            ),
            t.min_nominal_semantic_heads,
        )

        return self._finalize(result)

    def after_temporal(self) -> AssertionResult:
        """Assert graph state expected after the temporal phase."""
        t = self._thresholds
        result = AssertionResult(phase="temporal", passed=True)

        result.add_check(
            "TEvent nodes",
            self._count("MATCH (n:TEvent) RETURN count(n) AS c"),
            t.min_tevents,
        )
        result.add_check(
            "TIMEX nodes",
            self._count("MATCH (n:TIMEX) RETURN count(n) AS c"),
            t.min_timex,
        )
        result.add_check(
            "Signal nodes",
            self._count("MATCH (n:Signal) RETURN count(n) AS c"),
            t.min_signals,
        )
        self._add_upper_bound_check(
            result,
            label="TEvent nodes missing core TimeML fields",
            actual=self._count(
                """
                MATCH (e:TEvent)
                WHERE e.eid IS NULL
                   OR e.tense IS NULL
                   OR e.aspect IS NULL
                   OR e.polarity IS NULL
                   OR e.pos IS NULL
                RETURN count(e) AS c
                """
            ),
            maximum=t.max_tevents_missing_timeml_core,
        )
        self._add_upper_bound_check(
            result,
            label="TIMEX nodes missing core TimeML fields",
            actual=self._count(
                """
                MATCH (x:TIMEX)
                WHERE x.tid IS NULL
                   OR x.type IS NULL
                   OR x.value IS NULL
                RETURN count(x) AS c
                """
            ),
            maximum=t.max_timex_missing_timeml_core,
        )
        self._add_upper_bound_check(
            result,
            label="Signal nodes missing text/span fields",
            actual=self._count(
                """
                MATCH (s:Signal)
                WHERE s.text IS NULL
                   OR s.start_tok IS NULL
                   OR s.end_tok IS NULL
                RETURN count(s) AS c
                """
            ),
            maximum=t.max_signals_missing_text_span,
        )
        self._add_upper_bound_check(
            result,
            label="TLINK relationships missing relTypeCanonical",
            actual=self._count(
                """
                MATCH ()-[r:TLINK]->()
                WHERE r.relTypeCanonical IS NULL
                RETURN count(r) AS c
                """
            ),
            maximum=t.max_tlinks_missing_reltype_canonical,
        )
        if self._enforce_provenance_contracts:
            self._add_provenance_contract_check(
                result,
                rel_type="TLINK",
                label="TLINK relationships missing provenance contract fields",
            )

        return self._finalize(result)

    def after_event_enrichment(self) -> AssertionResult:
        """Assert graph state expected after the event enrichment phase."""
        t = self._thresholds
        result = AssertionResult(phase="event_enrichment", passed=True)

        legacy_describes = self._count("MATCH ()-[r:DESCRIBES]->() RETURN count(r) AS c")
        canonical_describes = self._count(
            "MATCH ()-[r:FRAME_DESCRIBES_EVENT]->() RETURN count(r) AS c"
        )
        legacy_participant = self._count(
            """
            MATCH ()-[r:PARTICIPANT]->(t)
            WHERE t:TEvent OR t:EventMention
            RETURN count(r) AS c
            """
        )
        canonical_participant = self._count(
            "MATCH ()-[r:EVENT_PARTICIPANT]->() RETURN count(r) AS c"
        )

        result.add_check(
            "DESCRIBES relationships (Frame->TEvent)",
            legacy_describes,
            t.min_describes_rels,
        )
        result.add_check(
            "PARTICIPANT relationships",
            legacy_participant,
            t.min_participant_rels,
        )
        result.add_check(
            "FRAME_DESCRIBES_EVENT relationships",
            canonical_describes,
            t.min_frame_describes_event_rels,
        )
        has_frame_arguments = self._count(
            "MATCH ()-[r:HAS_FRAME_ARGUMENT]->() RETURN count(r) AS c"
        )
        result.add_check(
            "HAS_FRAME_ARGUMENT relationships",
            has_frame_arguments,
            t.min_has_frame_argument_rels,
        )
        result.add_check(
            "EVENT_PARTICIPANT relationships",
            canonical_participant,
            t.min_event_participant_rels,
        )
        # Transition telemetry: always-pass checks that expose legacy/canonical balance.
        result.add_check(
            "Telemetry: Frame->TEvent canonical minus legacy",
            canonical_describes - legacy_describes,
            -10**9,
        )
        result.add_check(
            "Telemetry: Participant canonical minus legacy",
            canonical_participant - legacy_participant,
            -10**9,
        )
        describes_ratio = (
            (legacy_describes / canonical_describes)
            if canonical_describes > 0
            else (inf if legacy_describes > 0 else 0.0)
        )
        participant_ratio = (
            (legacy_participant / canonical_participant)
            if canonical_participant > 0
            else (inf if legacy_participant > 0 else 0.0)
        )
        self._add_upper_bound_check(
            result,
            label="Legacy-to-canonical DESCRIBES ratio",
            actual=describes_ratio,
            maximum=t.max_legacy_to_canonical_describes_ratio,
        )
        self._add_upper_bound_check(
            result,
            label="Legacy-to-canonical PARTICIPANT ratio",
            actual=participant_ratio,
            maximum=t.max_legacy_to_canonical_participant_ratio,
        )
        participants_per_event = (
            (canonical_participant / canonical_describes)
            if canonical_describes > 0
            else (inf if canonical_participant > 0 else 0.0)
        )
        frame_args_per_event = (
            (has_frame_arguments / canonical_describes)
            if canonical_describes > 0
            else (inf if has_frame_arguments > 0 else 0.0)
        )
        self._add_upper_bound_check(
            result,
            label="Cost-model: EVENT_PARTICIPANT per described event",
            actual=participants_per_event,
            maximum=t.max_event_participants_per_described_event,
        )
        self._add_upper_bound_check(
            result,
            label="Cost-model: HAS_FRAME_ARGUMENT per described event",
            actual=frame_args_per_event,
            maximum=t.max_frame_arguments_per_described_event,
        )
        if legacy_describes > canonical_describes:
            logger.warning(
                "[phase-assert] legacy DESCRIBES edges dominate canonical FRAME_DESCRIBES_EVENT edges (%d > %d)",
                legacy_describes,
                canonical_describes,
            )
            if self._strict_transition_gate:
                result.errors.append(
                    "[event_enrichment] strict transition gate failed: "
                    f"legacy DESCRIBES edges dominate canonical FRAME_DESCRIBES_EVENT edges "
                    f"({legacy_describes} > {canonical_describes})"
                )
                result.passed = False
        if legacy_participant > canonical_participant:
            logger.warning(
                "[phase-assert] legacy PARTICIPANT edges dominate canonical EVENT_PARTICIPANT edges (%d > %d)",
                legacy_participant,
                canonical_participant,
            )
            if self._strict_transition_gate:
                result.errors.append(
                    "[event_enrichment] strict transition gate failed: "
                    f"legacy PARTICIPANT edges dominate canonical EVENT_PARTICIPANT edges "
                    f"({legacy_participant} > {canonical_participant})"
                )
                result.passed = False
        result.add_check(
            "CLINK relationships",
            self._count("MATCH ()-[r:CLINK]->() RETURN count(r) AS c"),
            t.min_clink_rels,
        )
        result.add_check(
            "SLINK relationships",
            self._count("MATCH ()-[r:SLINK]->() RETURN count(r) AS c"),
            t.min_slink_rels,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (EVENT_PARTICIPANT)",
            actual=count_endpoint_violations(self._graph, "EVENT_PARTICIPANT"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (INSTANTIATES)",
            actual=count_endpoint_violations(self._graph, "INSTANTIATES"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (HAS_FRAME_ARGUMENT)",
            actual=count_endpoint_violations(self._graph, "HAS_FRAME_ARGUMENT"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (FRAME_DESCRIBES_EVENT)",
            actual=count_endpoint_violations(self._graph, "FRAME_DESCRIBES_EVENT"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (REFERS_TO)",
            actual=count_endpoint_violations(self._graph, "REFERS_TO"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (MODIFIES)",
            actual=count_endpoint_violations(self._graph, "MODIFIES"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (AFFECTS)",
            actual=count_endpoint_violations(self._graph, "AFFECTS"),
            maximum=t.max_event_endpoint_contract_violations,
        )
        if self._enforce_provenance_contracts:
            self._add_provenance_contract_check(
                result,
                rel_type="DESCRIBES",
                label="DESCRIBES relationships missing provenance contract fields",
            )
            self._add_provenance_contract_check(
                result,
                rel_type="FRAME_DESCRIBES_EVENT",
                label="FRAME_DESCRIBES_EVENT relationships missing provenance contract fields",
            )
            self._add_provenance_contract_check(
                result,
                rel_type="PARTICIPANT",
                label="PARTICIPANT relationships missing provenance contract fields",
            )
            self._add_provenance_contract_check(
                result,
                rel_type="EVENT_PARTICIPANT",
                label="EVENT_PARTICIPANT relationships missing provenance contract fields",
            )
            self._add_provenance_contract_check(
                result,
                rel_type="MODIFIES",
                label="MODIFIES relationships missing provenance contract fields",
            )
            self._add_provenance_contract_check(
                result,
                rel_type="AFFECTS",
                label="AFFECTS relationships missing provenance contract fields",
            )

        return self._finalize(result)

    def after_tlinks(self) -> AssertionResult:
        """Assert graph state expected after the TLINK recognition phase."""
        t = self._thresholds
        result = AssertionResult(phase="tlinks", passed=True)

        result.add_check(
            "TLINK relationships",
            self._count("MATCH ()-[r:TLINK]->() RETURN count(r) AS c"),
            t.min_tlink_rels,
        )
        self._add_upper_bound_check(
            result,
            label="Cost-model: TLINK relationships upper bound",
            actual=result.checks[-1]["actual"],
            maximum=t.max_tlink_rels,
        )
        self._add_upper_bound_check(
            result,
            label="Unsuppressed contradictory TLINK pairs",
            actual=self._count(
                """
                MATCH (a)-[r1:TLINK]->(b), (a)-[r2:TLINK]->(b)
                WHERE id(r1) < id(r2)
                  AND coalesce(r1.suppressed, false) = false
                  AND coalesce(r2.suppressed, false) = false
                WITH coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE') AS rel1,
                     coalesce(r2.relTypeCanonical, r2.relType, 'VAGUE') AS rel2
                WHERE (rel1 = 'BEFORE' AND rel2 = 'AFTER')
                   OR (rel1 = 'AFTER' AND rel2 = 'BEFORE')
                   OR (rel1 = 'INCLUDES' AND rel2 = 'IS_INCLUDED')
                   OR (rel1 = 'IS_INCLUDED' AND rel2 = 'INCLUDES')
                   OR (rel1 = 'BEGINS' AND rel2 = 'BEGUN_BY')
                   OR (rel1 = 'BEGUN_BY' AND rel2 = 'BEGINS')
                   OR (rel1 = 'ENDS' AND rel2 = 'ENDED_BY')
                   OR (rel1 = 'ENDED_BY' AND rel2 = 'ENDS')
                RETURN count(*) AS c
                """
            ),
            maximum=t.max_tlink_consistency_violations,
        )
        self._add_upper_bound_check(
            result,
            label="Endpoint contract violations (TLINK)",
            actual=count_endpoint_violations(self._graph, "TLINK"),
            maximum=t.max_tlink_endpoint_contract_violations,
        )
        if self._enforce_provenance_contracts:
            self._add_provenance_contract_check(
                result,
                rel_type="TLINK",
                label="TLINK relationships missing provenance contract fields",
            )

        return self._finalize(result)


# ---------------------------------------------------------------------------
# Phase run markers (Item 7)
# ---------------------------------------------------------------------------


def record_phase_run(
    graph: Any,
    phase_name: str,
    duration_seconds: float,
    documents_processed: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Write a ``PhaseRun`` marker node to Neo4j for restart visibility.

    The node is MERGE-d by a timestamp-based ID so repeated calls produce
    distinct audit records rather than overwriting.  Failures are logged but
    never re-raised, so a broken graph connection cannot block the pipeline.

    Parameters
    ----------
    graph :
        Neo4j graph connection; must expose ``.run(cypher, params).data()``.
    phase_name :
        Short canonical phase name, e.g. ``"ingestion"``.
    duration_seconds :
        Wall-clock seconds the phase took.
    documents_processed :
        Number of documents handled (0 when unknown).
    metadata :
        Any extra key/value pairs to store on the marker node.
    """
    try:
        run_id = utc_iso_now()
        props: Dict[str, Any] = {
            "phase": phase_name,
            "timestamp": run_id,
            "duration_seconds": round(duration_seconds, 3),
            "documents_processed": documents_processed,
        }
        if metadata:
            props.update({f"meta_{k}": str(v) for k, v in metadata.items()})

        cypher = """
        MERGE (r:PhaseRun {id: $id})
        SET r += $props
        RETURN id(r) AS node_id
        """
        graph.run(cypher, {"id": run_id, "props": props}).data()
        logger.info(
            "Recorded PhaseRun marker for '%s' (id=%s, %.2fs, %d docs)",
            phase_name,
            run_id,
            duration_seconds,
            documents_processed,
        )
    except Exception:
        logger.exception(
            "Failed to write PhaseRun marker for '%s' (non-fatal)", phase_name
        )
