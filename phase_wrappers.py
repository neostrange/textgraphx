"""
Simplified wrappers for pipeline phases to standardize orchestrator interface.

Each phase has different internal APIs, so these wrappers provide a consistent
execute() method for the orchestrator to call.
"""

import logging
import re
import time
from difflib import SequenceMatcher
from typing import Dict, Any, Optional
from pathlib import Path
from urllib.parse import unquote

import requests

from textgraphx.logging_utils import (
    get_logger, log_section, log_subsection, timer_log, ProgressLogger
)

logger = get_logger(__name__)


def _provenance_violations_from_assertion(assertion_result) -> int:
    if assertion_result is None:
        return 0
    return sum(
        int(check.get("actual", 0))
        for check in getattr(assertion_result, "checks", [])
        if "missing provenance contract fields" in str(check.get("label", ""))
    )


def _phase_thresholds_for_mode(phase_name: str):
    """Build phase assertion thresholds based on runtime mode.

    In review/testing-like modes we enforce strict upper bounds for newly
    introduced TimeML completeness and TLINK consistency checks.
    """
    from textgraphx.phase_assertions import PhaseThresholds

    thresholds = PhaseThresholds()
    try:
        from textgraphx.config import get_config

        mode = str(get_config().runtime.mode or "production").strip().lower()
    except Exception:
        mode = "production"

    strict_modes = {"review", "testing", "test", "ci"}
    if mode not in strict_modes:
        return thresholds

    if phase_name == "temporal":
        thresholds.max_tevents_missing_timeml_core = 0
        thresholds.max_timex_missing_timeml_core = 0
        thresholds.max_signals_missing_text_span = 0
        thresholds.max_tlinks_missing_reltype_canonical = 0
    elif phase_name == "tlinks":
        thresholds.max_tlink_consistency_violations = 0

    return thresholds


class DBpediaResolver:
    """Precision-first resolver for converting plain-text entity labels into DBpedia URIs."""

    _TYPE_QUERY_CLASS = {
        "PERSON": "Person",
        "PER": "Person",
        "ORG": "Organisation",
        "ORGANIZATION": "Organisation",
        "GPE": "Place",
        "LOC": "Place",
        "LOCATION": "Place",
        "FAC": "Place",
    }
    _TYPE_HINTS = {
        "PERSON": {"person", "agent", "artist", "athlete", "officeholder", "scientist", "politician"},
        "PER": {"person", "agent", "artist", "athlete", "officeholder", "scientist", "politician"},
        "ORG": {"organisation", "organization", "company", "bank", "agency", "institution", "publisher"},
        "ORGANIZATION": {"organisation", "organization", "company", "bank", "agency", "institution", "publisher"},
        "GPE": {"place", "location", "country", "city", "region", "settlement", "state"},
        "LOC": {"place", "location", "country", "city", "region", "settlement", "state"},
        "LOCATION": {"place", "location", "country", "city", "region", "settlement", "state"},
        "FAC": {"place", "location", "building", "infrastructure", "airport", "station"},
    }
    _CORPORATE_SUFFIXES = {
        "sa", "plc", "inc", "corp", "corporation", "co", "company", "limited", "ltd", "llc",
        "ag", "nv", "n.v", "group", "holdings", "holding",
    }

    def __init__(
        self,
        lookup_url: str,
        timeout_sec: int,
        max_candidates: int,
        min_similarity: float,
        min_margin: float,
    ):
        self.lookup_url = lookup_url
        self.timeout_sec = max(1, int(timeout_sec))
        self.max_candidates = max(1, int(max_candidates))
        self.min_similarity = float(min_similarity)
        self.min_margin = float(min_margin)

    @classmethod
    def _normalize_text(cls, value: Optional[str], strip_suffix: bool = False) -> str:
        text = unquote(str(value or "")).replace("_", " ").strip().lower()
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        tokens = [token for token in text.split() if token]
        if strip_suffix:
            while tokens and tokens[-1] in cls._CORPORATE_SUFFIXES:
                tokens.pop()
        return " ".join(tokens)

    @classmethod
    def _resource_basename(cls, resource_uri: Optional[str]) -> str:
        if not resource_uri:
            return ""
        return unquote(str(resource_uri).rstrip("/").rsplit("/", 1)[-1]).replace("_", " ")

    @staticmethod
    def _first_value(value: Any) -> Any:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    @classmethod
    def _extract_candidates(cls, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        raw_candidates = payload.get("docs") or payload.get("results") or payload.get("resources") or []
        candidates = []
        for item in raw_candidates:
            resource_uri = cls._first_value(item.get("resource") or item.get("uri"))
            label = cls._first_value(item.get("label") or item.get("name"))
            description = cls._first_value(item.get("comment") or item.get("description"))
            ref_count_raw = cls._first_value(item.get("refCount") or item.get("ref_count") or 0)
            try:
                ref_count = int(ref_count_raw)
            except Exception:
                ref_count = 0

            class_values = []
            for class_item in item.get("classes", []) or []:
                if isinstance(class_item, dict):
                    label_value = class_item.get("label") or class_item.get("uri") or ""
                else:
                    label_value = class_item
                if label_value:
                    class_values.append(str(label_value).lower())
            for type_name in item.get("typeName", []) or []:
                if type_name:
                    class_values.append(str(type_name).lower())

            if resource_uri:
                candidates.append(
                    {
                        "resource_uri": str(resource_uri),
                        "label": str(label or cls._resource_basename(resource_uri)),
                        "description": description,
                        "ref_count": ref_count,
                        "classes": sorted(set(class_values)),
                    }
                )
        return candidates

    def lookup_candidates(self, surface_form: str, expected_type: Optional[str]) -> list[Dict[str, Any]]:
        params = {
            "QueryString": surface_form,
            "MaxHits": self.max_candidates,
        }
        query_class = self._TYPE_QUERY_CLASS.get(str(expected_type or "").upper())
        headers = {"Accept": "application/json"}

        response = requests.get(
            self.lookup_url,
            params={**params, **({"QueryClass": query_class} if query_class else {})},
            headers=headers,
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        candidates = self._extract_candidates(response.json())
        if candidates or not query_class:
            return candidates

        response = requests.get(
            self.lookup_url,
            params=params,
            headers=headers,
            timeout=self.timeout_sec,
        )
        response.raise_for_status()
        return self._extract_candidates(response.json())

    def _type_match(self, expected_type: Optional[str], candidate: Dict[str, Any]) -> Optional[bool]:
        hints = self._TYPE_HINTS.get(str(expected_type or "").upper())
        if not hints:
            return None
        candidate_classes = candidate.get("classes") or []
        if not candidate_classes:
            return None
        classes_text = " ".join(candidate_classes)
        return any(hint in classes_text for hint in hints)

    @staticmethod
    def _similarity(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio()

    def _score_candidate(self, surface_form: str, expected_type: Optional[str], candidate: Dict[str, Any]) -> Dict[str, Any]:
        surface_norm = self._normalize_text(surface_form)
        surface_core = self._normalize_text(surface_form, strip_suffix=True)
        label = candidate.get("label") or self._resource_basename(candidate.get("resource_uri"))
        label_norm = self._normalize_text(label)
        label_core = self._normalize_text(label, strip_suffix=True)
        resource_label = self._resource_basename(candidate.get("resource_uri"))
        resource_norm = self._normalize_text(resource_label)

        similarity = max(
            self._similarity(surface_norm, label_norm),
            self._similarity(surface_core, label_core),
            self._similarity(surface_norm, resource_norm),
            self._similarity(surface_core, resource_norm),
        )
        exact_match = bool(surface_norm and (surface_norm == label_norm or surface_core == label_core))
        type_match = self._type_match(expected_type, candidate)
        ref_count = int(candidate.get("ref_count") or 0)
        ref_bonus = min(ref_count, 10000) / 10000.0 * 0.03
        score = similarity + (0.04 if exact_match else 0.0) + (0.03 if type_match else 0.0) + ref_bonus
        if type_match is False:
            score -= 0.12

        return {
            **candidate,
            "label": label,
            "similarity": similarity,
            "exact_match": exact_match,
            "type_match": type_match,
            "score": score,
        }

    def resolve(self, surface_form: Optional[str], expected_type: Optional[str] = None) -> Dict[str, Any]:
        surface_form = str(surface_form or "").strip()
        if not surface_form:
            return {
                "status": "no_query",
                "reason": "empty_surface_form",
                "surface_form": surface_form,
                "candidate_count": 0,
                "confidence": None,
                "resource_uri": None,
            }

        if surface_form.startswith(("http://dbpedia.org/resource/", "https://dbpedia.org/resource/")):
            return {
                "status": "resolved_existing_uri",
                "reason": "existing_dbpedia_uri",
                "surface_form": surface_form,
                "candidate_count": 1,
                "confidence": 1.0,
                "resource_uri": surface_form,
                "resolved_label": self._resource_basename(surface_form),
                "top_candidate_uri": surface_form,
                "top_candidate_label": self._resource_basename(surface_form),
            }

        if surface_form.startswith(("http://", "https://")):
            return {
                "status": "skipped_non_dbpedia_uri",
                "reason": "non_dbpedia_uri",
                "surface_form": surface_form,
                "candidate_count": 0,
                "confidence": None,
                "resource_uri": None,
            }

        candidates = self.lookup_candidates(surface_form, expected_type)
        if not candidates:
            return {
                "status": "no_match",
                "reason": "lookup_returned_no_candidates",
                "surface_form": surface_form,
                "candidate_count": 0,
                "confidence": None,
                "resource_uri": None,
            }

        scored = sorted(
            (self._score_candidate(surface_form, expected_type, candidate) for candidate in candidates),
            key=lambda item: item["score"],
            reverse=True,
        )
        top = scored[0]
        second = scored[1] if len(scored) > 1 else None
        margin = top["score"] - (second["score"] if second else 0.0)

        if top["type_match"] is False:
            return {
                "status": "no_match",
                "reason": "top_candidate_type_mismatch",
                "surface_form": surface_form,
                "candidate_count": len(scored),
                "confidence": None,
                "resource_uri": None,
                "top_candidate_uri": top.get("resource_uri"),
                "top_candidate_label": top.get("label"),
            }

        similarity_floor = self.min_similarity - (0.03 if top["exact_match"] else 0.0)
        if top["similarity"] < similarity_floor:
            return {
                "status": "no_match",
                "reason": "top_candidate_below_similarity_threshold",
                "surface_form": surface_form,
                "candidate_count": len(scored),
                "confidence": None,
                "resource_uri": None,
                "top_candidate_uri": top.get("resource_uri"),
                "top_candidate_label": top.get("label"),
            }

        if second and margin < self.min_margin:
            strong_top = top["exact_match"] and top["type_match"] is True and not second["exact_match"]
            if not strong_top:
                return {
                    "status": "ambiguous",
                    "reason": "top_candidates_too_close",
                    "surface_form": surface_form,
                    "candidate_count": len(scored),
                    "confidence": None,
                    "resource_uri": None,
                    "top_candidate_uri": top.get("resource_uri"),
                    "top_candidate_label": top.get("label"),
                }

        if not top["exact_match"] and top["type_match"] is not True and top["similarity"] < 0.96:
            return {
                "status": "ambiguous",
                "reason": "insufficient_non_exact_evidence",
                "surface_form": surface_form,
                "candidate_count": len(scored),
                "confidence": None,
                "resource_uri": None,
                "top_candidate_uri": top.get("resource_uri"),
                "top_candidate_label": top.get("label"),
            }

        confidence = min(
            0.999,
            0.60 * top["similarity"]
            + 0.20 * (1.0 if top["exact_match"] else 0.0)
            + 0.10 * (1.0 if top["type_match"] else 0.5 if top["type_match"] is None else 0.0)
            + 0.10 * min(1.0, margin / max(self.min_margin, 0.01)),
        )
        return {
            "status": "resolved",
            "reason": "accepted_top_candidate",
            "surface_form": surface_form,
            "candidate_count": len(scored),
            "confidence": round(confidence, 4),
            "resource_uri": top.get("resource_uri"),
            "resolved_label": top.get("label"),
            "top_candidate_uri": top.get("resource_uri"),
            "top_candidate_label": top.get("label"),
        }


class GraphBasedNLPWrapper:
    """Wrapper for GraphBasedNLP ingestion phase."""
    
    def __init__(
        self,
        model_name: str = "en_core_web_trf",
        require_neo4j: bool = True,
        strict_transition_gate: bool = False,
    ):
        self.model_name = model_name
        self.require_neo4j = require_neo4j
        self.strict_transition_gate = strict_transition_gate
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
                    
                    # Count input files expected by GraphBasedNLP.
                    xml_files = list(Path(directory).glob("*.xml"))
                    txt_files = list(Path(directory).glob("*.txt"))
                    naf_files = list(Path(directory).glob("*.naf"))
                    total_files = len(xml_files) + len(txt_files) + len(naf_files)
                    self.logger.info(
                        "Found %s documents (XML: %s, TXT: %s, NAF: %s)",
                        total_files,
                        len(xml_files),
                        len(txt_files),
                        len(naf_files),
                    )
                    
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
                    assertion_result = PhaseAssertions(
                        nlp.graph,
                        strict_transition_gate=self.strict_transition_gate,
                    ).after_ingestion()
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
    
    def __init__(self, strict_transition_gate: bool = False):
        self.strict_transition_gate = strict_transition_gate
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

                # Execute numeric/value refinement passes as a family so VALUE
                # and NUMERIC semantics are materialized before event enrichment.
                with log_subsection(self.logger, "Numeric/value normalization and materialization"):
                    refiner.run_rule_family("numeric_value")
                    self.logger.debug("✓ Completed: numeric_value family")

                # Nominal semantic-head materialization/profile passes. These
                # populate nominalSemanticHead* fields used by evaluation and
                # downstream semantic analysis.
                with log_subsection(self.logger, "Nominal semantic-head and profile enrichment"):
                    refiner.run_rule_family("nominal_mentions")
                    self.logger.debug("✓ Completed: nominal_mentions family")

                # Mention boundary cleanup: trim trailing punctuation tokens
                # from entity spans, then label discourse-relevant entities.
                # These run after numeric_value so VALUE nodes are already set.
                with log_subsection(self.logger, "Mention boundary cleanup"):
                    refiner.run_rule_family("mention_cleanup")
                    self.logger.debug("✓ Completed: mention_cleanup family")

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
                    assertion_result = PhaseAssertions(
                        refiner.graph,
                        strict_transition_gate=self.strict_transition_gate,
                    ).after_refinement()
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
    
    def __init__(self, strict_transition_gate: bool = False):
        self.strict_transition_gate = strict_transition_gate
        self.temporal_entities = 0
        self.logger = get_logger(f"{__name__}.TemporalPhase")
        self.logger.info("Initialized TemporalPhaseWrapper")

    @staticmethod
    def _normalize_doc_id(value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.isdigit():
                return int(stripped)
            return stripped
        return value
    
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
                                    document_ids.add(self._normalize_doc_id(doc_id))
                            elif item is not None:
                                document_ids.add(self._normalize_doc_id(item))
                    else:
                        self.logger.warning("No annotated text found")
                    
                    self.logger.info(f"Identified {len(document_ids)} unique documents")
                
                # Process each document with detailed logging
                if document_ids:
                    with log_subsection(self.logger, f"Processing temporal extraction for {len(document_ids)} documents"):
                        progress = ProgressLogger(self.logger, len(document_ids) * 7, "Temporal Operations")
                        doc_failures = []
                        
                        for doc_id in sorted(
                            document_ids,
                            key=lambda v: (0, v) if isinstance(v, int) else (1, str(v)),
                        ):
                            self.logger.debug(f"Processing document: {doc_id}")
                            
                            try:
                                temporal.create_DCT_node(doc_id)
                                progress.update(1, f"Created DCT node for {doc_id}")
                                
                                temporal.create_tevents2(doc_id)
                                progress.update(1, f"Created temporal events for {doc_id}")

                                if hasattr(temporal, "create_event_mentions2"):
                                    temporal.create_event_mentions2(doc_id)
                                    progress.update(1, f"Created event mentions for {doc_id}")
                                else:
                                    progress.update(1, f"Skipped event mentions (unsupported) for {doc_id}")

                                temporal.create_signals2(doc_id)
                                progress.update(1, f"Created temporal signals for {doc_id}")
                                
                                temporal.create_timexes2(doc_id)
                                progress.update(1, f"Created temporal expressions for {doc_id}")
                                
                                temporal.create_tlinks_e2e(doc_id)
                                progress.update(1, f"Created event-to-event temporal links for {doc_id}")
                                
                                temporal.create_tlinks_e2t(doc_id)
                                progress.update(1, f"Created event-to-time temporal links for {doc_id}")
                                
                                self.logger.debug(f"✓ Completed temporal processing for {doc_id}")
                            except Exception as doc_error:
                                doc_failures.append((doc_id, f"{type(doc_error).__name__}: {doc_error}"))
                                self.logger.error(
                                    f"Error processing document {doc_id}: {type(doc_error).__name__}: {doc_error}",
                                    exc_info=False
                                )
                        
                        progress.finish()
                        if doc_failures:
                            failed_docs = ", ".join(str(d[0]) for d in doc_failures)
                            raise RuntimeError(
                                f"Temporal extraction failed for {len(doc_failures)} document(s): {failed_docs}"
                            )
                
                self.logger.info("Temporal extraction completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                provenance_violations = 0
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    from textgraphx.provenance import stamp_inferred_relationships
                    stamp_inferred_relationships(
                        temporal.graph,
                        rel_type="TLINK",
                        confidence=0.75,
                        evidence_source="temporal_phase",
                        rule_id="temporal_xml_tlinks",
                        source_kind="service",
                        conflict_policy="merge",
                    )
                    assertion_result = PhaseAssertions(
                        temporal.graph,
                        thresholds=_phase_thresholds_for_mode("temporal"),
                        strict_transition_gate=self.strict_transition_gate,
                        enforce_provenance_contracts=True,
                    ).after_temporal()
                    assertions_passed = assertion_result.passed
                    provenance_violations = _provenance_violations_from_assertion(assertion_result)
                    record_phase_run(
                        temporal.graph, "temporal",
                        duration_seconds=0.0,
                        documents_processed=len(document_ids),
                    )
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {
                    "status": "success",
                    "temporal_entities": self.temporal_entities,
                    "documents": len(document_ids),
                    "assertions_passed": assertions_passed,
                    "provenance_violations": provenance_violations,
                }
                
            except Exception as e:
                self.logger.error(
                    f"Temporal phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise


class EventEnrichmentPhaseWrapper:
    """Wrapper for EventEnrichmentPhase semantic enrichment."""
    
    def __init__(self, strict_transition_gate: bool = False):
        self.strict_transition_gate = strict_transition_gate
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
                    ("Deriving causal links from ARGM-CAU", enricher.derive_clinks_from_causal_arguments),
                    ("Deriving subordinating links from ARGM-DSP", enricher.derive_slinks_from_reported_speech),
                    ("Enriching event mention properties (PHASE 2)", enricher.enrich_event_mention_properties),
                ]
                
                self.logger.info(f"Starting {len(enrichment_steps)} enrichment steps")
                
                for step_name, step_func in enrichment_steps:
                    with log_subsection(self.logger, step_name):
                        step_func()
                        self.logger.debug(f"✓ Completed: {step_name}")
                
                self.logger.info("Event enrichment completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                provenance_violations = 0
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    from textgraphx.provenance import stamp_inferred_relationships
                    stamp_inferred_relationships(
                        enricher.graph,
                        rel_type="DESCRIBES",
                        confidence=0.70,
                        evidence_source="event_enrichment",
                        rule_id="frame_to_event",
                        source_kind="rule",
                        conflict_policy="additive",
                    )
                    stamp_inferred_relationships(
                        enricher.graph,
                        rel_type="FRAME_DESCRIBES_EVENT",
                        confidence=0.70,
                        evidence_source="event_enrichment",
                        rule_id="frame_to_event",
                        source_kind="rule",
                        conflict_policy="additive",
                    )
                    stamp_inferred_relationships(
                        enricher.graph,
                        rel_type="PARTICIPANT",
                        confidence=0.65,
                        evidence_source="event_enrichment",
                        rule_id="participant_linking",
                        source_kind="rule",
                        conflict_policy="additive",
                    )
                    stamp_inferred_relationships(
                        enricher.graph,
                        rel_type="EVENT_PARTICIPANT",
                        confidence=0.65,
                        evidence_source="event_enrichment",
                        rule_id="participant_linking",
                        source_kind="rule",
                        conflict_policy="additive",
                    )
                    assertion_result = PhaseAssertions(
                        enricher.graph,
                        strict_transition_gate=self.strict_transition_gate,
                        enforce_provenance_contracts=True,
                    ).after_event_enrichment()
                    assertions_passed = assertion_result.passed
                    provenance_violations = _provenance_violations_from_assertion(assertion_result)
                    record_phase_run(enricher.graph, "event_enrichment", duration_seconds=0.0)
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {
                    "status": "success",
                    "events_enriched": self.events_enriched,
                    "assertions_passed": assertions_passed,
                    "provenance_violations": provenance_violations,
                }
                
            except Exception as e:
                self.logger.error(
                    f"Event enrichment phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise


class DBpediaEnrichmentPhaseWrapper:
    """Optional phase that uses DBpedia Spotlight for document-level resolution, then enriches via SPARQL."""

    def __init__(self, strict_transition_gate: bool = False):
        self.strict_transition_gate = strict_transition_gate
        self.logger = get_logger(f"{__name__}.DBpediaEnrichment")
        self.logger.info("Initialized DBpediaEnrichmentPhaseWrapper")

    @staticmethod
    def _extract_row_values(payload: Dict[str, Any]) -> Dict[str, Any]:
        bindings = payload.get("results", {}).get("bindings", [])
        if not bindings:
            return {"abstract": None, "types": []}
        row = bindings[0]
        abstract = row.get("abstract", {}).get("value")
        types_str = row.get("types", {}).get("value", "")
        type_labels = [item.strip() for item in types_str.split("|") if item.strip()]
        return {"abstract": abstract, "types": type_labels}

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        text = unquote(str(value or "")).replace("_", " ").strip().lower()
        text = re.sub(r"[^a-z0-9\s]+", " ", text)
        return " ".join(text.split())

    @staticmethod
    def _parse_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _parse_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _fetch_dbpedia_metadata(self, endpoint_url: str, resource_uri: str, timeout_sec: int) -> Dict[str, Any]:
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?abstract (GROUP_CONCAT(DISTINCT ?typeLabel; separator="|") AS ?types)
        WHERE {{
          OPTIONAL {{ <{resource_uri}> dbo:abstract ?abstract . FILTER(lang(?abstract) = 'en') }}
          OPTIONAL {{
            <{resource_uri}> rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
            ?type rdfs:label ?typeLabel .
            FILTER(lang(?typeLabel) = 'en')
          }}
        }}
        GROUP BY ?abstract
        LIMIT 1
        """
        response = requests.get(
            endpoint_url,
            params={
                "query": query,
                "format": "application/sparql-results+json",
            },
            timeout=timeout_sec,
        )
        response.raise_for_status()
        return self._extract_row_values(response.json())

    def _annotate_document(
        self,
        spotlight_url: str,
        document_text: str,
        timeout_sec: int,
        confidence: float,
        support: int,
    ) -> list[Dict[str, Any]]:
        response = requests.post(
            spotlight_url,
            data={
                "text": document_text,
                "confidence": confidence,
                "support": support,
            },
            headers={"Accept": "application/json"},
            timeout=timeout_sec,
        )
        response.raise_for_status()
        payload = response.json()
        raw_resources = payload.get("Resources") or []
        if isinstance(raw_resources, dict):
            raw_resources = [raw_resources]

        annotations = []
        for item in raw_resources:
            uri = item.get("@URI") or item.get("URI")
            surface_form = item.get("@surfaceForm") or item.get("surfaceForm") or item.get("label")
            if not uri or not surface_form:
                continue
            annotations.append(
                {
                    "resource_uri": str(uri),
                    "surface_form": str(surface_form),
                    "offset": self._parse_int(item.get("@offset") or item.get("offset")),
                    "similarity": self._parse_float(item.get("@similarityScore") or item.get("similarityScore")),
                    "support": self._parse_int(item.get("@support") or item.get("support")),
                    "types": str(item.get("@types") or item.get("types") or ""),
                }
            )
        return annotations

    def _annotation_type_match(self, expected_type: Optional[str], annotation_types: str) -> Optional[bool]:
        hints = DBpediaResolver._TYPE_HINTS.get(str(expected_type or "").upper())
        if not hints:
            return None
        normalized_types = self._normalize_text(annotation_types)
        if not normalized_types:
            return None
        return any(hint in normalized_types for hint in hints)

    def _resolve_from_document_annotations(
        self,
        row: Dict[str, Any],
        document_text: str,
        annotations: list[Dict[str, Any]],
        min_similarity: float,
    ) -> Dict[str, Any]:
        lookup_text = str(row.get("value") or row.get("lookup_text") or "").strip()
        if not lookup_text:
            return {
                "status": "no_query",
                "reason": "empty_surface_form",
                "surface_form": lookup_text,
                "candidate_count": 0,
                "confidence": None,
                "resource_uri": None,
            }

        dbpedia_resource = str(row.get("dbpedia_resource") or "").strip()
        kb_id = str(row.get("kb_id") or "").strip()
        if dbpedia_resource:
            return {
                "status": "resolved_existing_uri",
                "reason": "existing_dbpedia_uri",
                "surface_form": lookup_text,
                "candidate_count": 1,
                "confidence": 1.0,
                "resource_uri": dbpedia_resource,
                "resolved_label": lookup_text,
                "top_candidate_uri": dbpedia_resource,
                "top_candidate_label": lookup_text,
            }
        if kb_id.startswith(("http://dbpedia.org/resource/", "https://dbpedia.org/resource/")):
            return {
                "status": "resolved_existing_uri",
                "reason": "existing_dbpedia_uri",
                "surface_form": lookup_text,
                "candidate_count": 1,
                "confidence": 1.0,
                "resource_uri": kb_id,
                "resolved_label": lookup_text,
                "top_candidate_uri": kb_id,
                "top_candidate_label": lookup_text,
            }

        row_start = self._parse_int(row.get("start_char"), -1)
        row_end = self._parse_int(row.get("end_char"), -1)
        expected_type = row.get("entity_type")
        normalized_lookup = self._normalize_text(lookup_text)
        span_text = ""
        if row_start >= 0 and row_end > row_start:
            span_text = document_text[row_start:row_end]
        normalized_span = self._normalize_text(span_text)

        candidates = []
        for annotation in annotations:
            offset = self._parse_int(annotation.get("offset"), -1)
            surface_form = str(annotation.get("surface_form") or "")
            normalized_surface = self._normalize_text(surface_form)
            if offset != row_start:
                continue
            if normalized_surface not in {normalized_lookup, normalized_span}:
                continue
            annotation_end = offset + len(surface_form)
            if row_end > 0 and abs(annotation_end - row_end) > 1:
                continue
            type_match = self._annotation_type_match(expected_type, str(annotation.get("types") or ""))
            candidates.append(
                {
                    **annotation,
                    "type_match": type_match,
                }
            )

        if not candidates:
            return {
                "status": "no_match",
                "reason": "spotlight_found_no_aligned_annotation",
                "surface_form": lookup_text,
                "candidate_count": 0,
                "confidence": None,
                "resource_uri": None,
            }

        candidates.sort(
            key=lambda item: (
                self._parse_float(item.get("similarity"), 0.0),
                self._parse_int(item.get("support"), 0),
            ),
            reverse=True,
        )
        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None

        if top.get("type_match") is False:
            return {
                "status": "no_match",
                "reason": "spotlight_type_mismatch",
                "surface_form": lookup_text,
                "candidate_count": len(candidates),
                "confidence": None,
                "resource_uri": None,
                "top_candidate_uri": top.get("resource_uri"),
                "top_candidate_label": top.get("surface_form"),
            }

        similarity = self._parse_float(top.get("similarity"), 0.0)
        if similarity < min_similarity:
            return {
                "status": "no_match",
                "reason": "spotlight_similarity_below_threshold",
                "surface_form": lookup_text,
                "candidate_count": len(candidates),
                "confidence": None,
                "resource_uri": None,
                "top_candidate_uri": top.get("resource_uri"),
                "top_candidate_label": top.get("surface_form"),
            }

        if second:
            margin = similarity - self._parse_float(second.get("similarity"), 0.0)
            if margin < 0.05 and second.get("resource_uri") != top.get("resource_uri"):
                return {
                    "status": "ambiguous",
                    "reason": "spotlight_candidates_too_close",
                    "surface_form": lookup_text,
                    "candidate_count": len(candidates),
                    "confidence": None,
                    "resource_uri": None,
                    "top_candidate_uri": top.get("resource_uri"),
                    "top_candidate_label": top.get("surface_form"),
                }

        return {
            "status": "resolved",
            "reason": "spotlight_document_context",
            "surface_form": lookup_text,
            "candidate_count": len(candidates),
            "confidence": round(similarity, 4),
            "resource_uri": top.get("resource_uri"),
            "resolved_label": top.get("surface_form"),
            "top_candidate_uri": top.get("resource_uri"),
            "top_candidate_label": top.get("surface_form"),
        }

    @staticmethod
    def _write_resolution(graph: Any, element_id: int, resolution: Dict[str, Any], lookup_text: str) -> None:
        graph.run(
            """
            MATCH (n)
            WHERE id(n) = $node_id
            OPTIONAL MATCH (n)-[:REFERS_TO]->(e:Entity)
            SET n.dbpedia_lookup_text = $lookup_text,
                n.dbpedia_resolution_status = $resolution_status,
                n.dbpedia_resolution_reason = $resolution_reason,
                n.dbpedia_resolution_source = $resolution_source,
                n.dbpedia_resolution_candidate_count = $candidate_count,
                n.dbpedia_resolution_confidence = $confidence,
                n.dbpedia_resolution_label = $resolved_label,
                n.dbpedia_resource = $resource_uri,
                n.dbpedia_top_candidate_uri = $top_candidate_uri,
                n.dbpedia_top_candidate_label = $top_candidate_label,
                n.dbpedia_resolution_checked_at = timestamp()
            FOREACH (entity IN CASE WHEN e IS NULL THEN [] ELSE [e] END |
                SET entity.dbpedia_lookup_text = $lookup_text,
                    entity.dbpedia_resolution_status = $resolution_status,
                    entity.dbpedia_resolution_reason = $resolution_reason,
                    entity.dbpedia_resolution_source = $resolution_source,
                    entity.dbpedia_resolution_candidate_count = $candidate_count,
                    entity.dbpedia_resolution_confidence = $confidence,
                    entity.dbpedia_resolution_label = $resolved_label,
                    entity.dbpedia_resource = $resource_uri,
                    entity.dbpedia_top_candidate_uri = $top_candidate_uri,
                    entity.dbpedia_top_candidate_label = $top_candidate_label,
                    entity.dbpedia_resolution_checked_at = timestamp()
            )
            """,
            {
                "node_id": element_id,
                "lookup_text": lookup_text,
                "resolution_status": resolution.get("status"),
                "resolution_reason": resolution.get("reason"),
                "resolution_source": "dbpedia_spotlight",
                "candidate_count": resolution.get("candidate_count"),
                "confidence": resolution.get("confidence"),
                "resolved_label": resolution.get("resolved_label"),
                "resource_uri": resolution.get("resource_uri"),
                "top_candidate_uri": resolution.get("top_candidate_uri"),
                "top_candidate_label": resolution.get("top_candidate_label"),
            },
        )

    @staticmethod
    def _write_enrichment(graph: Any, element_id: int, resource_uri: str, values: Dict[str, Any]) -> None:
        graph.run(
            """
            MATCH (n)
            WHERE id(n) = $node_id
            OPTIONAL MATCH (n)-[:REFERS_TO]->(e:Entity)
            SET n.dbpedia_source = 'dbpedia_sparql',
                n.dbpedia_resource = $resource_uri,
                n.dbpedia_abstract = $abstract,
                n.dbpedia_types = $types,
                n.dbpedia_enriched_at = timestamp()
            FOREACH (entity IN CASE WHEN e IS NULL THEN [] ELSE [e] END |
                SET entity.dbpedia_source = 'dbpedia_sparql',
                    entity.dbpedia_resource = $resource_uri,
                    entity.dbpedia_abstract = $abstract,
                    entity.dbpedia_types = $types,
                    entity.dbpedia_enriched_at = timestamp()
            )
            """,
            {
                "node_id": element_id,
                "resource_uri": resource_uri,
                "abstract": values.get("abstract"),
                "types": values.get("types", []),
            },
        )

    def execute(self) -> Dict[str, Any]:
        """Execute optional DBpedia resolution and enrichment for entity mentions."""
        from textgraphx.config import get_config
        from textgraphx.neo4j_client import make_graph_from_config

        cfg = get_config()
        if not cfg.features.enable_dbpedia_enrichment:
            self.logger.info("DBpedia enrichment skipped (features.enable_dbpedia_enrichment=false)")
            return {
                "status": "skipped",
                "reason": "disabled_by_config",
                "entities_considered": 0,
                "entities_enriched": 0,
            }

        with log_section(self.logger, "DBPEDIA ENRICHMENT PHASE - Spotlight + SPARQL Metadata"):
            graph = make_graph_from_config()
            endpoint_url = cfg.services.dbpedia_sparql_url
            spotlight_url = cfg.services.dbpedia_spotlight_url
            timeout_sec = max(1, int(cfg.services.dbpedia_timeout_sec))
            limit = max(1, int(cfg.services.dbpedia_max_entities_per_run))
            spotlight_confidence = float(cfg.services.dbpedia_spotlight_confidence)
            spotlight_support = max(0, int(cfg.services.dbpedia_spotlight_support))
            min_similarity = float(cfg.services.dbpedia_spotlight_min_similarity)
            entities_considered = 0
            entities_enriched = 0
            failures = 0
            resolved_existing_uri = 0
            resolved_spotlight = 0
            ambiguous = 0
            no_match = 0
            skipped = 0
            documents_annotated = 0
            metadata_cache: Dict[str, Dict[str, Any]] = {}

            try:
                with log_subsection(self.logger, "Collecting named entities for DBpedia Spotlight analysis"):
                    rows = graph.run(
                        """
                        MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:PARTICIPATES_IN]->(n:NamedEntity)
                        WHERE coalesce(d.text, '') <> ''
                        WITH d, n,
                             min(toInteger(tok.index)) AS start_char,
                             max(toInteger(tok.end_index)) AS end_char,
                             min(tok.tok_index_doc) AS start_tok,
                             max(tok.tok_index_doc) AS end_tok
                        RETURN d.id AS doc_id,
                               d.text AS document_text,
                               id(n) AS element_id,
                               coalesce(n.type, '') AS entity_type,
                               coalesce(n.normal_term, n.value, n.head, n.kb_id, '') AS lookup_text,
                               n.value AS value,
                               coalesce(n.kb_id, '') AS kb_id,
                               coalesce(n.dbpedia_resource, '') AS dbpedia_resource,
                               start_char,
                               end_char,
                               start_tok,
                               end_tok
                        ORDER BY doc_id, start_tok
                        LIMIT $limit
                        """,
                        {"limit": limit},
                    ).data()
                    entities_considered = len(rows)
                    self.logger.info("Found %s named entities for DBpedia Spotlight analysis", entities_considered)

                rows_by_doc: Dict[str, Dict[str, Any]] = {}
                for row in rows:
                    doc_key = str(row.get("doc_id"))
                    bucket = rows_by_doc.setdefault(
                        doc_key,
                        {
                            "document_text": str(row.get("document_text") or ""),
                            "rows": [],
                        },
                    )
                    bucket["rows"].append(row)

                progress = ProgressLogger(self.logger, max(1, entities_considered), "DBpedia enrichment")
                for doc_key, doc_payload in rows_by_doc.items():
                    document_text = doc_payload["document_text"]
                    doc_rows = doc_payload["rows"]
                    unresolved_rows = [
                        row for row in doc_rows
                        if not str(row.get("dbpedia_resource") or "").strip()
                        and not str(row.get("kb_id") or "").startswith(("http://dbpedia.org/resource/", "https://dbpedia.org/resource/"))
                    ]
                    annotations: list[Dict[str, Any]] = []
                    if unresolved_rows:
                        annotations = self._annotate_document(
                            spotlight_url=spotlight_url,
                            document_text=document_text,
                            timeout_sec=timeout_sec,
                            confidence=spotlight_confidence,
                            support=spotlight_support,
                        )
                        documents_annotated += 1
                        self.logger.debug(
                            "Spotlight annotated doc=%s with %s resources",
                            doc_key,
                            len(annotations),
                        )

                    for row in doc_rows:
                        element_id = self._parse_int(row.get("element_id"), -1)
                        lookup_text = str(row.get("lookup_text") or row.get("value") or "").strip()
                        try:
                            resolution = self._resolve_from_document_annotations(
                                row=row,
                                document_text=document_text,
                                annotations=annotations,
                                min_similarity=min_similarity,
                            )
                            self._write_resolution(graph, element_id, resolution, lookup_text)

                            status = resolution.get("status")
                            if status == "resolved_existing_uri":
                                resolved_existing_uri += 1
                            elif status == "resolved":
                                resolved_spotlight += 1
                            elif status == "ambiguous":
                                ambiguous += 1
                            elif status in {"no_match", "no_query"}:
                                no_match += 1
                            else:
                                skipped += 1

                            resource_uri = resolution.get("resource_uri")
                            if resource_uri:
                                if resource_uri not in metadata_cache:
                                    metadata_cache[resource_uri] = self._fetch_dbpedia_metadata(
                                        endpoint_url,
                                        resource_uri,
                                        timeout_sec,
                                    )
                                self._write_enrichment(graph, element_id, resource_uri, metadata_cache[resource_uri])
                                entities_enriched += 1
                        except Exception as exc:
                            failures += 1
                            self.logger.warning("DBpedia enrichment failed for %s: %s", lookup_text or element_id, exc)
                        finally:
                            progress.update(1, f"entity={lookup_text or element_id}")

                progress.finish()

                assertions_passed = None
                try:
                    from textgraphx.phase_assertions import record_phase_run

                    record_phase_run(
                        graph,
                        "dbpedia_enrichment",
                        duration_seconds=0.0,
                        documents_processed=documents_annotated,
                    )
                    assertions_passed = True
                except Exception:
                    self.logger.debug("Phase marker unavailable for dbpedia_enrichment", exc_info=True)

                self.logger.info(
                    "DBpedia enrichment complete: considered=%s documents_annotated=%s resolved_existing=%s resolved_spotlight=%s ambiguous=%s no_match=%s skipped=%s enriched=%s failures=%s",
                    entities_considered,
                    documents_annotated,
                    resolved_existing_uri,
                    resolved_spotlight,
                    ambiguous,
                    no_match,
                    skipped,
                    entities_enriched,
                    failures,
                )
                return {
                    "status": "success",
                    "entities_considered": entities_considered,
                    "documents_annotated": documents_annotated,
                    "resolved_existing_uri": resolved_existing_uri,
                    "resolved_spotlight": resolved_spotlight,
                    "resolved_lookup": resolved_spotlight,
                    "ambiguous": ambiguous,
                    "no_match": no_match,
                    "skipped": skipped,
                    "entities_enriched": entities_enriched,
                    "failures": failures,
                    "assertions_passed": assertions_passed,
                }
            finally:
                close_fn = getattr(graph, "close", None)
                if callable(close_fn):
                    close_fn()


class TlinksRecognizerWrapper:
    """Wrapper for TlinksRecognizer temporal link identification."""
    
    def __init__(self, strict_transition_gate: bool = False):
        self.strict_transition_gate = strict_transition_gate
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

                with log_subsection(self.logger, "Normalize TLINK relation inventory"):
                    recognizer.normalize_tlink_reltypes()
                    self.logger.debug("✓ Completed: TLINK relType normalization")

                suppressed_tlinks = 0
                with log_subsection(self.logger, "Suppress contradictory TLINKs"):
                    suppression_rows = recognizer.suppress_tlink_conflicts()
                    if suppression_rows:
                        suppressed_tlinks = suppression_rows[0].get("suppressed", 0)
                    self.logger.debug("✓ Completed: TLINK conflict suppression (%d suppressed)", suppressed_tlinks)
                
                self.logger.info("TLINK recognition completed successfully")

                # Phase assertions (Item 5) and run marker (Item 7)
                assertions_passed = None
                provenance_violations = 0
                try:
                    from textgraphx.phase_assertions import PhaseAssertions, record_phase_run
                    from textgraphx.provenance import stamp_inferred_relationships
                    stamp_inferred_relationships(
                        recognizer.graph,
                        rel_type="TLINK",
                        confidence=0.80,
                        evidence_source="tlinks_recognizer",
                        rule_id="case_rules",
                        source_kind="rule",
                        conflict_policy="additive",
                    )
                    assertion_result = PhaseAssertions(
                        recognizer.graph,
                        thresholds=_phase_thresholds_for_mode("tlinks"),
                        strict_transition_gate=self.strict_transition_gate,
                        enforce_provenance_contracts=True,
                    ).after_tlinks()
                    assertions_passed = assertion_result.passed
                    provenance_violations = _provenance_violations_from_assertion(assertion_result)
                    record_phase_run(recognizer.graph, "tlinks", duration_seconds=0.0)
                except Exception:
                    self.logger.debug("Phase assertions/marker unavailable", exc_info=True)

                return {
                    "status": "success",
                    "tlinks_created": self.tlinks_created,
                    "suppressed_tlinks": suppressed_tlinks,
                    "assertions_passed": assertions_passed,
                    "provenance_violations": provenance_violations,
                }
                
            except Exception as e:
                self.logger.error(
                    f"TLINKs phase failed: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise
