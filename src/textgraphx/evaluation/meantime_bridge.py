"""Milestone 8a: MEANTIME Bridge - Unified Integration with External Gold Standards.

Bridges the unified evaluation framework (M1-M7) with the existing MEANTIME
evaluator to produce consolidated quality reports combining:
  - Phase-level quality metrics (M1-M7 EvaluationSuite)
  - Gold-standard task accuracy (MEANTIME PRF)
  - Cross-paradigm consistency checking

Provides:
  - MEANTIMEBridge: Adapter connecting M1-M7 suite to MEANTIME evaluation
  - ConsolidatedQualityReport: Combined metrics from both paradigms
  - Quality scoring that weights structural soundness + task accuracy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import warnings

from textgraphx.evaluation.fullstack_harness import EvaluationSuite
from textgraphx.evaluation.meantime_evaluator import (
    NormalizedDocument,
    parse_meantime_xml,
    build_document_from_neo4j,
    EvaluationMapping,
    score_mention_layer,
    score_relation_layer,
)
from textgraphx.evaluation.metrics import precision_recall_f1, macro_average
from textgraphx.evaluation.report_validity import RunMetadata

try:
    from textgraphx.evaluation.srl_kg_quality import (
        SRLKGQualityEvaluator,
        SRLKGQualityReport,
    )
    _SRL_QUALITY_AVAILABLE = True
except ImportError:
    _SRL_QUALITY_AVAILABLE = False
    SRLKGQualityReport = None  # type: ignore[assignment,misc]


def _safe_div(num: float, den: float) -> float:
    """Return num/den with safe zero-denominator fallback."""
    return float(num) / float(den) if den else 0.0


@dataclass(frozen=True)
class LayerScores:
    """Precision/Recall/F1 scores for a single layer (entity/event/timex/relation)."""

    layer_name: str
    strict_mode: bool
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    sample_size: int = 0

    @classmethod
    def from_prf_dict(cls, layer_name: str, strict: bool, prf_dict: Dict[str, Any]) -> LayerScores:
        """Create from precision_recall_f1 output dict."""
        return cls(
            layer_name=layer_name,
            strict_mode=strict,
            tp=int(prf_dict.get("tp", 0)),
            fp=int(prf_dict.get("fp", 0)),
            fn=int(prf_dict.get("fn", 0)),
            precision=float(prf_dict.get("precision", 0.0)),
            recall=float(prf_dict.get("recall", 0.0)),
            f1=float(prf_dict.get("f1", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "layer": self.layer_name,
            "strict_mode": self.strict_mode,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "sample_size": self.sample_size,
        }


@dataclass
class MEANTIMEResults:
    """Aggregated MEANTIME evaluation results for a document."""

    doc_id: str
    entity_strict: LayerScores
    entity_relaxed: LayerScores
    event_strict: LayerScores
    event_relaxed: LayerScores
    timex_strict: LayerScores
    timex_relaxed: LayerScores
    relation_scores: Dict[str, LayerScores] = field(default_factory=dict)
    mode: str = "hybrid"  # 'strict', 'relaxed', or 'hybrid'
    evaluation_note: str = ""
    gold_document: Optional[NormalizedDocument] = None
    predicted_document: Optional[NormalizedDocument] = None
    # Step-16: optional SRL KG quality diagnostics attached at evaluation time
    srl_diagnostics: Optional[Any] = field(default=None, compare=False)

    def macro_layer_f1(self, mode: str = "relaxed") -> Dict[str, float]:
        """Macro-average F1 across layers excluding relations."""
        layers = [
            self.entity_relaxed if mode == "relaxed" else self.entity_strict,
            self.event_relaxed if mode == "relaxed" else self.event_strict,
            self.timex_relaxed if mode == "relaxed" else self.timex_strict,
        ]
        scores = [l.f1 for l in layers if l.f1 >= 0]
        if not scores:
            return {"macro_f1": 0.0, "count": 0}
        return {
            "macro_f1": sum(scores) / len(scores),
            "count": len(scores),
        }

    def macro_all_f1(self, mode: str = "relaxed") -> float:
        """F1 averaged across entity/event/timex/relation layers."""
        layers = []
        if mode == "relaxed":
            layers.extend([self.entity_relaxed, self.event_relaxed, self.timex_relaxed])
        else:
            layers.extend([self.entity_strict, self.event_strict, self.timex_strict])
        layers.extend(self.relation_scores.values())

        scores = [l.f1 for l in layers if l.f1 >= 0]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "doc_id": self.doc_id,
            "mode": self.mode,
            "mention_layers": {
                "entity": {
                    "strict": self.entity_strict.to_dict(),
                    "relaxed": self.entity_relaxed.to_dict(),
                },
                "event": {
                    "strict": self.event_strict.to_dict(),
                    "relaxed": self.event_relaxed.to_dict(),
                },
                "timex": {
                    "strict": self.timex_strict.to_dict(),
                    "relaxed": self.timex_relaxed.to_dict(),
                },
            },
            "relations": {rtype: scores.to_dict() for rtype, scores in self.relation_scores.items()},
            "macro_f1": {
                "layers_only": self.macro_layer_f1(mode="relaxed"),
                "all_including_relations": self.macro_all_f1(mode="relaxed"),
            },
            "evaluation_note": self.evaluation_note,
            # Step-15 diagnostic: gold events with no projected match
            "unmatched_gold_events": (
                self.predicted_document.unmatched_gold_events
                if self.predicted_document is not None
                else 0
            ),
            # Step-16: SRL diagnostics attached at evaluation time (may be absent)
            "srl_diagnostics": (
                self._srl_diagnostics_inline()
                if self.srl_diagnostics is not None
                else None
            ),
        }

    def _srl_diagnostics_inline(self) -> Dict[str, Any]:
        """Serialize srl_diagnostics to a plain dict (used by to_dict())."""
        try:
            from dataclasses import asdict
            return asdict(self.srl_diagnostics)
        except Exception:
            return {}


@dataclass
class ConsolidatedQualityReport:
    """Combined evaluation report: phase quality + MEANTIME gold-standard validation."""

    run_metadata: RunMetadata
    evaluation_suite: EvaluationSuite
    meantime_results: MEANTIMEResults
    consolidation_mode: str = "weighted_average"  # 'strict', 'relaxed', 'weighted_average'

    # Consolidation parameters
    weight_phase_quality: float = 0.40  # Phase-level structural quality
    weight_meantime_f1: float = 0.40    # Gold-standard task accuracy
    weight_consistency: float = 0.20    # Cross-layer consistency

    # Step-16: optional SRL KG quality diagnostics
    srl_diagnostics: Optional[Any] = field(default=None, compare=False)

    def phase_quality_score(self) -> float:
        """Quality from M1-M7 evaluation suite (macro-average of all phases)."""
        return self.evaluation_suite.overall_quality()

    def meantime_quality_score(self, mode: str = "relaxed") -> float:
        """Quality from MEANTIME comparison (macro F1 across layers)."""
        return self.meantime_results.macro_all_f1(mode=mode)

    def consistency_score(self) -> float:
        """Cross-layer consistency check: how well do phase reports correlate with MEANTIME?

        Simple heuristic: if phases report high quality but MEANTIME shows low F1,
        consistency is low. If they agree, consistency is high.
        """
        phase_quality = self.phase_quality_score()
        meantime_quality = self.meantime_quality_score()

        # If both high or both low, consistency is good
        # If divergent, consistency is reduced
        delta = abs(phase_quality - meantime_quality)
        consistency = max(0.0, 1.0 - delta)  # Linear penalty for divergence
        return consistency

    def overall_quality(self) -> float:
        """Consolidated quality score combining all three dimensions."""
        phase = self.phase_quality_score() * self.weight_phase_quality
        meantime = self.meantime_quality_score() * self.weight_meantime_f1
        consistency = self.consistency_score() * self.weight_consistency

        return phase + meantime + consistency

    def quality_tier(self) -> str:
        """Assign quality tier based on consolidated score."""
        score = self.overall_quality()
        if score >= 0.90:
            return "PRODUCTION_READY"
        elif score >= 0.80:
            return "ACCEPTABLE"
        elif score >= 0.70:
            return "NEEDS_WORK"
        else:
            return "RESEARCH_PHASE"

    def passed_quality_gate(self, threshold: float = 0.80) -> bool:
        """Check if consolidated quality meets gate threshold."""
        return self.overall_quality() >= threshold

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON export."""
        timestamp = self.run_metadata.timestamp
        if hasattr(timestamp, 'isoformat'):
            timestamp_str = timestamp.isoformat()
        else:
            timestamp_str = str(timestamp)
        
        return {
            "timestamp": timestamp_str,
            "run_metadata": self.run_metadata.to_dict(),
            "evaluation_dimensions": {
                "phase_structure": {
                    "score": self.phase_quality_score(),
                    "weight": self.weight_phase_quality,
                    "description": "M1-M7 phase evaluation quality (reproducibility, determinism, feature activation)",
                },
                "gold_standard_accuracy": {
                    "score": self.meantime_quality_score(),
                    "weight": self.weight_meantime_f1,
                    "description": "MEANTIME PRF against gold XML (entity/event/timex/relation)",
                },
                "cross_layer_consistency": {
                    "score": self.consistency_score(),
                    "weight": self.weight_consistency,
                    "description": "Agreement between phase quality and MEANTIME accuracy",
                },
            },
            "consolidated_quality": {
                "score": self.overall_quality(),
                "tier": self.quality_tier(),
                "passed_gate": self.passed_quality_gate(),
            },
            "phase_suite": self.evaluation_suite.to_dict(),
            "meantime_validation": self.meantime_results.to_dict(),
            "srl_diagnostics": self._srl_diagnostics_dict(),
        }

    def to_markdown(self) -> str:
        """Generate rich markdown report with consolidated results."""
        timestamp = self.run_metadata.timestamp
        if hasattr(timestamp, 'isoformat'):
            timestamp_str = timestamp.isoformat()
        else:
            timestamp_str = str(timestamp)
        
        lines = [
            "# Consolidated Evaluation Report",
            "",
            f"**Report Generated**: {timestamp_str}",
            f"**Pipeline Config Hash**: `{self.run_metadata.config_hash}`",
            f"**Dataset Hash**: `{self.run_metadata.dataset_hash}`",
            "",
            "## 📊 Consolidated Quality Assessment",
            "",
        ]

        # Overall score card
        overall = self.overall_quality()
        tier = self.quality_tier()
        lines.extend([
            f"| Metric | Score | Status |",
            f"|--------|-------|--------|",
            f"| **Overall Quality** | `{overall:.4f}` | **{tier}** |",
            f"| Phase Structure (M1-M7) | `{self.phase_quality_score():.4f}` | {self._score_badge(self.phase_quality_score())} |",
            f"| Gold-Standard Accuracy | `{self.meantime_quality_score():.4f}` | {self._score_badge(self.meantime_quality_score())} |",
            f"| Cross-Layer Consistency | `{self.consistency_score():.4f}` | {self._score_badge(self.consistency_score())} |",
            "",
        ])

        # Detailed breakdown
        lines.extend([
            "## 🔬 Detailed Breakdown",
            "",
            "### Phase-Level Quality (M1-M7)",
            "",
        ])
        phase_scores = self.evaluation_suite.quality_scores()
        for phase_name, score in phase_scores.items():
            lines.append(f"- **{phase_name}**: `{score:.4f}` {self._score_badge(score)}")
        lines.append("")

        # MEANTIME results
        lines.extend([
            "### Gold-Standard Validation (MEANTIME)",
            "",
            "#### Mention Layer Accuracy (Relaxed Mode)",
            "",
            f"| Layer | Precision | Recall | F1 |",
            f"|-------|-----------|--------|-----|",
            f"| Entity | `{self.meantime_results.entity_relaxed.precision:.4f}` | `{self.meantime_results.entity_relaxed.recall:.4f}` | `{self.meantime_results.entity_relaxed.f1:.4f}` |",
            f"| Event | `{self.meantime_results.event_relaxed.precision:.4f}` | `{self.meantime_results.event_relaxed.recall:.4f}` | `{self.meantime_results.event_relaxed.f1:.4f}` |",
            f"| Temporal Expression | `{self.meantime_results.timex_relaxed.precision:.4f}` | `{self.meantime_results.timex_relaxed.recall:.4f}` | `{self.meantime_results.timex_relaxed.f1:.4f}` |",
            "",
        ])

        # Quality gate
        gate_status = "✅ PASS" if self.passed_quality_gate() else "❌ FAIL"
        lines.extend([
            f"## ✅ Quality Gate Assessment",
            "",
            f"**Status**: {gate_status}",
            f"**Required Threshold**: 0.80",
            f"**Actual Score**: `{overall:.4f}`",
            "",
        ])

        # Conclusiveness
        is_conclusive, reasons = self.evaluation_suite.conclusiveness()
        conclusive_str = "✅ Conclusive" if is_conclusive else "⚠️ Inconclusive"
        lines.extend([
            f"## 📋 Evaluation Conclusiveness",
            "",
            f"**Status**: {conclusive_str}",
        ])
        if reasons:
            lines.append("**Reasons for inconclusiveness**:")
            for reason in reasons:
                lines.append(f"- {reason}")
        lines.append("")

        # Step-16: SRL diagnostics section
        srl_dict = self._srl_diagnostics_dict()
        if srl_dict:
            ta = srl_dict.get("temporal_anchoring", {})
            lines.extend([
                "## 🔗 SRL Knowledge-Graph Diagnostics",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Frame coverage (frames/sentence) | `{srl_dict.get('coverage', {}).get('frames_per_sentence', 0.0):.3f}` |",
                f"| Argument density (args/frame) | `{srl_dict.get('density', {}).get('args_per_frame', 0.0):.3f}` |",
                f"| Provisional frame rate | `{srl_dict.get('calibration', {}).get('provisional_rate', 0.0):.3f}` |",
                f"| ALIGNS_WITH edges | `{srl_dict.get('aligns_with_count', 0)}` |",
                f"| SRL timex candidates created | `{ta.get('srl_timex_candidates_created', 0)}` |",
                f"| Nominal events with time anchor | `{ta.get('nominal_events_with_srl_temporal_anchor', 0)}` |",
                f"| Events with HAS_TIME_ANCHOR | `{ta.get('events_with_time_anchor', 0)}` |",
                f"| Anchor→TLINK yield | `{ta.get('anchor_tlink_yield_rate', 0.0):.3f}` |",
                f"| Temporally isolated events | `{ta.get('temporally_isolated_events', 0)}` |",
                "",
            ])

        return "\n".join(lines)

    def _srl_diagnostics_dict(self) -> Dict[str, Any]:
        """Serialize SRL diagnostics to a plain dict (empty if not present)."""
        if self.srl_diagnostics is None:
            return {}
        try:
            from dataclasses import asdict
            return asdict(self.srl_diagnostics)
        except Exception:
            return {}

    @staticmethod
    def _score_badge(score: float) -> str:
        """Generate markdown badge for score quality."""
        if score >= 0.90:
            return "🟢 Excellent"
        elif score >= 0.80:
            return "🟡 Good"
        elif score >= 0.70:
            return "🟠 Fair"
        else:
            return "🔴 Poor"


class MEANTIMEBridge:
    """Adapter bridging unified evaluation framework with MEANTIME gold-standard validation.

    Workflow:
      1. Initialize with gold XML path and evaluation mapping
      2. Pass UnifiedMetricReport suite from M1-M7 evaluation
      3. Extract document from Neo4j graph or XML
      4. Compare against gold standard
      5. Generate consolidated report combining both paradigms
    """

    def __init__(
        self,
        gold_xml_path: Path | str,
        evaluation_mapping: Optional[EvaluationMapping] = None,
        discourse_only: bool = False,
        normalize_nominal_boundaries: bool = True,
    ):
        """Initialize bridge with gold standard XML.

        Args:
            gold_xml_path: Path to MEANTIME-format gold annotation XML
            evaluation_mapping: Custom mention/relation attribute mapping (default: standard)
            discourse_only: If True, restrict entity evaluation to DiscourseEntity-labeled nodes
            normalize_nominal_boundaries: If True, normalize nominal entity spans for comparison
        """
        self.gold_xml_path = Path(gold_xml_path)
        self.evaluation_mapping = evaluation_mapping or EvaluationMapping()
        self.discourse_only = discourse_only
        self.normalize_nominal_boundaries = normalize_nominal_boundaries

        if not self.gold_xml_path.exists():
            raise FileNotFoundError(f"Gold XML not found: {self.gold_xml_path}")

        self.gold_document = parse_meantime_xml(str(self.gold_xml_path))

    def evaluate_from_neo4j(
        self,
        graph: Any,
        doc_id: int | str,
        gold_token_sequence: Optional[Tuple[Tuple[int, str], ...]] = None,
        run_srl_diagnostics: bool = False,
    ) -> MEANTIMEResults:
        """Evaluate Neo4j-projected document against gold standard.

        Args:
            graph: Neo4j driver or session
            doc_id: Document ID in Neo4j
            gold_token_sequence: Token sequence from gold XML (for alignment if needed)
            run_srl_diagnostics: If True, also compute SRL KG quality diagnostics and
                attach them to the returned MEANTIMEResults as ``srl_diagnostics``.

        Returns:
            MEANTIMEResults with strict/relaxed scores for all mention layers
        """
        predicted_document = build_document_from_neo4j(
            graph=graph,
            doc_id=doc_id,
            gold_token_sequence=gold_token_sequence,
            discourse_only=self.discourse_only,
            normalize_nominal_boundaries=self.normalize_nominal_boundaries,
        )
        results = self._score_documents(self.gold_document, predicted_document)

        if run_srl_diagnostics and _SRL_QUALITY_AVAILABLE:
            try:
                srl_report = SRLKGQualityEvaluator(graph).evaluate(doc_id=str(doc_id))
                results = MEANTIMEResults(
                    doc_id=results.doc_id,
                    entity_strict=results.entity_strict,
                    entity_relaxed=results.entity_relaxed,
                    event_strict=results.event_strict,
                    event_relaxed=results.event_relaxed,
                    timex_strict=results.timex_strict,
                    timex_relaxed=results.timex_relaxed,
                    relation_scores=results.relation_scores,
                    mode=results.mode,
                    evaluation_note=results.evaluation_note,
                    gold_document=results.gold_document,
                    predicted_document=results.predicted_document,
                    srl_diagnostics=srl_report,
                )
            except Exception:
                pass  # non-fatal: SRL diagnostics are advisory

        return results

    def evaluate_from_xml(
        self,
        predicted_xml_path: Path | str,
    ) -> MEANTIMEResults:
        """Evaluate XML-projected document against gold standard.

        Args:
            predicted_xml_path: Path to prediction XML in MEANTIME format

        Returns:
            MEANTIMEResults with strict/relaxed scores
        """
        predicted_document = parse_meantime_xml(str(predicted_xml_path))
        return self._score_documents(self.gold_document, predicted_document)

    def _score_documents(
        self,
        gold: NormalizedDocument,
        predicted: NormalizedDocument,
    ) -> MEANTIMEResults:
        """Compute strict/relaxed scores for all layers."""
        # Mention layers - strict mode
        entity_strict_dict = score_mention_layer(
            gold_mentions=gold.entity_mentions,
            predicted_mentions=predicted.entity_mentions,
            mode="strict",
            attr_keys=self.evaluation_mapping.mention_attr_keys.get("entity", ()),
        )
        # Mention layers - relaxed mode
        entity_relaxed_dict = score_mention_layer(
            gold_mentions=gold.entity_mentions,
            predicted_mentions=predicted.entity_mentions,
            mode="relaxed",
            attr_keys=self.evaluation_mapping.mention_attr_keys.get("entity", ()),
        )

        # Event mentions
        event_strict_dict = score_mention_layer(
            gold_mentions=gold.event_mentions,
            predicted_mentions=predicted.event_mentions,
            mode="strict",
            attr_keys=self.evaluation_mapping.mention_attr_keys.get("event", ()),
        )
        event_relaxed_dict = score_mention_layer(
            gold_mentions=gold.event_mentions,
            predicted_mentions=predicted.event_mentions,
            mode="relaxed",
            attr_keys=self.evaluation_mapping.mention_attr_keys.get("event", ()),
        )

        # Temporal expressions
        timex_strict_dict = score_mention_layer(
            gold_mentions=gold.timex_mentions,
            predicted_mentions=predicted.timex_mentions,
            mode="strict",
            attr_keys=self.evaluation_mapping.mention_attr_keys.get("timex", ()),
        )
        timex_relaxed_dict = score_mention_layer(
            gold_mentions=gold.timex_mentions,
            predicted_mentions=predicted.timex_mentions,
            mode="relaxed",
            attr_keys=self.evaluation_mapping.mention_attr_keys.get("timex", ()),
        )

        # Relations (TLINKs)
        tlink_strict_dict = score_relation_layer(
            gold_relations=gold.relations,
            predicted_relations=predicted.relations,
            mode="strict",
            attr_keys=self.evaluation_mapping.relation_attr_keys.get("tlink", ()),
        )
        tlink_relaxed_dict = score_relation_layer(
            gold_relations=gold.relations,
            predicted_relations=predicted.relations,
            mode="relaxed",
            attr_keys=self.evaluation_mapping.relation_attr_keys.get("tlink", ()),
        )

        relation_scores = {
            "tlink": LayerScores.from_prf_dict("tlink", False, tlink_relaxed_dict),
        }

        # Step-15 diagnostic: populate unmatched_gold_events on the predicted doc
        predicted.unmatched_gold_events = int(event_relaxed_dict.get("fn", 0))

        return MEANTIMEResults(
            doc_id=str(gold.doc_id),
            entity_strict=LayerScores.from_prf_dict("entity", True, entity_strict_dict),
            entity_relaxed=LayerScores.from_prf_dict("entity", False, entity_relaxed_dict),
            event_strict=LayerScores.from_prf_dict("event", True, event_strict_dict),
            event_relaxed=LayerScores.from_prf_dict("event", False, event_relaxed_dict),
            timex_strict=LayerScores.from_prf_dict("timex", True, timex_strict_dict),
            timex_relaxed=LayerScores.from_prf_dict("timex", False, timex_relaxed_dict),
            relation_scores=relation_scores,
            mode="relaxed",
            gold_document=gold,
            predicted_document=predicted,
        )

    def consolidate(
        self,
        evaluation_suite: EvaluationSuite,
        meantime_results: MEANTIMEResults,
        weight_phase_quality: float = 0.40,
        weight_meantime_f1: float = 0.40,
        weight_consistency: float = 0.20,
        srl_diagnostics: Optional[Any] = None,
    ) -> ConsolidatedQualityReport:
        """Create consolidated report combining phase + MEANTIME evaluation.

        Args:
            evaluation_suite: EvaluationSuite from M1-M7 full-stack evaluator
            meantime_results: MEANTIMEResults from MEANTIME comparison
            weight_phase_quality: Weight for phase-level structural quality
            weight_meantime_f1: Weight for gold-standard task accuracy
            weight_consistency: Weight for cross-layer consistency
            srl_diagnostics: Optional SRLKGQualityReport attached by
                ``evaluate_from_neo4j(run_srl_diagnostics=True)``. Falls back
                to ``meantime_results.srl_diagnostics`` when None.

        Returns:
            ConsolidatedQualityReport with combined metrics and analysis
        """
        effective_srl = srl_diagnostics if srl_diagnostics is not None else getattr(meantime_results, "srl_diagnostics", None)
        report = ConsolidatedQualityReport(
            run_metadata=evaluation_suite.run_metadata,
            evaluation_suite=evaluation_suite,
            meantime_results=meantime_results,
            weight_phase_quality=weight_phase_quality,
            weight_meantime_f1=weight_meantime_f1,
            weight_consistency=weight_consistency,
            srl_diagnostics=effective_srl,
        )
        return report


# Aliases for convenience
EvalBridge = MEANTIMEBridge
QualityReport = ConsolidatedQualityReport
