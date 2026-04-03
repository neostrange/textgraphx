from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Iterable, List

from EventEnrichmentPhase import EventEnrichmentPhase
from GraphBasedNLP import GraphBasedNLP
from RefinementPhase import RefinementPhase
from TemporalPhase import TemporalPhase
from TlinksRecognizer import TlinksRecognizer


logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Programmatic orchestrator for the five NLP/KG pipeline phases."""

    PHASE_ORDER = [
        "ingestion",
        "refinement",
        "temporal",
        "event_enrichment",
        "tlinks",
    ]

    def __init__(self, directory: str, model_name: str = "en_core_web_sm") -> None:
        self.directory = str(Path(directory))
        self.model_name = self._resolve_model_name(model_name)
        logger.info(
            "PipelineOrchestrator initialized: directory=%s model_name=%s",
            self.directory,
            self.model_name,
        )

    @staticmethod
    def _resolve_model_name(model_name: str) -> str:
        """Support both short aliases and full spaCy model names."""
        aliases = {
            "sm": "en_core_web_sm",
            "trf": "en_core_web_trf",
        }
        return aliases.get(model_name, model_name)

    @staticmethod
    def _normalize_phase_name(phase: str) -> str:
        value = phase.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "event": "event_enrichment",
            "eventenrichment": "event_enrichment",
            "tlink": "tlinks",
            "graphbasednlp": "ingestion",
            "ingest": "ingestion",
        }
        return aliases.get(value, value)

    @staticmethod
    def _log_step(step_name: str, fn) -> None:
        started = time.perf_counter()
        logger.info("Starting step: %s", step_name)
        try:
            fn()
        except Exception as e:
            elapsed = time.perf_counter() - started
            logger.error("Failed step: %s after %.2fs - %s", step_name, elapsed, e, exc_info=True)
            raise
        elapsed = time.perf_counter() - started
        logger.info("Finished step: %s (%.2fs)", step_name, elapsed)

    @staticmethod
    def _close_graph_if_present(obj: object) -> None:
        graph = getattr(obj, "graph", None)
        close_fn = getattr(graph, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                logger.exception("Failed to close graph handle cleanly")

    def run_ingestion(self, text_id: int = 1, store_tag: bool = False) -> None:
        """Run ingestion phase via GraphBasedNLP.store_corpus + process_text."""
        Path(self.directory).mkdir(parents=True, exist_ok=True)
        graph_nlp = GraphBasedNLP([], model_name=self.model_name, require_neo4j=False)
        try:
            try:
                text_tuples = graph_nlp.store_corpus(self.directory)
            except FileNotFoundError as e:
                raise FileNotFoundError(
                    f"Dataset directory not accessible: {self.directory}\n"
                    f"Original error: {e}"
                ) from e
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load documents from {self.directory}: {e}"
                ) from e
            
            logger.info("Loaded %d documents from %s", len(text_tuples), self.directory)
            
            if not text_tuples:
                logger.warning(
                    "No documents found in %s. Check that dataset has .txt or .xml files "
                    "in the top-level directory.",
                    self.directory
                )
            
            try:
                graph_nlp.process_text(text_tuples=text_tuples, text_id=text_id, storeTag=store_tag)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to process documents: {e}\n"
                    f"This may indicate a Neo4j connection issue or missing spaCy model."
                ) from e
        finally:
            graph_nlp.close()

    def run_refinement(self) -> None:
        """Run all refinement rule methods in the same order as __main__."""
        phase = RefinementPhase([])
        steps = [
            "get_and_assign_head_info_to_entity_multitoken",
            "get_and_assign_head_info_to_entity_singletoken",
            "get_and_assign_head_info_to_antecedent_multitoken",
            "get_and_assign_head_info_to_antecedent_singletoken",
            "get_and_assign_head_info_to_corefmention_multitoken",
            "get_and_assign_head_info_to_corefmention_singletoken",
            "get_and_assign_head_info_to_all_frameArgument_singletoken",
            "get_and_assign_head_info_to_all_frameArgument_multitoken",
            "get_and_assign_head_info_to_frameArgument_singletoken",
            "get_and_assign_head_info_to_frameArgument_multitoken",
            "get_and_assign_head_info_to_frameArgument_with_preposition",
            "get_and_assign_head_info_to_temporal_frameArgument_singletoken",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_pcomp",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj",
            "get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp",
            "link_antecedent_to_namedEntity",
            "detect_correct_NEL_result_for_missing_kb_id",
            "link_frameArgument_to_namedEntity_for_nam_nom",
            "link_frameArgument_to_namedEntity_for_pobj",
            "link_frameArgument_to_namedEntity_for_pobj_entity",
            "link_frameArgument_to_namedEntity_for_pro",
            "link_frameArgument_to_new_entity",
            "tag_value_entities",
            "tag_numeric_entities",
            "detect_quantified_entities_from_frameArgument",
            "link_frameArgument_to_numeric_entities",
            "link_frameArgument_to_entity_via_named_entity",
        ]

        try:
            for step in steps:
                try:
                    self._log_step(f"refinement::{step}", lambda s=step: getattr(phase, s)())
                except Exception as e:
                    logger.error(
                        "Refinement step '%s' failed. This may indicate missing ingestion data.",
                        step
                    )
                    raise
        finally:
            self._close_graph_if_present(phase)

    def run_temporal(self) -> None:
        """Run temporal extraction for all annotated documents."""
        phase = TemporalPhase([])
        try:
            try:
                ids = phase.get_annotated_text()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to retrieve annotated documents for temporal phase: {e}\n"
                    f"Make sure refinement phase completed successfully."
                ) from e
            
            logger.info("Temporal phase will process %d documents", len(ids))
            
            if not ids:
                logger.warning(
                    "No annotated documents found. This may indicate the refinement phase "
                    "did not complete or found no data."
                )
            
            for doc_id in ids:
                try:
                    self._log_step(
                        f"temporal::create_DCT_node(doc_id={doc_id})",
                        lambda d=doc_id: phase.create_DCT_node(d),
                    )
                    self._log_step(
                        f"temporal::create_tevents2(doc_id={doc_id})",
                        lambda d=doc_id: phase.create_tevents2(d),
                    )
                    self._log_step(
                        f"temporal::create_timexes2(doc_id={doc_id})",
                        lambda d=doc_id: phase.create_timexes2(d),
                    )
                except Exception as e:
                    logger.error(
                        "Temporal phase failed for document %d: %s",
                        doc_id, e
                    )
                    raise
        finally:
            self._close_graph_if_present(phase)

    def run_event_enrichment(self) -> None:
        """Run event enrichment phase methods in __main__ order."""
        phase = EventEnrichmentPhase([])
        try:
            self._log_step(
                "event_enrichment::link_frameArgument_to_event",
                phase.link_frameArgument_to_event,
            )
            self._log_step(
                "event_enrichment::add_core_participants_to_event",
                phase.add_core_participants_to_event,
            )
            self._log_step(
                "event_enrichment::add_non_core_participants_to_event",
                phase.add_non_core_participants_to_event,
            )
            self._log_step(
                "event_enrichment::add_label_to_non_core_fa",
                phase.add_label_to_non_core_fa,
            )
        finally:
            self._close_graph_if_present(phase)

    def run_tlinks(self) -> None:
        """Run all six TLINK recognizer case methods."""
        phase = TlinksRecognizer([])
        try:
            self._log_step("tlinks::case1", phase.create_tlinks_case1)
            self._log_step("tlinks::case2", phase.create_tlinks_case2)
            self._log_step("tlinks::case3", phase.create_tlinks_case3)
            self._log_step("tlinks::case4", phase.create_tlinks_case4)
            self._log_step("tlinks::case5", phase.create_tlinks_case5)
            self._log_step("tlinks::case6", phase.create_tlinks_case6)
        finally:
            self._close_graph_if_present(phase)

    def run_selected(
        self,
        phases: Iterable[str],
        *,
        text_id: int = 1,
        store_tag: bool = False,
    ) -> List[str]:
        """Run only selected phases while preserving canonical order."""
        normalized = [self._normalize_phase_name(p) for p in phases]
        invalid = [p for p in normalized if p not in self.PHASE_ORDER]
        if invalid:
            raise ValueError(f"Unknown phase names: {invalid}. Valid: {self.PHASE_ORDER}")

        selected = [phase for phase in self.PHASE_ORDER if phase in set(normalized)]
        logger.info("Selected phases (ordered): %s", selected)

        for phase in selected:
            if phase == "ingestion":
                self._log_step(
                    "phase::ingestion",
                    lambda: self.run_ingestion(text_id=text_id, store_tag=store_tag),
                )
            elif phase == "refinement":
                self._log_step("phase::refinement", self.run_refinement)
            elif phase == "temporal":
                self._log_step("phase::temporal", self.run_temporal)
            elif phase == "event_enrichment":
                self._log_step("phase::event_enrichment", self.run_event_enrichment)
            elif phase == "tlinks":
                self._log_step("phase::tlinks", self.run_tlinks)

        return selected


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
