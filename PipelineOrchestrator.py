from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List

from textgraphx.orchestration.orchestrator import PipelineOrchestrator as _CanonicalPipelineOrchestrator

logger = logging.getLogger(__name__)


class _SummaryCompat:
    """Compatibility wrapper exposing legacy summary methods over canonical summary."""

    def __init__(self, orchestrator: _CanonicalPipelineOrchestrator) -> None:
        self._orchestrator = orchestrator

    def start(self) -> None:
        # Legacy callers invoke this explicitly; canonical orchestrator manages lifecycle.
        return None

    def finish(self) -> None:
        # Legacy callers invoke this explicitly; canonical orchestrator manages lifecycle.
        return None

    @property
    def phases(self):
        return self._orchestrator.summary.phases

    @property
    def phase_count(self) -> int:
        return int(self._orchestrator.summary.phase_count)

    @property
    def success_count(self) -> int:
        return int(self._orchestrator.summary.success_count)

    @property
    def failed_count(self) -> int:
        return int(self._orchestrator.summary.failed_count)

    @property
    def total_duration(self) -> float:
        return float(self._orchestrator.summary.total_duration)

    @property
    def total_documents(self):
        return self._orchestrator.summary.total_documents

    @property
    def errors(self) -> List[str]:
        out: List[str] = []
        for name, phase in self._orchestrator.summary.phases.items():
            if phase.error:
                out.append(f"{name}: {phase.error}")
        return out


class PipelineOrchestrator:
    """Compatibility shim for the legacy orchestrator path.

    Canonical implementation now lives in textgraphx.orchestration.orchestrator.
    Legacy phase ordering remains TemporalPhase before TlinksRecognizer.
    """

    PHASE_ORDER = ["ingestion", "refinement", "temporal", "event_enrichment", "dbpedia_enrichment", "tlinks"]

    def __init__(self, directory: str, model_name: str = "en_core_web_sm") -> None:
        logger.warning(
            "textgraphx.PipelineOrchestrator is deprecated; using textgraphx.orchestration.orchestrator.PipelineOrchestrator"
        )
        self._delegate = _CanonicalPipelineOrchestrator(directory=directory, model_name=model_name)
        self.summary = _SummaryCompat(self._delegate)

    def run_selected(
        self,
        phases: Iterable[str],
        *,
        text_id: int = 1,
        store_tag: bool = False,
    ) -> List[str]:
        # Keep signature compatibility; canonical orchestrator ignores text_id/store_tag.
        del text_id, store_tag
        self._delegate.run_selected(list(phases))
        return list(phases)

    def run_for_review(self, phases: List[str] | None = None):
        return self._delegate.run_for_review(phases=phases)

    def prepare_review_run(self, graph=None):
        return self._delegate.prepare_review_run(graph=graph)

    def validate_materialization_gate(self, graph=None, thresholds=None):
        return self._delegate.validate_materialization_gate(graph=graph, thresholds=thresholds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="Run full or selective textgraphx pipeline")
    parser.add_argument(
        "--directory",
        "-d",
        default=str(Path(__file__).resolve().parent / "datastore" / "dataset"),
        help="Dataset directory",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="en_core_web_sm",
        help="spaCy model (en_core_web_sm/en_core_web_trf or sm/trf)",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        default=PipelineOrchestrator.PHASE_ORDER,
        help="Phases to run",
    )
    args = parser.parse_args()

    orchestrator = PipelineOrchestrator(args.directory, args.model)
    orchestrator.run_selected(args.phases)
