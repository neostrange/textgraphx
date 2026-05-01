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
class SRLKGQualityReport:
    doc_id: Optional[str]
    coverage: FrameCoverageMetrics = field(default_factory=FrameCoverageMetrics)
    density: ArgumentDensityMetrics = field(default_factory=ArgumentDensityMetrics)
    calibration: ConfidenceCalibrationMetrics = field(
        default_factory=ConfidenceCalibrationMetrics
    )
    aligns_with_count: int = 0


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
