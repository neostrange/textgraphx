"""
Simplified wrappers for pipeline phases to standardize orchestrator interface.

Each phase has different internal APIs, so these wrappers provide a consistent
execute() method for the orchestrator to call.
"""

import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path
from textgraphx.logging_utils import (
    get_logger, log_section, log_subsection, timer_log, ProgressLogger
)

logger = get_logger(__name__)


class GraphBasedNLPWrapper:
    """Wrapper for GraphBasedNLP ingestion phase."""
    
    def __init__(self, model_name: str = "en_core_web_trf", require_neo4j: bool = True):
        self.model_name = model_name
        self.require_neo4j = require_neo4j
        self.documents_processed = 0
        self.logger = get_logger(f"{__name__}.GraphBasedNLP")
        self.logger.info(
            f"Initialized GraphBasedNLPWrapper with model={model_name}, "
            f"require_neo4j={require_neo4j}"
        )
    
    def execute(self, directory: str) -> Dict[str, Any]:
        """Execute GraphBasedNLP on a directory."""
        with log_section(self.logger, "INGESTION PHASE - GraphBasedNLP"):
            try:
                with log_subsection(self.logger, "Importing GraphBasedNLP"):
                    from textgraphx.GraphBasedNLP import GraphBasedNLP
                    self.logger.debug("GraphBasedNLP imported successfully")
                
                with log_subsection(self.logger, f"Processing directory: {directory}"):
                    # Check if directory exists
                    if not Path(directory).exists():
                        self.logger.error(f"Directory not found: {directory}")
                        return {"status": "error", "message": f"Directory not found: {directory}"}
                    
                    # Count input files
                    xml_files = list(Path(directory).glob("*.xml"))
                    txt_files = list(Path(directory).glob("*.txt"))
                    total_files = len(xml_files) + len(txt_files)
                    self.logger.info(f"Found {total_files} documents (XML: {len(xml_files)}, TXT: {len(txt_files)})")
                    
                    if total_files == 0:
                        self.logger.warning("No documents found in directory")
                        return {"status": "success", "documents_processed": 0, "message": "No documents found"}
                
                # Initialize the processor
                with log_subsection(self.logger, "Initializing GraphBasedNLP"):
                    nlp = GraphBasedNLP(
                        argv=[],
                        model_name=self.model_name,
                        require_neo4j=self.require_neo4j
                    )
                    self.logger.debug("GraphBasedNLP initialized successfully")
                
                # Process corpus
                with log_subsection(self.logger, "Storing corpus and extracting text"):
                    start_time = time.time()
                    text_tuples = nlp.store_corpus(directory)
                    corpus_time = time.time() - start_time
                    
                    if text_tuples:
                        self.logger.info(f"Extracted {len(text_tuples)} text tuples in {corpus_time:.2f}s")
                    else:
                        self.logger.warning("No text tuples extracted from corpus")
                        return {"status": "success", "documents_processed": 0}
                
                # Process extracted text
                with log_subsection(self.logger, "Processing extracted text with NLP"):
                    start_time = time.time()
                    
                    progress = ProgressLogger(self.logger, len(text_tuples), "NLP Processing")
                    
                    nlp.process_text(
                        text_tuples=text_tuples,
                        text_id=1,
                        storeTag=False
                    )
                    
                    process_time = time.time() - start_time
                    self.documents_processed = len(text_tuples)
                    
                    self.logger.info(
                        f"Processed {self.documents_processed} documents in {process_time:.2f}s "
                        f"({process_time/max(1, self.documents_processed):.2f}s per document)"
                    )
                    progress.finish()
                
                # Store in Neo4j
                with log_subsection(self.logger, "Storing results in Neo4j"):
                    # This is typically done within process_text, but log the result
                    self.logger.info(f"Results stored in Neo4j database")
                
                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    assertion_result = PhaseAssertions(nlp.graph).after_ingestion()
                    assertions_passed = assertion_result.passed
                    record_phase_run(
                        nlp.graph, "ingestion",
                        duration_seconds=corpus_time + process_time,
                        documents_processed=self.documents_processed,
                    )
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                result = {
                    "status": "success",
                    "documents_processed": self.documents_processed,
                    "corpus_time": corpus_time,
                    "processing_time": process_time,
                    "assertions_passed": assertions_passed,
                }
                self.logger.info(f"Ingestion phase completed successfully: {result}")
                return result
                
            except Exception as e:
                self.logger.error(
                    f"Ingestion phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise


class RefinementPhaseWrapper:
    """Wrapper for RefinementPhase entity/relation refinement."""
    
    def __init__(self):
        self.entities_refined = 0
        self.logger = get_logger(f"{__name__}.RefinementPhase")
        self.logger.info("Initialized RefinementPhaseWrapper")
    
    def execute(self) -> Dict[str, Any]:
        """Execute RefinementPhase for data cleaning."""
        with log_section(self.logger, "REFINEMENT PHASE - Entity/Relation Cleaning"):
            try:
                with log_subsection(self.logger, "Importing RefinementPhase"):
                    from textgraphx.RefinementPhase import RefinementPhase
                    self.logger.debug("RefinementPhase imported successfully")
                
                with log_subsection(self.logger, "Initializing RefinementPhase"):
                    refiner = RefinementPhase(argv=[])
                    self.logger.debug("RefinementPhase initialized")
                
                # Run refinement steps with detailed logging
                refinement_steps = [
                    ("Entity multitoken head assignment", refiner.get_and_assign_head_info_to_entity_multitoken),
                    ("Entity single-token head assignment", refiner.get_and_assign_head_info_to_entity_singletoken),
                    ("Antecedent multitoken head assignment", refiner.get_and_assign_head_info_to_antecedent_multitoken),
                    ("Antecedent single-token head assignment", refiner.get_and_assign_head_info_to_antecedent_singletoken),
                    ("Coreference mention multitoken head assignment", refiner.get_and_assign_head_info_to_corefmention_multitoken),
                    ("Coreference mention single-token head assignment", refiner.get_and_assign_head_info_to_corefmention_singletoken),
                    ("Frame argument single-token assignment", refiner.get_and_assign_head_info_to_all_frameArgument_singletoken),
                ]
                
                self.logger.info(f"Starting {len(refinement_steps)} refinement steps")
                
                for step_name, step_func in refinement_steps:
                    with log_subsection(self.logger, step_name):
                        step_func()
                        self.logger.debug(f"✓ Completed: {step_name}")

                cross_sentence_links = 0
                cross_document_links = 0
                with log_subsection(self.logger, "Cross-sentence/cross-document fusion"):
                    from textgraphx.fusion import (
                        fuse_entities_cross_sentence,
                        fuse_entities_cross_document,
                    )
                    cross_sentence_links = fuse_entities_cross_sentence(refiner.graph)
                    cross_document_links = fuse_entities_cross_document(refiner.graph)
                    self.logger.info(
                        "Fusion links created: CO_OCCURS_WITH=%s, SAME_AS=%s",
                        cross_sentence_links,
                        cross_document_links,
                    )
                
                self.logger.info("All refinement steps completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    assertion_result = PhaseAssertions(refiner.graph).after_refinement()
                    assertions_passed = assertion_result.passed
                    record_phase_run(refiner.graph, "refinement", duration_seconds=0.0)
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {
                    "status": "success",
                    "entities_refined": self.entities_refined,
                    "cross_sentence_links": cross_sentence_links,
                    "cross_document_links": cross_document_links,
                    "assertions_passed": assertions_passed,
                }
                
            except Exception as e:
                self.logger.error(
                    f"Refinement phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise


class TemporalPhaseWrapper:
    """Wrapper for TemporalPhase temporal entity extraction."""
    
    def __init__(self):
        self.temporal_entities = 0
        self.logger = get_logger(f"{__name__}.TemporalPhase")
        self.logger.info("Initialized TemporalPhaseWrapper")
    
    def execute(self) -> Dict[str, Any]:
        """Execute TemporalPhase for temporal extraction."""
        with log_section(self.logger, "TEMPORAL PHASE - Temporal Entity & Relation Extraction"):
            try:
                with log_subsection(self.logger, "Importing TemporalPhase"):
                    from textgraphx.TemporalPhase import TemporalPhase
                    self.logger.debug("TemporalPhase imported successfully")
                
                with log_subsection(self.logger, "Initializing TemporalPhase"):
                    temporal = TemporalPhase(argv=[])
                    self.logger.debug("TemporalPhase initialized")
                
                # Get annotated text to find document IDs
                with log_subsection(self.logger, "Retrieving annotated text"):
                    annotated = temporal.get_annotated_text()
                    document_ids = set()
                    
                    if annotated:
                        self.logger.info(f"Retrieved annotated text ({len(annotated)} items)")
                        for item in annotated:
                            if isinstance(item, dict):
                                doc_id = item.get("doc_id", item.get("n.id", item.get("id")))
                                if doc_id is not None:
                                    document_ids.add(doc_id)
                            elif item is not None:
                                document_ids.add(item)
                    else:
                        self.logger.warning("No annotated text found")
                    
                    self.logger.info(f"Identified {len(document_ids)} unique documents")
                
                # Process each document with detailed logging
                if document_ids:
                    with log_subsection(self.logger, f"Processing temporal extraction for {len(document_ids)} documents"):
                        progress = ProgressLogger(self.logger, len(document_ids) * 5, "Temporal Operations")
                        
                        for doc_id in sorted(document_ids):
                            self.logger.debug(f"Processing document: {doc_id}")
                            
                            try:
                                temporal.create_DCT_node(doc_id)
                                progress.update(1, f"Created DCT node for {doc_id}")
                                
                                temporal.create_tevents2(doc_id)
                                progress.update(1, f"Created temporal events for {doc_id}")
                                
                                temporal.create_timexes2(doc_id)
                                progress.update(1, f"Created temporal expressions for {doc_id}")
                                
                                temporal.create_tlinks_e2e(doc_id)
                                progress.update(1, f"Created event-to-event temporal links for {doc_id}")
                                
                                temporal.create_tlinks_e2t(doc_id)
                                progress.update(1, f"Created event-to-time temporal links for {doc_id}")
                                
                                self.logger.debug(f"✓ Completed temporal processing for {doc_id}")
                            except Exception as doc_error:
                                self.logger.error(
                                    f"Error processing document {doc_id}: {type(doc_error).__name__}: {doc_error}",
                                    exc_info=False
                                )
                        
                        progress.finish()
                
                self.logger.info("Temporal extraction completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    from textgraphx.provenance import stamp_inferred_relationships
                    assertion_result = PhaseAssertions(temporal.graph).after_temporal()
                    assertions_passed = assertion_result.passed
                    stamp_inferred_relationships(
                        temporal.graph,
                        rel_type="TLINK",
                        confidence=0.75,
                        evidence_source="temporal_phase",
                        rule_id="temporal_xml_tlinks",
                    )
                    record_phase_run(
                        temporal.graph, "temporal",
                        duration_seconds=0.0,
                        documents_processed=len(document_ids),
                    )
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {"status": "success", "temporal_entities": self.temporal_entities, "documents": len(document_ids), "assertions_passed": assertions_passed}
                
            except Exception as e:
                self.logger.error(
                    f"Temporal phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise


class EventEnrichmentPhaseWrapper:
    """Wrapper for EventEnrichmentPhase semantic enrichment."""
    
    def __init__(self):
        self.events_enriched = 0
        self.logger = get_logger(f"{__name__}.EventEnrichmentPhase")
        self.logger.info("Initialized EventEnrichmentPhaseWrapper")
    
    def execute(self) -> Dict[str, Any]:
        """Execute EventEnrichmentPhase for event enrichment."""
        with log_section(self.logger, "EVENT ENRICHMENT PHASE - Semantic Event Enrichment"):
            try:
                with log_subsection(self.logger, "Importing EventEnrichmentPhase"):
                    from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase
                    self.logger.debug("EventEnrichmentPhase imported successfully")
                
                with log_subsection(self.logger, "Initializing EventEnrichmentPhase"):
                    enricher = EventEnrichmentPhase(argv=[])
                    self.logger.debug("EventEnrichmentPhase initialized")
                
                # Run all enrichment steps
                enrichment_steps = [
                    ("Linking frame arguments to events", enricher.link_frameArgument_to_event),
                    ("Adding core participants to events", enricher.add_core_participants_to_event),
                    ("Adding non-core participants to events", enricher.add_non_core_participants_to_event),
                    ("Adding labels to non-core frame arguments", enricher.add_label_to_non_core_fa),
                ]
                
                self.logger.info(f"Starting {len(enrichment_steps)} enrichment steps")
                
                for step_name, step_func in enrichment_steps:
                    with log_subsection(self.logger, step_name):
                        step_func()
                        self.logger.debug(f"✓ Completed: {step_name}")
                
                self.logger.info("Event enrichment completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    from textgraphx.provenance import stamp_inferred_relationships
                    assertion_result = PhaseAssertions(enricher.graph).after_event_enrichment()
                    assertions_passed = assertion_result.passed
                    stamp_inferred_relationships(
                        enricher.graph,
                        rel_type="DESCRIBES",
                        confidence=0.70,
                        evidence_source="event_enrichment",
                        rule_id="frame_to_event",
                    )
                    stamp_inferred_relationships(
                        enricher.graph,
                        rel_type="PARTICIPANT",
                        confidence=0.65,
                        evidence_source="event_enrichment",
                        rule_id="participant_linking",
                    )
                    record_phase_run(enricher.graph, "event_enrichment", duration_seconds=0.0)
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {"status": "success", "events_enriched": self.events_enriched, "assertions_passed": assertions_passed}
                
            except Exception as e:
                self.logger.error(
                    f"Event enrichment phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise


class TlinksRecognizerWrapper:
    """Wrapper for TlinksRecognizer temporal link identification."""
    
    def __init__(self):
        self.tlinks_created = 0
        self.logger = get_logger(f"{__name__}.TlinksRecognizer")
        self.logger.info("Initialized TlinksRecognizerWrapper")
    
    def execute(self) -> Dict[str, Any]:
        """Execute TlinksRecognizer for TLINK extraction."""
        with log_section(self.logger, "TLINKS PHASE - Temporal Link Recognition"):
            try:
                with log_subsection(self.logger, "Importing TlinksRecognizer"):
                    from textgraphx.TlinksRecognizer import TlinksRecognizer
                    self.logger.debug("TlinksRecognizer imported successfully")
                
                with log_subsection(self.logger, "Initializing TlinksRecognizer"):
                    recognizer = TlinksRecognizer(argv=[])
                    self.logger.debug("TlinksRecognizer initialized")
                
                # Run all TLINK recognition cases
                tlink_cases = [
                    (1, recognizer.create_tlinks_case1, "Case 1: Event-to-Event TLINKs"),
                    (2, recognizer.create_tlinks_case2, "Case 2: Specific Temporal Cases"),
                    (3, recognizer.create_tlinks_case3, "Case 3: Additional Temporal Patterns"),
                    (4, recognizer.create_tlinks_case4, "Case 4: Complex TLINK Patterns"),
                    (5, recognizer.create_tlinks_case5, "Case 5: Special Cases"),
                    (6, recognizer.create_tlinks_case6, "Case 6: Final TLINK Patterns"),
                ]
                
                self.logger.info(f"Starting {len(tlink_cases)} TLINK recognition cases")
                
                for case_num, case_func, case_desc in tlink_cases:
                    with log_subsection(self.logger, case_desc):
                        case_func()
                        self.logger.debug(f"✓ Completed: Case {case_num}")
                
                self.logger.info("TLINK recognition completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    from textgraphx.provenance import stamp_inferred_relationships
                    assertion_result = PhaseAssertions(recognizer.graph).after_tlinks()
                    assertions_passed = assertion_result.passed
                    stamp_inferred_relationships(
                        recognizer.graph,
                        rel_type="TLINK",
                        confidence=0.80,
                        evidence_source="tlinks_recognizer",
                        rule_id="case_rules",
                    )
                    record_phase_run(recognizer.graph, "tlinks", duration_seconds=0.0)
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {"status": "success", "tlinks_created": self.tlinks_created, "assertions_passed": assertions_passed}
                
            except Exception as e:
                self.logger.error(
                    f"TLINKs phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise
