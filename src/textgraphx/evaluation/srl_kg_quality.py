"""
SRL knowledge-graph quality evaluator.

Computes three quality dimensions over the Frame / FrameArgument sub-graph:

1. **Frame coverage** — average number of Frame nodes per sentence.
2. **Argument density** — average number of FrameArgument nodes per Frame.
3. **Confidence calibration** — distribution of sense_conf values and provisional
   frame rate.

All metrics are schema-aware: they accept a Neo4j graph cursor and a ``doc_id``
scope parameter so that per-document or corpus-level aggregation is supported.

Usage
-----
>>> from textgraphx.evaluation.srl_kg_quality import SRLKGQualityEvaluator
>>> metrics = SRLKGQualityEvaluator(graph).evaluate(doc_id="myDoc")
>>> print(metrics)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FrameCoverageMetrics:
    """Frame coverage per sentence."""
    total_sentences: int = 0
    total_frames: int = 0
    propbank_frames: int = 0
    nombank_frames: int = 0
    frames_per_sentence: float = 0.0


@dataclass
class ArgumentDensityMetrics:
    """Argument density per frame."""
    total_frames: int = 0
    total_arguments: int = 0
    args_per_frame: float = 0.0


@dataclass
class ConfidenceCalibrationMetrics:
    """Confidence distribution and provisional rate."""
    total_frames_with_conf: int = 0
    provisional_frames: int = 0
    provisional_rate: float = 0.0
    mean_confidence: float = 0.0
    # Histogram buckets: [0.0-0.5), [0.5-0.7), [0.7-0.9), [0.9-1.0]
    confidence_histogram: Dict[str, int] = field(default_factory=dict)


@dataclass
class TemporalAnchoringMetrics:
    """Quality of the SRL → canonical TIMEX → TLINK anchoring pipeline."""
    srl_timex_candidates_created: int = 0
    srl_timex_promoted_to_canonical: int = 0
    srl_timex_as_tlink_endpoint: int = 0
    nominal_events_with_srl_temporal_anchor: int = 0
    promotion_rate: float = 0.0
    tlink_yield_rate: float = 0.0
    # Step-12 HAS_TIME_ANCHOR diagnostics
    events_with_time_anchor: int = 0
    anchored_events_as_tlink_endpoint: int = 0
    temporally_isolated_events: int = 0
    anchor_tlink_yield_rate: float = 0.0


@dataclass
class SRLKGQualityReport:
    doc_id: Optional[str]
    coverage: FrameCoverageMetrics = field(default_factory=FrameCoverageMetrics)
    density: ArgumentDensityMetrics = field(default_factory=ArgumentDensityMetrics)
    calibration: ConfidenceCalibrationMetrics = field(
        default_factory=ConfidenceCalibrationMetrics
    )
    aligns_with_count: int = 0
    temporal_anchoring: TemporalAnchoringMetrics = field(
        default_factory=TemporalAnchoringMetrics
    )


class SRLKGQualityEvaluator:
    """Evaluator for the SRL sub-graph quality.

    Parameters
    ----------
    graph:
        Graph connection with a ``.run(query, params)`` method.
    """

    def __init__(self, graph):
        self.graph = graph

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, doc_id: Optional[str] = None) -> SRLKGQualityReport:
        """Run all quality checks and return a consolidated report.

        Parameters
        ----------
        doc_id:
            Scope evaluation to a single document. Pass ``None`` to evaluate
            the entire graph (corpus-level).
        """
        report = SRLKGQualityReport(doc_id=doc_id)
        report.coverage = self._frame_coverage(doc_id)
        report.density = self._argument_density(doc_id)
        report.calibration = self._confidence_calibration(doc_id)
        report.aligns_with_count = self._aligns_with_count(doc_id)
        report.temporal_anchoring = self._temporal_anchoring(doc_id)
        return report

    # ------------------------------------------------------------------
    # Internal metric queries
    # ------------------------------------------------------------------

    def _frame_coverage(self, doc_id: Optional[str]) -> FrameCoverageMetrics:
        where = "WHERE at.id = $doc_id" if doc_id else ""
        params = {"doc_id": doc_id} if doc_id else {}

        q = f"""
        MATCH (at:AnnotatedText)-[:CONTAINS_SENTENCE]->(s:Sentence)
        {where}
        WITH count(s) AS total_sentences
        OPTIONAL MATCH (f:Frame)
        {"WHERE f.doc_id = $doc_id" if doc_id else ""}
        WITH total_sentences,
             count(f) AS total_frames,
             sum(CASE WHEN f.framework = 'PROPBANK' THEN 1 ELSE 0 END) AS propbank_frames,
             sum(CASE WHEN f.framework = 'NOMBANK'  THEN 1 ELSE 0 END) AS nombank_frames
        RETURN total_sentences, total_frames, propbank_frames, nombank_frames
        """
        try:
            row = self.graph.run(q, params).data()
            if row:
                r = row[0]
                total_s = r.get("total_sentences", 0) or 1
                total_f = r.get("total_frames", 0) or 0
                return FrameCoverageMetrics(
                    total_sentences=total_s,
                    total_frames=total_f,
                    propbank_frames=r.get("propbank_frames", 0) or 0,
                    nombank_frames=r.get("nombank_frames", 0) or 0,
                    frames_per_sentence=total_f / total_s,
                )
        except Exception as exc:
            logger.warning("frame_coverage query failed: %s", exc)
        return FrameCoverageMetrics()

    def _argument_density(self, doc_id: Optional[str]) -> ArgumentDensityMetrics:
        where = "WHERE f.doc_id = $doc_id" if doc_id else ""
        params = {"doc_id": doc_id} if doc_id else {}

        q = f"""
        MATCH (f:Frame) {where}
        OPTIONAL MATCH (f)-[:HAS_FRAME_ARGUMENT|PARTICIPANT*1..1]->(fa:FrameArgument)
        WITH count(DISTINCT f) AS total_frames, count(DISTINCT fa) AS total_arguments
        RETURN total_frames, total_arguments
        """
        try:
            row = self.graph.run(q, params).data()
            if row:
                r = row[0]
                total_f = r.get("total_frames", 0) or 1
                total_a = r.get("total_arguments", 0) or 0
                return ArgumentDensityMetrics(
                    total_frames=total_f,
                    total_arguments=total_a,
                    args_per_frame=total_a / total_f,
                )
        except Exception as exc:
            logger.warning("argument_density query failed: %s", exc)
        return ArgumentDensityMetrics()

    def _confidence_calibration(self, doc_id: Optional[str]) -> ConfidenceCalibrationMetrics:
        where = "WHERE f.sense_conf IS NOT NULL" + (
            " AND f.doc_id = $doc_id" if doc_id else ""
        )
        params = {"doc_id": doc_id} if doc_id else {}

        q = f"""
        MATCH (f:Frame) {where}
        RETURN f.sense_conf AS conf, f.provisional AS provisional
        """
        try:
            rows = self.graph.run(q, params).data()
        except Exception as exc:
            logger.warning("confidence_calibration query failed: %s", exc)
            return ConfidenceCalibrationMetrics()

        if not rows:
            return ConfidenceCalibrationMetrics()

        confs: List[float] = []
        provisional_count = 0
        buckets = {"[0.0,0.5)": 0, "[0.5,0.7)": 0, "[0.7,0.9)": 0, "[0.9,1.0]": 0}
        for row in rows:
            c = row.get("conf")
            if c is None:
                continue
            c = float(c)
            confs.append(c)
            if row.get("provisional"):
                provisional_count += 1
            if c < 0.5:
                buckets["[0.0,0.5)"] += 1
            elif c < 0.7:
                buckets["[0.5,0.7)"] += 1
            elif c < 0.9:
                buckets["[0.7,0.9)"] += 1
            else:
                buckets["[0.9,1.0]"] += 1

        n = len(confs)
        mean_conf = sum(confs) / n if n else 0.0
        return ConfidenceCalibrationMetrics(
            total_frames_with_conf=n,
            provisional_frames=provisional_count,
            provisional_rate=provisional_count / n if n else 0.0,
            mean_confidence=mean_conf,
            confidence_histogram=buckets,
        )

    def _aligns_with_count(self, doc_id: Optional[str]) -> int:
        where = "WHERE r.confidence IS NOT NULL" + (
            " AND (vf.doc_id = $doc_id OR nf.doc_id = $doc_id)" if doc_id else ""
        )
        params = {"doc_id": doc_id} if doc_id else {}

        q = f"""
        MATCH (vf:Frame)-[r:ALIGNS_WITH]->(nf:Frame)
        {where}
        RETURN count(r) AS cnt
        """
        try:
            row = self.graph.run(q, params).data()
            return (row[0].get("cnt", 0) or 0) if row else 0
        except Exception as exc:
            logger.warning("aligns_with_count query failed: %s", exc)
            return 0

    def _temporal_anchoring(self, doc_id: Optional[str]) -> TemporalAnchoringMetrics:
        """Measure how well SRL ARGM-TMP candidates flow into canonical TIMEXs and TLINKs."""
        doc_filter = "AND tm.doc_id = toInteger($doc_id)" if doc_id else ""
        params = {"doc_id": doc_id} if doc_id else {}

        # Count all SRLTimexCandidate mentions
        q_candidates = f"""
        MATCH (tm:TimexMention:SRLTimexCandidate)
        WHERE 1=1 {doc_filter}
        RETURN count(tm) AS total
        """
        # Count those that have a REFERS_TO → TIMEX bridge
        q_promoted = f"""
        MATCH (tm:TimexMention:SRLTimexCandidate)-[:REFERS_TO]->(t:TIMEX)
        WHERE 1=1 {doc_filter}
        RETURN count(DISTINCT t) AS total
        """
        # Count canonical TIMEXs (reached from SRL candidates) that appear as TLINK endpoints
        q_tlink_endpoint = f"""
        MATCH (tm:TimexMention:SRLTimexCandidate)-[:REFERS_TO]->(t:TIMEX)
        WHERE 1=1 {doc_filter}
        WITH DISTINCT t
        MATCH ()-[:TLINK]->(t)
        RETURN count(DISTINCT t) AS total
        """
        # Count nominal TEvents (source='nombank_srl') that have at least one TLINK to an SRL-derived TIMEX
        q_nominal_anchored = f"""
        MATCH (tm:TimexMention:SRLTimexCandidate)-[:REFERS_TO]->(t:TIMEX)
        WHERE 1=1 {doc_filter}
        WITH DISTINCT t
        MATCH (e:TEvent {{source: 'nombank_srl'}})-[:TLINK]->(t)
        RETURN count(DISTINCT e) AS total
        """

        def _fetch(query: str) -> int:
            try:
                row = self.graph.run(query, params).data()
                return (row[0].get("total", 0) or 0) if row else 0
            except Exception as exc:
                logger.warning("temporal_anchoring sub-query failed: %s", exc)
                return 0

        candidates = _fetch(q_candidates)
        promoted = _fetch(q_promoted)
        tlink_ep = _fetch(q_tlink_endpoint)
        nominal_anchored = _fetch(q_nominal_anchored)

        promotion_rate = promoted / candidates if candidates else 0.0
        tlink_yield = tlink_ep / promoted if promoted else 0.0

        # --- Step-12 HAS_TIME_ANCHOR diagnostics ---
        doc_filter_e = "AND e.doc_id = toInteger($doc_id)" if doc_id else ""

        # TEvents that carry at least one HAS_TIME_ANCHOR edge (from step 10)
        q_anchored = f"""
        MATCH (e:TEvent)-[:HAS_TIME_ANCHOR]->(:TimexMention:SRLTimexCandidate)
        WHERE coalesce(e.merged, false) = false {doc_filter_e}
        RETURN count(DISTINCT e) AS total
        """
        # Of those, how many are already an endpoint of at least one TLINK
        q_anchor_tlink = f"""
        MATCH (e:TEvent)-[:HAS_TIME_ANCHOR]->(:TimexMention:SRLTimexCandidate)
        WHERE coalesce(e.merged, false) = false {doc_filter_e}
        WITH DISTINCT e
        MATCH (e)-[:TLINK]->()
        RETURN count(DISTINCT e) AS total
        """
        # Canonical non-merged TEvents with no TLINK and no HAS_TIME_ANCHOR (temporally isolated)
        q_isolated = f"""
        MATCH (e:TEvent)
        WHERE coalesce(e.merged, false) = false
          AND coalesce(e.low_confidence, false) = false
          AND coalesce(e.is_timeml_core, true) = true
          {doc_filter_e}
          AND NOT EXISTS {{ MATCH (e)-[:HAS_TIME_ANCHOR]->() }}
          AND NOT EXISTS {{ MATCH (e)-[:TLINK]->() }}
          AND NOT EXISTS {{ MATCH ()-[:TLINK]->(e) }}
        RETURN count(e) AS total
        """

        events_with_anchor = _fetch(q_anchored)
        anchor_tlink_ep = _fetch(q_anchor_tlink)
        isolated = _fetch(q_isolated)
        anchor_tlink_yield = anchor_tlink_ep / events_with_anchor if events_with_anchor else 0.0

        return TemporalAnchoringMetrics(
            srl_timex_candidates_created=candidates,
            srl_timex_promoted_to_canonical=promoted,
            srl_timex_as_tlink_endpoint=tlink_ep,
            nominal_events_with_srl_temporal_anchor=nominal_anchored,
            promotion_rate=promotion_rate,
            tlink_yield_rate=tlink_yield,
            events_with_time_anchor=events_with_anchor,
            anchored_events_as_tlink_endpoint=anchor_tlink_ep,
            temporally_isolated_events=isolated,
            anchor_tlink_yield_rate=anchor_tlink_yield,
        )
