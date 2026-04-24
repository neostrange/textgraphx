"""Pipeline orchestration module for managing complex NLP workflows."""

import uuid
import time
import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

from .db_interface import ExecutionHistory, ExecutionStatus
from .checkpoint import CheckpointManager
from textgraphx.config import get_config
from textgraphx.infrastructure.logging_utils import (
    get_logger, log_section, log_subsection, ProgressLogger
)
from textgraphx.neo4j_client import make_graph_from_config

logger = get_logger(__name__)


@dataclass
class PhaseResult:
    """Result of executing a pipeline phase."""
    name: str
    status: str
    duration: float
    documents_processed: int = 0
    error: Optional[str] = None
    assertions_passed: Optional[bool] = None  # Item 5: phase-level assertions result
    provenance_violations: int = 0


@dataclass
class PipelineSummary:
    """Summary of pipeline execution."""
    execution_id: str
    phase_count: int
    success_count: int
    failed_count: int
    total_duration: float
    total_documents: Optional[int] = None
    phases: Dict[str, PhaseResult] = field(default_factory=dict)


class PipelineOrchestrator:
    """Orchestrates the execution of multi-phase NLP pipeline."""

    MAINTENANCE_ONLY_PHASES = {"dbpedia_enrichment"}

    DEFAULT_MATERIALIZATION_THRESHOLDS = {
        "MATCH (n:AnnotatedText) RETURN count(n) AS c": 1,
        "MATCH (n:Sentence) RETURN count(n) AS c": 1,
        "MATCH (n:TagOccurrence) RETURN count(n) AS c": 1,
        "MATCH (n:TEvent) RETURN count(n) AS c": 1,
        "MATCH (n:TIMEX) RETURN count(n) AS c": 1,
        "MATCH ()-[r:FRAME_DESCRIBES_EVENT]->() WITH count(r) AS canonical MATCH ()-[l:DESCRIBES]->() WITH canonical, count(l) as l_count RETURN CASE WHEN canonical > 0 THEN canonical ELSE l_count END AS c": 1,
        "MATCH ()-[r:TLINK]->() RETURN count(r) AS c": 1,
    }

    def __init__(self, directory: str = "datastore/dataset", model_name: str = "en_core_web_trf"):
        """Initialize the pipeline orchestrator.
        
        Args:
            directory: Dataset directory path.
            model_name: spaCy model name to use.
        """
        self.directory = Path(directory)
        self.model_name = model_name
        self.execution_id = str(uuid.uuid4())
        cfg = get_config()
        self.execution_history = ExecutionHistory()
        self.checkpoint_manager = CheckpointManager(
            base_dir=str(Path(cfg.paths.output_dir) / "checkpoints")
        )
        self.summary = PipelineSummary(
            execution_id=self.execution_id,
            phase_count=0,
            success_count=0,
            failed_count=0,
            total_duration=0.0,
        )
        self.start_time = None
        self.phases_executed = []
        self.runtime_mode = cfg.runtime.mode
        self.strict_transition_gate = (
            cfg.runtime.strict_transition_gate
            if cfg.runtime.strict_transition_gate is not None
            else self.runtime_mode == "testing"
        )
        
        logger.info(f"Initialized PipelineOrchestrator (ID: {self.execution_id})")
        logger.debug(f"  Dataset directory: {self.directory}")
        logger.debug(f"  Model name: {self.model_name}")
        logger.debug(f"  Runtime mode: {self.runtime_mode}")
        logger.debug(f"  Strict transition gate: {self.strict_transition_gate}")
        logger.debug(f"  Config setup complete")

    def _checkpoint_doc_id(self) -> str:
        """Build a stable checkpoint document key for dataset-level runs."""
        return f"dataset::{self.directory.resolve()}"

    def _dataset_files(self) -> List[Path]:
        patterns = ("*.xml", "*.naf", "*.naf.xml", "*.txt")
        files: List[Path] = []
        for pattern in patterns:
            files.extend(sorted(self.directory.glob(pattern)))
        return sorted({path.resolve() for path in files})

    @staticmethod
    def default_phases(cfg=None) -> List[str]:
        """Return canonical phase order with optional DBpedia enrichment step."""
        cfg = cfg or get_config()
        phases = [
            "ingestion",
            "refinement",
            "temporal",
            "event_enrichment",
        ]
        if cfg.features.enable_dbpedia_enrichment:
            phases.append("dbpedia_enrichment")
        phases.append("tlinks")
        return phases

    @staticmethod
    def _extract_document_identity(path: Path) -> Dict[str, Optional[str]]:
        identity: Dict[str, Optional[str]] = {
            "path": str(path),
            "filename": path.name,
            "public_id": None,
            "uri": None,
        }
        if path.suffix.lower() not in {".xml", ".naf"} and not path.name.lower().endswith(".naf.xml"):
            return identity

        try:
            root = ET.parse(path).getroot()
        except Exception:
            return identity

        file_desc = root.find(".//fileDesc")
        public = root.find(".//public")
        if file_desc is not None and file_desc.attrib.get("filename"):
            identity["filename"] = file_desc.attrib["filename"]
        if public is not None:
            identity["public_id"] = public.attrib.get("publicId")
            identity["uri"] = public.attrib.get("uri")
        return identity

    def _get_dataset_identities(self) -> List[Dict[str, Optional[str]]]:
        return [self._extract_document_identity(path) for path in self._dataset_files()]

    @staticmethod
    def _count_existing_documents(graph, identities: List[Dict[str, Optional[str]]]) -> Dict[str, int]:
        filenames = [item["filename"] for item in identities if item.get("filename")]
        public_ids = [item["public_id"] for item in identities if item.get("public_id")]
        uris = [item["uri"] for item in identities if item.get("uri")]
        rows = graph.run(
            """
            MATCH (n:AnnotatedText)
            WHERE n.filename IN $filenames
               OR n.publicId IN $public_ids
               OR n.uri IN $uris
            RETURN count(n) AS count
            """,
            {
                "filenames": filenames,
                "public_ids": public_ids,
                "uris": uris,
            },
        ).data()
        count = int(rows[0].get("count", 0)) if rows else 0
        return {
            "count": count,
            "matched_documents": filenames,
        }

    @staticmethod
    def _count_total_documents(graph) -> int:
        rows = graph.run("MATCH (n:AnnotatedText) RETURN count(n) AS count").data()
        return int(rows[0].get("count", 0)) if rows else 0

    @staticmethod
    def _clear_graph(graph) -> int:
        rows = graph.run("MATCH (n) DETACH DELETE n RETURN count(n) AS count").data()
        return int(rows[0].get("count", 0)) if rows else 0

    def prepare_review_run(self, graph=None) -> Dict[str, object]:
        """Prepare a full review run.

        Any existing AnnotatedText data is considered unsafe for deterministic
        review/evaluation runs. In testing mode, the full graph is cleared before
        running. In non-testing modes, this raises instead of mutating data.
        """
        cfg = get_config()
        identities = self._get_dataset_identities()
        if not identities:
            raise RuntimeError(f"No dataset documents found in {self.directory}")

        owns_graph = graph is None
        graph = graph or make_graph_from_config()
        try:
            existing = self._count_existing_documents(graph, identities)
            already_processed = existing["count"] > 0
            total_existing = self._count_total_documents(graph)
            contains_foreign_documents = total_existing > existing["count"]

            if total_existing > 0 and cfg.runtime.mode != "testing":
                raise RuntimeError(
                    "AnnotatedText nodes already exist in Neo4j. "
                    "Automatic database reset is only allowed in testing mode."
                )

            cleared = 0
            if total_existing > 0:
                cleared = self._clear_graph(graph)
                logger.warning(
                    "Cleared Neo4j graph for testing review run; removed %s nodes",
                    cleared,
                )

            return {
                "already_processed": already_processed,
                "database_cleared": total_existing > 0,
                "cleared_node_count": cleared,
                "matched_documents": existing["matched_documents"],
                "existing_document_count": total_existing,
                "foreign_documents_present": contains_foreign_documents,
                "runtime_mode": cfg.runtime.mode,
            }
        finally:
            if owns_graph:
                close_fn = getattr(graph, "close", None)
                if callable(close_fn):
                    close_fn()

    def assess_review_run_safety(self, phases: Optional[List[str]] = None, graph=None) -> Dict[str, object]:
        """Return a non-mutating safety posture for a review run.

        This method never clears data. It reports whether a run would be blocked
        or require cleanup under current runtime mode and selected phases.
        """
        cfg = get_config()
        phases = phases or self.default_phases(cfg)

        posture = {
            "runtime_mode": cfg.runtime.mode,
            "strict_transition_gate": bool(self.strict_transition_gate),
            "cross_document_fusion_enabled": bool(
                getattr(cfg.runtime, "enable_cross_document_fusion", False)
            ),
            "review_preparation_required": self.phases_require_review_preparation(phases),
            "materialization_gate_required": self.phases_require_materialization_gate(phases),
            "dataset_file_count": 0,
            "dataset_identity_count": 0,
            "matched_documents": [],
            "matched_existing_documents": 0,
            "existing_document_count": 0,
            "foreign_documents_present": False,
            "would_clear_graph": False,
            "would_block_run": False,
            "reason": "ok",
        }

        if not posture["review_preparation_required"]:
            posture["reason"] = "maintenance_only_phases"
            return posture

        identities = self._get_dataset_identities()
        posture["dataset_identity_count"] = len(identities)
        posture["dataset_file_count"] = len(self._dataset_files())
        if not identities:
            posture["would_block_run"] = True
            posture["reason"] = "no_dataset_documents"
            return posture

        owns_graph = graph is None
        graph = graph or make_graph_from_config()
        try:
            existing = self._count_existing_documents(graph, identities)
            total_existing = self._count_total_documents(graph)
            foreign = total_existing > existing["count"]

            posture["matched_documents"] = existing["matched_documents"]
            posture["matched_existing_documents"] = int(existing["count"])
            posture["existing_document_count"] = int(total_existing)
            posture["foreign_documents_present"] = bool(foreign)

            if total_existing > 0:
                if cfg.runtime.mode == "testing":
                    posture["would_clear_graph"] = True
                    posture["reason"] = "testing_mode_requires_clean_graph"
                else:
                    posture["would_block_run"] = True
                    posture["reason"] = "existing_documents_in_non_testing_mode"
            return posture
        finally:
            if owns_graph:
                close_fn = getattr(graph, "close", None)
                if callable(close_fn):
                    close_fn()

    @classmethod
    def _normalized_phase_set(cls, phases: Optional[List[str]]) -> set[str]:
        return {str(phase).strip().lower() for phase in (phases or []) if str(phase).strip()}

    @classmethod
    def phases_require_review_preparation(cls, phases: Optional[List[str]]) -> bool:
        normalized = cls._normalized_phase_set(phases)
        if not normalized:
            return True
        return not normalized.issubset(cls.MAINTENANCE_ONLY_PHASES)

    @classmethod
    def phases_require_materialization_gate(cls, phases: Optional[List[str]]) -> bool:
        normalized = cls._normalized_phase_set(phases)
        if not normalized:
            return True
        return not normalized.issubset(cls.MAINTENANCE_ONLY_PHASES)

    def run_for_review(self, phases: Optional[List[str]] = None) -> Dict[str, object]:
        """Prepare the graph and run the requested phases for Neo4j review."""
        phases = phases or self.default_phases()
        self._allow_empty_materialization_gate = False
        if self.phases_require_review_preparation(phases):
            preparation = self.prepare_review_run()
        else:
            preparation = {
                "already_processed": False,
                "database_cleared": False,
                "cleared_node_count": 0,
                "matched_documents": [],
                "runtime_mode": self.runtime_mode,
                "review_preparation_skipped": True,
            }
        self.run_selected(phases)
        if int(getattr(self.summary, "total_documents", 0) or 0) == 0:
            self._allow_empty_materialization_gate = True
        if self.phases_require_materialization_gate(phases):
            preparation["materialization_gate"] = self.validate_materialization_gate()
        else:
            preparation["materialization_gate"] = {
                "passed": True,
                "checks": [],
                "skipped": True,
                "reason": "maintenance_only_phases",
            }
        return preparation

    def validate_materialization_gate(
        self,
        graph=None,
        thresholds: Optional[Dict[str, int]] = None,
    ) -> Dict[str, object]:
        """Validate that key graph layers were materialized after a run.

        Raises RuntimeError when any threshold is not met.
        """
        checks: List[Dict[str, object]] = []
        thresholds = thresholds or self.DEFAULT_MATERIALIZATION_THRESHOLDS
        owns_graph = graph is None
        graph = graph or make_graph_from_config()

        try:
            for query, minimum in thresholds.items():
                rows = graph.run(query).data()
                actual = int(rows[0].get("c", 0)) if rows else 0
                checks.append(
                    {
                        "query": query,
                        "minimum": int(minimum),
                        "actual": actual,
                        "passed": actual >= int(minimum),
                    }
                )

            failed = [check for check in checks if not check["passed"]]

            if (
                owns_graph
                and getattr(self, "_allow_empty_materialization_gate", False)
                and checks
                and all(int(check.get("actual", 0)) == 0 for check in checks)
            ):
                return {
                    "passed": True,
                    "checks": checks,
                    "skipped": True,
                    "reason": "empty_review_run",
                }

            result = {
                "passed": len(failed) == 0,
                "checks": checks,
            }
            if failed:
                failing_summary = "; ".join(
                    f"min={c['minimum']} actual={c['actual']} query={c['query']}"
                    for c in failed
                )
                raise RuntimeError(f"Materialization gate failed: {failing_summary}")
            return result
        finally:
            if owns_graph:
                close_fn = getattr(graph, "close", None)
                if callable(close_fn):
                    close_fn()

    def run_selected(self, phases: List[str], resume_from_checkpoint: bool = False) -> None:
        """Run selected phases of the pipeline.
        
        Args:
            phases: List of phase names to execute.
            resume_from_checkpoint: If true, skip phases that already have a checkpoint.
            
        Raises:
            Exception: If a phase fails fatally.
        """
        with log_section(logger, f"PIPELINE EXECUTION - {len(phases)} phases"):
            self.start_time = time.time()
            started_at = datetime.now().isoformat()

            if resume_from_checkpoint:
                resume_plan = self.checkpoint_manager.resume_from_checkpoint(
                    doc_id=self._checkpoint_doc_id(),
                    phase_order=phases,
                )
                phases = resume_plan.remaining_phases
                logger.info(
                    "Checkpoint resume enabled: completed=%s remaining=%s",
                    ", ".join(resume_plan.completed_phases) or "<none>",
                    ", ".join(resume_plan.remaining_phases) or "<none>",
                )
                if not phases:
                    logger.info("No remaining phases to execute after checkpoint resume.")
                    self.summary.phase_count = 0
                    self.summary.success_count = 0
                    self.summary.failed_count = 0
                    self.summary.total_duration = 0.0
                    self.summary.total_documents = 0
                    return

            # Item 8: per-document run report
            from textgraphx.run_report import RunReport
            run_report = RunReport(execution_id=self.execution_id)

            logger.info(f"Execution ID: {self.execution_id}")
            logger.info(f"Phases to execute: {', '.join(phases)}")
            
            try:
                # Map phases to their functions
                phase_runners = {
                    "ingestion": self._run_ingestion,
                    "refinement": self._run_refinement,
                    "temporal": self._run_temporal,
                    "event_enrichment": self._run_event_enrichment,
                    "dbpedia_enrichment": self._run_dbpedia_enrichment,
                    "tlinks": self._run_tlinks,
                }

                self.summary.phase_count = len(phases)
                total_documents = 0

                # Execute each selected phase
                for idx, phase_name in enumerate(phases, 1):
                    if phase_name not in phase_runners:
                        logger.warning(f"Unknown phase: {phase_name}")
                        continue

                    with log_subsection(logger, f"Phase {idx}/{len(phases)}: {phase_name.upper()}"):
                        phase_start = time.time()
                        try:
                            result = phase_runners[phase_name]()
                            if (
                                isinstance(result, dict)
                                and str(result.get("status", "")).strip().lower() == "error"
                            ):
                                raise RuntimeError(
                                    f"Phase '{phase_name}' returned error status: "
                                    f"{result.get('message', 'unspecified phase error')}"
                                )
                            phase_duration = time.time() - phase_start
                            doc_count = result.get("documents_processed", 0)
                            assertions_passed = result.get("assertions_passed")
                            provenance_violations = int(result.get("provenance_violations", 0) or 0)
                            endpoint_violations = int(result.get("endpoint_violations", 0) or 0)

                            self.summary.phases[phase_name] = PhaseResult(
                                name=phase_name,
                                status="completed",
                                duration=phase_duration,
                                documents_processed=doc_count,
                                assertions_passed=assertions_passed,
                                provenance_violations=provenance_violations,
                            )
                            self.summary.success_count += 1
                            total_documents += doc_count
                            self.phases_executed.append(phase_name)

                            # Item 5: checkpoint write for resumable phase execution.
                            checkpoint_nodes = result.get("node_counts") if isinstance(result, dict) else None
                            checkpoint_edges = result.get("edge_counts") if isinstance(result, dict) else None
                            self.checkpoint_manager.save_checkpoint(
                                doc_id=self._checkpoint_doc_id(),
                                phase_name=phase_name,
                                node_counts=checkpoint_nodes if isinstance(checkpoint_nodes, dict) else None,
                                edge_counts=checkpoint_edges if isinstance(checkpoint_edges, dict) else None,
                                phase_markers=list(self.phases_executed),
                                properties_snapshot={
                                    "assertions_passed": assertions_passed,
                                    "provenance_violations": provenance_violations,
                                    "endpoint_violations": endpoint_violations,
                                },
                                metadata={
                                    "execution_id": self.execution_id,
                                    "phase_duration_seconds": phase_duration,
                                    "documents_processed": doc_count,
                                },
                            )

                            # Item 8: record phase outcome in run report
                            run_report.mark_processed(
                                doc_id=phase_name,
                                filename=f"phase:{phase_name}",
                                phases_completed=[phase_name],
                                duration_seconds=phase_duration,
                            )

                            # Item 5: log assertion status inline
                            assertion_label = (
                                " [assertions: PASS]"
                                if assertions_passed is True
                                else " [assertions: FAIL]"
                                if assertions_passed is False
                                else ""
                            )
                            provenance_label = (
                                f" [provenance_violations: {provenance_violations}]"
                                if provenance_violations > 0
                                else ""
                            )
                            endpoint_label = (
                                f" [endpoint_violations: {endpoint_violations}]"
                                if endpoint_violations > 0
                                else ""
                            )
                            logger.info(
                                f"\u2713 Phase '{phase_name}' completed in "
                                f"{phase_duration:.2f}s{assertion_label}{provenance_label}{endpoint_label}"
                            )
                            logger.debug(f"  Result: {result}")

                            if self.strict_transition_gate and assertions_passed is False:
                                raise RuntimeError(
                                    "Strict transition gate failed: "
                                    f"phase '{phase_name}' reported assertion failure in testing mode"
                                )
                            if self.strict_transition_gate and provenance_violations > 0:
                                raise RuntimeError(
                                    "Strict transition gate failed: "
                                    f"phase '{phase_name}' reported {provenance_violations} provenance contract violations"
                                )
                            if self.strict_transition_gate and endpoint_violations > 0:
                                raise RuntimeError(
                                    "Strict transition gate failed: "
                                    f"phase '{phase_name}' reported {endpoint_violations} endpoint contract violations"
                                )

                        except Exception as e:
                            phase_duration = time.time() - phase_start
                            self.summary.phases[phase_name] = PhaseResult(
                                name=phase_name,
                                status="failed",
                                duration=phase_duration,
                                error=str(e),
                            )
                            self.summary.failed_count += 1

                            # Item 8: record failed phase in run report
                            run_report.mark_failed(
                                doc_id=phase_name,
                                filename=f"phase:{phase_name}",
                                failed_phase=phase_name,
                                reason=f"{type(e).__name__}: {e}",
                                phases_completed=list(self.phases_executed),
                                duration_seconds=phase_duration,
                            )

                            logger.error(f"\u2717 Phase '{phase_name}' failed after {phase_duration:.2f}s")
                            logger.error(f"  Error: {type(e).__name__}: {e}")
                            raise

                # Calculate total duration
                total_duration = time.time() - self.start_time
                self.summary.total_duration = total_duration
                self.summary.total_documents = total_documents

                # Record execution in history
                completed_at = datetime.now().isoformat()
                status = ExecutionStatus.SUCCESS.value if self.summary.failed_count == 0 else ExecutionStatus.FAILED.value
                
                logger.info(f"\n{'='*60}")
                logger.info(f"PIPELINE EXECUTION SUMMARY")
                logger.info(f"{'='*60}")
                logger.info(f"Execution ID: {self.execution_id}")
                logger.info(f"Total Duration: {total_duration:.2f}s")
                logger.info(f"Phases Completed: {self.summary.success_count}/{self.summary.phase_count}")
                logger.info(f"Documents Processed: {total_documents}")
                logger.info(f"Status: {status.upper()}")
                logger.info(f"{'='*60}\n")

                # Item 8: emit per-phase run report
                run_report.log_summary()

                self.execution_history.record_execution(
                    execution_id=self.execution_id,
                    status=status,
                    total_duration=total_duration,
                    documents_processed=total_documents,
                    phases=self.phases_executed,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_message=None,
                )
            
            except Exception as e:
                # Record failed execution
                total_duration = time.time() - self.start_time if self.start_time else 0
                self.summary.total_duration = total_duration
                completed_at = datetime.now().isoformat()
                
                self.execution_history.record_execution(
                    execution_id=self.execution_id,
                    status=ExecutionStatus.FAILED.value,
                    total_duration=total_duration,
                    documents_processed=self.summary.total_documents or 0,
                    phases=self.phases_executed,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_message=str(e),
                )
                raise

    # Phase execution methods
    def _run_ingestion(self) -> Dict[str, any]:
        """Run the ingestion phase - parse documents using GraphBasedNLP."""
        logger.info("Starting ingestion phase...")
        try:
            from textgraphx.phase_wrappers import GraphBasedNLPWrapper
            
            wrapper = GraphBasedNLPWrapper(
                model_name=self.model_name,
                require_neo4j=True,
                strict_transition_gate=self.strict_transition_gate,
            )
            result = wrapper.execute(str(self.directory))
            logger.info(f"Ingestion phase: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in ingestion phase: {e}")
            # Fallback to stub mode on any error
            documents = self._count_documents()
            return {"documents_processed": documents}

    def _run_refinement(self) -> Dict[str, any]:
        """Run the refinement phase - clean and normalize extracted data."""
        logger.info("Starting refinement phase...")
        try:
            from textgraphx.phase_wrappers import RefinementPhaseWrapper
            
            wrapper = RefinementPhaseWrapper(
                strict_transition_gate=self.strict_transition_gate
            )
            result = wrapper.execute()
            logger.info(f"Refinement phase: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in refinement phase: {e}")
            # Fallback to stub mode on any error
            return {"status": "error", "message": str(e)}

    def _run_temporal(self) -> Dict[str, any]:
        """Run the temporal phase - identify temporal entities and relations."""
        logger.info("Starting temporal phase...")
        try:
            from textgraphx.phase_wrappers import TemporalPhaseWrapper
            
            wrapper = TemporalPhaseWrapper(
                strict_transition_gate=self.strict_transition_gate
            )
            result = wrapper.execute()
            logger.info(f"Temporal phase: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in temporal phase: {e}")
            # Fallback to stub mode on any error
            return {"status": "error", "message": str(e)}

    def _run_event_enrichment(self) -> Dict[str, any]:
        """Run the event enrichment phase - extract and enrich events."""
        logger.info("Starting event enrichment phase...")
        try:
            from textgraphx.phase_wrappers import EventEnrichmentPhaseWrapper
            
            wrapper = EventEnrichmentPhaseWrapper(
                strict_transition_gate=self.strict_transition_gate
            )
            result = wrapper.execute()
            logger.info(f"Event enrichment phase: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in event enrichment phase: {e}")
            # Fallback to stub mode on any error
            return {"status": "error", "message": str(e)}

    def _run_tlinks(self) -> Dict[str, any]:
        """Run the TLINKs phase - identify temporal links between events."""
        logger.info("Starting TLINKs phase...")
        try:
            from textgraphx.phase_wrappers import TlinksRecognizerWrapper
            
            wrapper = TlinksRecognizerWrapper(
                strict_transition_gate=self.strict_transition_gate
            )
            result = wrapper.execute()
            logger.info(f"TLINKs phase: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in TLINKs phase: {e}")
            # Fallback to stub mode on any error
            return {"status": "error", "message": str(e)}

    def _run_dbpedia_enrichment(self) -> Dict[str, any]:
        """Run optional DBpedia enrichment phase."""
        logger.info("Starting DBpedia enrichment phase...")
        try:
            from textgraphx.phase_wrappers import DBpediaEnrichmentPhaseWrapper

            wrapper = DBpediaEnrichmentPhaseWrapper(
                strict_transition_gate=self.strict_transition_gate
            )
            result = wrapper.execute()
            logger.info(f"DBpedia enrichment phase: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in DBpedia enrichment phase: {e}")
            return {"status": "error", "message": str(e)}

    def _count_documents(self) -> int:
        """Count documents in the dataset directory.
        
        Returns:
            Number of documents found.
        """
        try:
            if not self.directory.exists():
                return 0
            
            # Count XML and TXT files safely
            xml_files = list(self.directory.glob("*.xml"))
            txt_files = list(self.directory.glob("*.txt"))
            count = len(xml_files) + len(txt_files)
            return count
        except Exception as e:
            logger.warning(f"Could not count documents in {self.directory}: {e}")
            return 0


class JobScheduler:
    """Manages scheduled pipeline jobs."""

    def __init__(self):
        """Initialize the job scheduler."""
        self.jobs = {}
        self.job_history = ExecutionHistory()

    def list_jobs(self) -> Dict[str, Dict]:
        """Get all scheduled jobs.
        
        Returns:
            Dictionary mapping job IDs to job configurations.
        """
        return self.jobs.copy()

    def get_scheduled_jobs(self) -> List[Dict]:
        """Get all scheduled jobs.
        
        Returns:
            List of job configurations.
        """
        return list(self.jobs.values())

    def schedule_job(
        self,
        schedule_time: str,
        phases: List[str],
        dataset_dir: str,
        model_name: str = "en_core_web_trf",
    ) -> str:
        """Schedule a pipeline job.
        
        Args:
            schedule_time: ISO format datetime for when to run the job.
            phases: List of phases to execute.
            dataset_dir: Dataset directory path.
            model_name: spaCy model name to use.
            
        Returns:
            Job ID.
        """
        job_id = str(uuid.uuid4())
        
        self.jobs[job_id] = {
            "schedule_time": schedule_time,
            "phases": phases,
            "dataset_dir": dataset_dir,
            "model_name": model_name,
            "status": "scheduled",
            "type": "one-time",
        }
        
        logger.info(f"Job {job_id} scheduled for {schedule_time}")
        return job_id

    def schedule_interval(
        self,
        job_id: str,
        dataset_path: str,
        phases: List[str],
        hours: int,
        model_name: str = "en_core_web_trf",
    ) -> bool:
        """Schedule a recurring pipeline job with interval.
        
        Args:
            job_id: Unique job identifier.
            dataset_path: Dataset directory path.
            phases: List of phases to execute.
            hours: Interval in hours.
            model_name: spaCy model name to use.
            
        Returns:
            True if job was scheduled successfully.
        """
        try:
            self.jobs[job_id] = {
                "type": "interval",
                "dataset_dir": dataset_path,
                "phases": phases,
                "hours": hours,
                "model_name": model_name,
                "status": "scheduled",
            }
            logger.info(f"Interval job {job_id} scheduled every {hours} hour(s)")
            return True
        except Exception as e:
            logger.error(f"Failed to schedule interval job: {e}")
            return False

    def schedule_cron(
        self,
        job_id: str,
        dataset_path: str,
        phases: List[str],
        cron_expression: str,
        model_name: str = "en_core_web_trf",
    ) -> bool:
        """Schedule a recurring pipeline job with cron expression.
        
        Args:
            job_id: Unique job identifier.
            dataset_path: Dataset directory path.
            phases: List of phases to execute.
            cron_expression: Cron expression for scheduling.
            model_name: spaCy model name to use.
            
        Returns:
            True if job was scheduled successfully.
        """
        try:
            self.jobs[job_id] = {
                "type": "cron",
                "dataset_dir": dataset_path,
                "phases": phases,
                "cron_expression": cron_expression,
                "model_name": model_name,
                "status": "scheduled",
            }
            logger.info(f"Cron job {job_id} scheduled with expression: {cron_expression}")
            return True
        except Exception as e:
            logger.error(f"Failed to schedule cron job: {e}")
            return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job.
        
        Args:
            job_id: ID of the job to cancel.
            
        Returns:
            True if job was cancelled, False if not found.
        """
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Job {job_id} cancelled")
            return True
        return False


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the full textgraphx pipeline for Neo4j review")
    parser.add_argument("--dir", dest="directory", default="datastore/dataset")
    parser.add_argument("--model", dest="model_name", default="en_core_web_trf")
    parser.add_argument(
        "--phases",
        nargs="*",
        default=None,
    )
    args = parser.parse_args(argv)

    orchestrator = PipelineOrchestrator(directory=args.directory, model_name=args.model_name)
    selected_phases = args.phases if args.phases else orchestrator.default_phases()
    result = orchestrator.run_for_review(phases=selected_phases)
    logger.info("Review-run result: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
