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
from typing import Any, Dict, List, Optional

from textgraphx.time_utils import utc_iso_now

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

    # --- temporal ---
    min_tevents: int = 0                      # TEvent nodes (0: temporal service optional)
    min_timex: int = 0                        # TIMEX nodes
    min_signals: int = 0                      # Signal nodes

    # --- event_enrichment ---
    min_describes_rels: int = 0              # DESCRIBES relationships (Frame->TEvent)
    min_participant_rels: int = 0            # PARTICIPANT relationships
    min_frame_describes_event_rels: int = 0  # FRAME_DESCRIBES_EVENT relationships
    min_has_frame_argument_rels: int = 0     # HAS_FRAME_ARGUMENT relationships
    min_event_participant_rels: int = 0      # EVENT_PARTICIPANT relationships
    min_clink_rels: int = 0                  # CLINK relationships
    min_slink_rels: int = 0                  # SLINK relationships

    # --- tlinks ---
    min_tlink_rels: int = 0                  # TLINK relationships


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
            logger.debug(
                "  %s %s: %s (min %s)", sym, c["label"], c["actual"], c["minimum"]
            )
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
    ) -> None:
        self._graph = graph
        self._thresholds = thresholds or PhaseThresholds()
        self._hard_fail = hard_fail
        self._strict_transition_gate = strict_transition_gate

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
        result.add_check(
            "HAS_FRAME_ARGUMENT relationships",
            self._count("MATCH ()-[r:HAS_FRAME_ARGUMENT]->() RETURN count(r) AS c"),
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
