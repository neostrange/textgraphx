# textgraphx Architecture Overview

This document summarizes the current repository state on the active schema-alignment workstream and reflects the implementation in `GraphBasedNLP.py`, `RefinementPhase.py`, `TemporalPhase.py`, `EventEnrichmentPhase.py`, `TlinksRecognizer.py`, and the supporting components under `text_processing_components/`.

## 1. What textgraphx is doing

textgraphx is a staged NLP-to-knowledge-graph system. It reads structured text documents, runs a sequence of linguistic and information-extraction passes, and writes a document-scoped graph into Neo4j.

The system is best understood as a pipeline of separate phases rather than a single monolithic model. The current operational order is:

1. Initial graph construction
2. Refinement
3. Temporal extraction
4. Event enrichment
5. Temporal link recognition

The shell runner [scripts/run_pipeline.sh](../scripts/run_pipeline.sh) executes those phases in that order.

Multi-document safety note (new hardening):

- review-mode preparation now treats any pre-existing `AnnotatedText` nodes as contamination risk
- in `runtime.mode=testing`, the graph is fully cleared before review runs when any documents exist
- in `runtime.mode=production`, review preparation fails fast instead of silently mixing corpora

Schema ownership note:

- migrations define the enforced schema
- schema.md defines the maintained semantic contract
- for implementation decisions, follow precedence documented in `docs/schema.md` (runtime write path -> migration -> schema contract -> ontology metadata)
- new text-processing functions should follow the LPG authoring rules in `docs/schema.md` Section 10
- ontology-level reasoning contracts are now explicit in `schema/ontology.json` (`relation_endpoint_contract`, `event_attribute_vocabulary`, `temporal_reasoning_profile`)

## 2. End-to-end pipeline

```mermaid
flowchart LR
    A[MEANTIME XML documents] --> B[GraphBasedNLP.py]
    B --> C[Initial graph in Neo4j]
    C --> D[RefinementPhase.py]
    D --> E[TemporalPhase.py]
    E --> F[EventEnrichmentPhase.py]
    F --> G[TlinksRecognizer.py]
    G --> H[Knowledge graph for downstream reasoning]
```

### Stage 1: Initial graph construction

Main files:

- [GraphBasedNLP.py](../GraphBasedNLP.py)
- [TextProcessor.py](../TextProcessor.py)
- [text_processing_components/DocumentImporter.py](../text_processing_components/DocumentImporter.py)
- [text_processing_components/SentenceCreator.py](../text_processing_components/SentenceCreator.py)
- [text_processing_components/TagOccurrenceCreator.py](../text_processing_components/TagOccurrenceCreator.py)
- [text_processing_components/TagOccurrenceDependencyProcessor.py](../text_processing_components/TagOccurrenceDependencyProcessor.py)
- [text_processing_components/EntityProcessor.py](../text_processing_components/EntityProcessor.py)
- [text_processing_components/EntityFuser.py](../text_processing_components/EntityFuser.py)
- [text_processing_components/EntityDisambiguator.py](../text_processing_components/EntityDisambiguator.py)
- [text_processing_components/CoreferenceResolver.py](../text_processing_components/CoreferenceResolver.py)
- [text_processing_components/SRLProcessor.py](../text_processing_components/SRLProcessor.py)
- [text_processing_components/NounChunkProcessor.py](../text_processing_components/NounChunkProcessor.py)
- [text_processing_components/WordSenseDisambiguator.py](../text_processing_components/WordSenseDisambiguator.py)
- [text_processing_components/WordnetTokenEnricher.py](../text_processing_components/WordnetTokenEnricher.py)

What happens here:

- `GraphBasedNLP` loads spaCy, configures the tokenizer, adds the SRL pipe, creates Neo4j constraints, and checks connectivity.
- `store_corpus()` imports MEANTIME XML documents into `AnnotatedText` nodes through `MeantimeXMLImporter`.
- During `store_corpus()`, NAF raw text is normalized by `text_normalization.normalize_naf_raw_text` before spaCy sentence segmentation.
    - Runtime control: `runtime.naf_sentence_mode` (`auto`, `preserve`, `meantime`, `legacy`).
    - `auto` is the default and is recommended for mixed corpora.
    - `meantime` is recommended when evaluating against MEANTIME gold where headline/date blocks are common.

    ID stability and type safety note (new hardening):

    - ingestion now iterates source files in deterministic sorted order
    - fallback document IDs are now deterministic integer IDs derived from filename hashing
    - non-numeric `publicId` values no longer become graph IDs; integer fallback is used to preserve temporal/event query contracts
- `process_text()` sends documents through spaCy and orchestrates sentence/token persistence, WSD, WordNet enrichment, noun chunks, entity processing/fusion/disambiguation, coreference resolution, SRL persistence, and relationship extraction.
- The token-level graph is created through `Sentence`, `TagOccurrence`, `HAS_TOKEN`, `HAS_NEXT`, and `IS_DEPENDENT` relationships.
- Named entities, noun chunks, coreference nodes, semantic role frames, and token-level enrichment are written into Neo4j.
- WordNet token enrichment now persists both synset identifiers and lexical-domain metadata so later refinement passes can roll token semantics up onto nominal mentions.

Current implementation note:

- The `TextProcessor.process_entities` parameter names are legacy (`document_id, nes`) but the actual positional call path from `GraphBasedNLP` passes `(doc, text_id)` and is forwarded to `EntityProcessor.process_entities(doc, text_id)`, so it currently works despite confusing naming.

The current design is a write-heavy pipeline with deterministic IDs and mostly document-scoped graph objects.

### Stage 2: Refinement

Main file:

- [RefinementPhase.py](../RefinementPhase.py)

What happens here:

- Assigns syntactic heads to multi-token and single-token `NamedEntity`, `Antecedent`, `CorefMention`, and `FrameArgument` nodes.
- Links `FrameArgument` nodes to canonical `NamedEntity` or `Entity` nodes when the syntactic pattern supports it.
- Promotes numeric and value-like mentions into graph entities where appropriate.
- Normalizes or corrects named-entity-linking results when KB IDs are present or missing.
- Detects quantified entities and creates links from frame arguments to numeric entities.
- Materializes explicit `EntityMention:NominalMention` nodes for frame-argument and noun-chunk nominals, with token anchoring for evaluation and graph inspection.
- Derives noun-preferred nominal semantic heads and lexical-semantic profile fields without overwriting the original surface-head metadata.
- Exposes diagnostic helpers that count node and relationship types to help explain empty query matches.
- Entity-state enrichment is operationally observable through runtime diagnostics query-pack entries:
    - `entity_state_coverage` reports mention-level coverage ratio
    - `entity_state_type_distribution` reports normalized type distribution (`ATTRIBUTE`, `CONDITION`, `ROLE_OR_CLASS`, `STATE`)
- Entity specificity class enrichment (`ent_class`: `SPC|GEN|USP|NEG`) is now added on both mention and canonical entity nodes via `annotate_entity_specificity_classes`.
- Runtime diagnostics now also expose:
    - `entity_specificity_coverage` for `ent_class` coverage
    - `event_external_ref_coverage` for event-level `external_ref`
    - `glink_relation_inventory` for grammatical-link relation distribution

Current implementation note:

- The script entrypoint executes a long ordered sequence (roughly 28 refinement passes) and records a `RefinementRun` marker node with pass names and timestamp.

This phase is the main rule-based canonicalization layer. It is where the graph starts moving from surface mentions toward reusable, normalized entities.

Nominal enhancement track:

- `ENH-NOM-01` semantic head resolution. Purpose: repair modifier-heavy nominal heads before semantic interpretation. Rationale: surface parse roots are often not the semantically informative noun.
- `ENH-NOM-02` WordNet lexical-domain persistence. Purpose: keep coarse semantic classes queryable on the graph. Rationale: `wnLexname` is a more stable signal for eventive nominal analysis than ad hoc hypernym matching alone.
- `ENH-NOM-03` additive nominal semantic/evaluation profiling. Purpose: support scorer projections and downstream KG queries without deleting or collapsing graph evidence. Rationale: evaluation scope and semantic richness must remain separable concerns.

### Stage 3: Temporal extraction

Main file:

- [TemporalPhase.py](../TemporalPhase.py)

What happens here:

- Creates a document creation time node (`DCT`) from `AnnotatedText.creationtime`.
- Extracts temporal expressions (`TIMEX`) from external temporal tools and links them back to triggering tokens.
- Creates temporal event nodes (`TEvent`) and links them to triggering tokens.
- Materializes temporal signal spans used later by link recognition.
- Persists event `external_ref` identifiers when available from temporal XML annotations.
- Materializes grammatical links (`GLINK`) between existing event nodes when present in annotation output.
- Does not create temporal links; that work belongs to `TlinksRecognizer.py`.
- Does not create `EventMention` nodes; mention-level event materialization belongs to `EventEnrichmentPhase.create_event_mentions()`.

Current implementation note:

- In the current `__main__` flow of `TemporalPhase.py`, `create_DCT_node`, `materialize_tevents`, `materialize_signals`, `materialize_timexes_fallback`, and `materialize_glinks` are executed. Temporal link creation is handled separately by `TlinksRecognizer.py`.
- A compatibility layer now preserves legacy TemporalPhase method contracts (`create_tevents2`, `create_timexes2`, `create_signals2`, `create_tlinks_e2e`, `create_tlinks_e2t`, `create_event_mentions2`) as shims over the canonical materialization/linking path so older runtime tests and maintenance scripts remain stable during migration.

The temporal phase depends on external XML-producing services and APOC XML parsing inside Neo4j.

### Stage 4: Event enrichment

Main file:

- [EventEnrichmentPhase.py](../EventEnrichmentPhase.py)

What happens here:

- Materializes `EventMention` nodes from existing `TEvent` nodes and links them with `REFERS_TO`.
- Carries canonical event `external_ref` identifiers from `TEvent` into mention-layer `EventMention` nodes.
- Attempts to link `Frame` nodes to `TEvent` nodes through `DESCRIBES`.
- Writes the canonical `FRAME_DESCRIBES_EVENT` edge in parallel with `DESCRIBES` for backward-compatible transition support.
- Links `Frame` nodes to `EventMention` nodes through `INSTANTIATES`.
- Adds core participants from `FrameArgument` nodes to events through `PARTICIPANT` edges.
- Adds canonical `EVENT_PARTICIPANT` edges alongside `PARTICIPANT` where the maintained mention/event layer expects them.
- Adds non-core participants and labels them with human-readable argument types.
- Keeps temporal arguments separate from the non-core participant bucket so temporal reasoning stays visible.

Current implementation note:

- `link_frameArgument_to_event()` currently uses the pattern `(f:Frame)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)`. This is important to revisit because most frame/token connectivity in the project is mediated via `FrameArgument` and `PARTICIPANT`, so this query may under-link in real datasets.

This phase connects predicate structure to the temporal event layer and gives each event a richer argument structure.

### Stage 5: TLINK recognition

Main file:

- [TlinksRecognizer.py](../TlinksRecognizer.py)

What happens here:

- Applies rule-based heuristics to infer temporal relations from argument structure, tense, aspect, and temporal modifiers.
- Produces TLINKs such as AFTER, BEFORE, SIMULTANEOUS, IS_INCLUDED, BEGUN_BY, ENDED_BY, and MEASURE.
- Uses six explicit matching cases that look for repeated syntactic/temporal patterns around `TEvent` and `TIMEX` nodes.
- Normalizes TLINK relation inventory to canonical TimeML labels and applies conservative transitive closure (`BEFORE/AFTER/IDENTITY` subset).
- Suppresses contradictory TLINK pairs using confidence-first conflict policy and validates TLINK endpoint contracts against ontology typing rules.

This phase is currently a heuristic layer on top of the temporal graph, not a learned temporal reasoner.

### Execution reality snapshot (code-verified)

- The script-level pipeline order is currently: `GraphBasedNLP.py` -> `RefinementPhase.py` -> `TemporalPhase.py` -> `EventEnrichmentPhase.py` -> `TlinksRecognizer.py` (via `scripts/run_pipeline.sh`).
- Temporal extraction and temporal linking are split across phases: `TemporalPhase` materializes `DCT`, `TIMEX`, `TEvent`, and `Signal`; `EventEnrichmentPhase` materializes `EventMention`; `TlinksRecognizer` runs the TLINK heuristics over those existing temporal nodes.
- Runtime phase assertions now enforce ontology endpoint contracts and strict legacy-to-canonical edge-ratio thresholds in testing/review modes.
- Full-stack quality exports now embed runtime diagnostics payloads, including entity-state coverage, entity specificity coverage, event external-ref coverage, and GLINK inventory totals, so semantic-state progress is visible in JSON/Markdown reports and CLI summaries.
- External NLP services are still hardcoded in multiple modules (`TextProcessor.py`, `TemporalPhase.py`, `util/RestCaller.py`, `util/CallAllenNlpCoref.py`).
- Refinement is broad and rule-heavy; it is not a single pass but a sequence of many targeted Cypher transforms.

### Ownership matrix (current state)

| Graph element | Primary owner | Notes |
| --- | --- | --- |
| `AnnotatedText`, `Sentence`, `TagOccurrence`, `NamedEntity`, `Entity`, `Frame`, `FrameArgument` | Initial graph construction | Created during ingestion and token/SRL/entity processing. |
| `EntityMention:NominalMention` | `RefinementPhase.py` | Materialized from nominal arguments and noun chunks. |
| `TIMEX`, `TEvent`, `Signal`, DCT `TIMEX` | `TemporalPhase.py` | Extraction/materialization only; no TLINK creation. |
| `EventMention` | `EventEnrichmentPhase.py` | Created by `create_event_mentions()` and linked to `TEvent` via `REFERS_TO`. |
| `TLINK` | `TlinksRecognizer.py` | Created after temporal extraction and event enrichment have populated the graph. |
| `GLINK` | `TemporalPhase.py` | Materialized from temporal XML relation tags over existing `TEvent` nodes. |

## 3. Core graph model

The graph is strongly document-scoped. Most IDs are built from document id plus token spans so that re-runs can use `MERGE` safely and later phases can match against stable identifiers.

The canonical ontology is documented in [schema/ontology.json](../schema/ontology.json) and rendered for humans in [docs/ontology.html](ontology.html).

### Main node types

| Node | Purpose | Typical properties |
| --- | --- | --- |
| `AnnotatedText` | Document-level container | `id`, `text`, `author`, `creationtime`, `filename`, `uri` |
| `Sentence` | Sentence container | `id`, `text` |
| `TagOccurrence` | Token-level node used across the pipeline | `id`, `index`, `end_index`, `text`, `lemma`, `pos`, `upos`, `tok_index_doc`, `tok_index_sent` |
| `Tag` | Lemma grouping node | `id` |
| `NamedEntity` | Surface entity mention | `id`, `type`, `value`, `kb_id`, `head`, `headTokenIndex`, `token_id` |
| `Entity` | Canonical/disambiguated entity | `id`, `type`, `kb_id` |
| `Frame` | Semantic role labeling predicate | `id`, `headword`, `headTokenIndex`, `text` |
| `FrameArgument` | Semantic role labeling argument | `id`, `type`, `head`, `headTokenIndex`, `syntacticType` |
| `NounChunk` | Noun phrase span | `id`, `type`, `value` |
| `Antecedent` | Coreference cluster head | `id`, `text`, `startIndex`, `endIndex` |
| `CorefMention` | Coreference mention | `id`, `text`, `startIndex`, `endIndex` |
| `TIMEX` | Temporal expression | `tid`, `doc_id`, `type`, `value`, `text` |
| `TEvent` | Temporal event | `eiid`, `doc_id`, `begin`, `end`, `tense`, `aspect` |
| `NUMERIC` | Dynamic label on selected `NamedEntity` mentions treated as numeric participants | Reuses `NamedEntity` properties; applied by refinement based on NER type |
| `Evidence` | Relation provenance | `id`, `type` |
| `Relationship` | Higher-level relation abstraction | `id`, `type` |
| `RefinementRun` | Refinement execution marker | `id`, `timestamp`, `passes` |

### Main relationships

| Relationship | Direction | Purpose |
| --- | --- | --- |
| `CONTAINS_SENTENCE` | `AnnotatedText -> Sentence` | Connects a document to its sentence nodes |
| `HAS_TOKEN` | `Sentence -> TagOccurrence` | Connects a sentence to its token sequence |
| `HAS_NEXT` | `TagOccurrence -> TagOccurrence` | Orders tokens inside the sentence |
| `IS_DEPENDENT` | `TagOccurrence -> TagOccurrence` | Stores dependency edges and dependency labels |
| `PARTICIPATES_IN` | `TagOccurrence -> NamedEntity|Frame|FrameArgument|CorefMention|Antecedent|NounChunk` | Links a token to the mention or structure it participates in |
| `REFERS_TO` | `NamedEntity -> Entity` | Connects a mention to a canonical entity |
| `PARTICIPANT` | `FrameArgument -> Frame` | Stores SRL role membership |
| `COREF` | `CorefMention -> Antecedent` | Links mentions to antecedents |
| `TRIGGERS` | `TagOccurrence -> TIMEX|TEvent` | Connects a token span to a temporal object |
| `DESCRIBES` | `Frame -> TEvent` | Connects a predicate frame to a temporal event |
| `TLINK` | `TEvent/TIMEX -> TEvent/TIMEX` | Stores temporal relations and relation type |
| `IS_RELATED_TO` | `NamedEntity -> NamedEntity` | Mention-level relation support |

### Identity conventions

Stable ID generation is centralized in [utils/id_utils.py](../utils/id_utils.py):

- Frame: `frame_<doc>_<start>_<end>`
- FrameArgument: `fa_<doc>_<start>_<end>_<argtype>`
- NamedEntity: `<doc>_<start>_<end>_<type>`
- TagOccurrence: `<doc>_<sent>_<token_idx>`
- NounChunk: `<doc>_<start>`

There is also a migration helper, [tools/migrate_namedentity_token_ids.py](../tools/migrate_namedentity_token_ids.py), that can derive token-index-based IDs for existing `NamedEntity` nodes without changing the original surface ID.

### Constraints created at initialization

`GraphBasedNLP.create_constraints()` currently creates node-key constraints for:

- `Tag(id)`
- `TagOccurrence(id)`
- `Sentence(id)`
- `AnnotatedText(id)`
- `NamedEntity(id)`
- `Entity(type, id)`
- `Evidence(id)`
- `Relationship(id)`
- `NounChunk(id)`
- `TEvent(eiid, doc_id)`

## 4. Configuration and runtime assumptions

### Configuration

The central configuration loader is [config.py](../config.py). It supports INI and TOML, plus environment variable overrides.

Precedence:

1. Explicit path passed to the loader
2. `TEXTGRAPHX_CONFIG`
3. Repo-local `config.ini`
4. User config under `~/.textgraphx/config.ini`
5. Built-in defaults

Useful environment variables include:

- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `SPACY_MODEL`, `SPACY_USE_GPU`
- `TEXTGRAPHX_LOG_LEVEL`, `TEXTGRAPHX_LOG_JSON`, `TEXTGRAPHX_LOG_FILE`
- `TEXTGRAPHX_DATA_DIR`, `TEXTGRAPHX_OUTPUT_DIR`, `TEXTGRAPHX_TMP_DIR`
- `TEXTGRAPHX_NAF_SENTENCE_MODE` (`auto|preserve|meantime|legacy`)

Sentence normalization guidance:

- Use `auto` for general-purpose ingestion where document formatting may vary.
- Use `meantime` when ingesting MEANTIME-like NAF files for evaluation; it improves sentence boundaries for headline/date paragraphs that lack terminal punctuation.
- Use `preserve` when you want zero heuristic paragraph rewriting.
- Use `legacy` only for backward compatibility with historical runs.

### Neo4j access

The Neo4j compatibility layer lives in [neo4j_client.py](../neo4j_client.py). It wraps the official Neo4j driver and preserves the `.run(query, parameters).data()` contract that the older code expects.

The older [GraphDBBase](../util/GraphDbBase.py) helper still exists and is used by some entry points, but the newer code paths prefer the centralized Neo4j wrapper.

### Logging

Logging setup is centralized in [logging_config.py](../logging_config.py). It supports plain text logs, optional JSON output, and optional rotating file logs.

### External services and runtime dependencies

The pipeline assumes a running Neo4j instance and several external NLP services:

- spaCy models for tokenization, dependency parsing, and NER
- AMuSE-WSD at `http://localhost:81/api/model`
- Coreference service at `http://localhost:9999/coreference_resolution`
- Temporal annotation service at `http://localhost:5050/annotate`
- Neo4j APOC procedures for XML parsing and migration utilities
- NLTK WordNet data for token enrichment and disambiguation

Additional codebase-level service URLs currently appear in helper modules (`util/RestCaller.py`, `util/CallAllenNlpCoref.py`, and LLM helper skeletons), which indicates endpoint configuration is still only partially centralized.

The provided script [scripts/run_pipeline.sh](../scripts/run_pipeline.sh) bootstraps a local venv if needed, installs requirements, downloads `en_core_web_sm`, and then runs the phase scripts in sequence.

### CLI behavior

`GraphBasedNLP.py` supports a small command-line interface:

- `--dir` to choose the document directory
- `--model` to choose between `sm` and `trf`
- `--require-neo4j` to fail fast if the database is unreachable
- `--neo4j-retries` and `--neo4j-backoff` to control startup connectivity checks

## 5. What is solid today

- The pipeline is clearly separated into phases with intuitive responsibilities.
- The graph model is document-scoped and uses deterministic IDs.
- Neo4j access has been modernized through a compatibility wrapper.
- The config loader centralizes runtime settings and supports environment overrides.
- The ontology is already documented in machine-readable and human-readable form.

## 6. Current gaps and risks

- `TextProcessor.py` still mixes orchestration, legacy helper paths, and component wiring, which increases maintenance cost.
- Some Cypher in phase modules still uses string interpolation for IDs/filenames instead of full parameterization.
- Service endpoint management is partially centralized (`config.py`) but still hardcoded in several modules.
- Automated tests are currently minimal; the existing test file focuses on NamedEntity token-id migration logic.
- Checkpoint/resume is now available for dataset-scoped phase execution through JSON checkpoints under `out/checkpoints/` (phase-level skip/resume support in orchestrator).
- Historical docs and comments still contain pre-remediation wording about temporal-link ownership; that drift is riskier than the current runtime split itself.
- `EventEnrichmentPhase.py` contains a key linking query that should be validated against expected graph topology on real datasets.

These do not change the architectural direction, but they are important for reliability and iteration speed.

## 7. Phased enhancement plan

### Iteration 1: reliability baseline (short cycle)

1. Externalize all service URLs into config and env vars (`wsd`, `coreference`, `temporal`, optional LLM endpoint).
2. Add startup/service health checks with clear warnings and fail-fast mode.
3. Parameterize remaining interpolated Cypher in temporal and refinement-related methods.
4. Add one end-to-end smoke test (single tiny document) that verifies stage output counts.
pytest tests/test_smoke_e2e.py -v -m slow
### Iteration 2: pipeline correctness and observability

5. Add phase-level assertions (expected node/edge minimums) and structured per-phase timing logs.
6. Validate and, if needed, refactor `EventEnrichmentPhase.link_frameArgument_to_event()` to align with actual frame/argument topology.
7. Add phase run markers consistently (beyond `RefinementRun`) for restart visibility.
8. Introduce a simple per-document run report (processed, skipped, failed phase, reason).

### Iteration 3: maintainability and modularization

9. Split orchestration responsibilities in `TextProcessor.py` into smaller services with explicit interfaces.
10. Group refinement rules into documented rule families (head assignment, linking, numeric/value, NEL correction).
11. Expand integration tests for each phase and for cross-phase invariants.
12. Add a stable query pack for graph inspection and debugging.

Current implementation status:

- Done: `TextProcessor.py` now delegates component construction to `text_processing_components/pipeline/component_factory.py`, with explicit orchestration interfaces in `text_processing_components/pipeline/interfaces.py`.
- Done: `RefinementPhase.py` now exposes `RULE_FAMILIES` and supports family-wise execution through `run_rule_family()` / `run_all_rule_families()`.
- Done: integration tests were expanded with cross-phase invariant checks in `tests/test_integration_cross_phase_invariants.py` and phase-level checks in `tests/test_integration_phase_assertions.py`.
- Done: stable query pack added under `queries/` (`counts_by_label.cypher`, `doc_invariants.cypher`, `recent_phase_runs.cypher`) with loader utilities in `queries/query_pack.py`.
- Done: per-dataset checkpoint/resume scaffolding added via `checkpoint.py` and `orchestration/orchestrator.py` (`run_selected(..., resume_from_checkpoint=True)` now skips already-checkpointed phases).

### Iteration 4: semantic quality and KG completeness

13. Add evaluation harnesses for entity/event/temporal quality (precision/coverage style metrics).
14. Introduce confidence/provenance attributes for inferred links where feasible.
15. Expand cross-sentence/cross-document fusion logic for stronger global KG coherence.
16. Add domain-specific semantic enrichment layers as optional post-processing modules.

Current implementation status:

- Done: Iteration 4.13 baseline evaluation harness added in `evaluation/metrics.py` with stable metric primitives (`precision_recall_f1`, `coverage`, `macro_average`) and graph-backed snapshots via `GraphEvaluationHarness`.
- Done: unit/regression tests for metric contracts in `tests/test_evaluation_metrics.py`.
- Done: integration coverage for the harness in `tests/test_integration_evaluation_harness.py`.
- Done: Iteration 4.14 provenance/confidence stamping added through `provenance.py` and wired into phase wrappers for `TLINK`, `DESCRIBES`, and `PARTICIPANT` inferred links.
- Done: provenance unit/regression tests in `tests/test_provenance.py` and integration checks in `tests/test_integration_provenance.py`.
- Done: confidence-calibration scaffolding added in `confidence.py` (`compute_evidence_weighted_confidence`, `calibrate_confidence`) and provenance stamping now persists `calibration_version` and `confidence_components` metadata.
- Done: Iteration 4.15 cross-sentence and cross-document fusion baseline added in `fusion.py`, creating `CO_OCCURS_WITH` links for sentence-local entity pairs and `SAME_AS` links for cross-document entities that share `kb_id`.
- Done: cross-document fusion hardening now supports optional type-compatibility enforcement for `SAME_AS` creation (`require_type_compatibility` in `fusion.py`).
- Done: refinement orchestration now runs fusion post-processing in `phase_wrappers.py` and reports created link counts.
- Done: cross-document fusion in refinement is now runtime-gated by `runtime.enable_cross_document_fusion` (default `false`) so strict evaluation/review runs can prevent cross-document linkage unless explicitly enabled.
- Done: fusion unit/regression tests in `tests/test_fusion.py` and integration checks in `tests/test_integration_fusion.py`.
- Done: strict post-run materialization gate added in `orchestration/orchestrator.py` (review runs now fail fast if key layers like `TEvent`, `DESCRIBES`, or `TLINK` are missing).
- Done: review-run preparation in `orchestration/orchestrator.py` now clears stale graph state whenever any `AnnotatedText` exists in testing mode, and blocks in production mode to prevent mixed-corpus contamination.
- Done: orchestrator phase execution now fails fast if a phase runner returns `{"status": "error"}` (previously some wrappers could return error payloads without failing the run).
- Done: integration regression added in `tests/test_integration_pipeline_materialization.py` to ensure single-document review runs materialize temporal/event layers.
- Done: MEANTIME evaluator supports `--discourse-only` as an entity-scope filter only (`:DiscourseEntity` labels); event projection remains unchanged, and report JSON now includes `evaluation_scope` metadata to make this explicit.
- Done: event mention predicate canonicalization now prefers trigger-token lemma and preserves phrasal-verb particles (`VB*` + following `RP`) at mention level, improving strict event matching while keeping canonical `TEvent` semantics stable.
- Done: event factuality defaults were tightened (`certainty` heuristic for future/infinitive/modal contexts, noun-event tense/aspect over-specification cleanup) to better align mention attributes with MEANTIME-style annotation practice.
- Done: conservative low-confidence event gating was added for non-verbal mentions with no frame/participant/TLINK evidence; flags are stored as `EventMention.low_confidence` and rolled up to `TEvent.low_confidence` only when all mentions are low-confidence. Evaluator projection excludes low-confidence events without deleting graph evidence.
- Done: an incremental change ledger with rationale and measured outcomes is now maintained in `docs/EVALUATION_IMPROVEMENT_LOG.md`.
- Done: a targeted cognitive-participle normalization (`fearing that ...`) and fallback event projection de-duplication removed the last strict event type-mismatch on doc 76437 and improved strict event F1.
- Done: `ENH-NOM-01` and `ENH-NOM-02` nominal semantic-head layer (`resolve_nominal_semantic_heads`) and `wnLexname` persistence (`annotate_nominal_semantic_profiles`) are implemented in `RefinementPhase.py`; the head-repair pass prefers NOUN/PROPN/PRON tokens over modifiers/determiners and sets `nominalSemanticHead*` fields on `EntityMention` and `Entity` nodes, while `wnLexname` from `WordnetTokenEnricher` is read and stored as `nominalHeadWnLexname`.
- Done: `ENH-NOM-03` evaluator nominal profile modes (`all`, `eventive`, `salient`, `candidate-gold`, `background`) are implemented in `meantime_evaluator.build_document_from_neo4j` and validated against `allowed_profile_modes`; all five modes are covered by comprehensive unit tests in `tests/test_enh_nom_01_02_03.py` (55 tests).
- Done: Iteration 4.13/10 operator-grade KG quality toolkit CLI added as `python -m textgraphx.tools.evaluate_kg_quality` (exports JSON/CSV/Markdown from `evaluation/fullstack_harness.py`, with deterministic run metadata and quality/conclusiveness summary).

## 8. Enhancement backlog (prioritized list)

1. ~~Service-config unification and endpoint cleanup across all modules.~~ **Done**: All service callers (`RestCaller.py`, `CallAllenNlpCoref.py`, `TextProcessor.py`) already read URLs exclusively via `get_config().services.*`. Fixed `heideltime_url` default bug (was `:5050`, now `:5000` to match `config.example.toml`). Added standardised `TEXTGRAPHX_*` env-var aliases for all service URLs alongside the legacy names (backward-compatible). Contract verified by 32 tests in `tests/test_service_config_contract.py`.
2. ~~Cypher safety pass (parameterization + query-style normalization).~~ **Done**: Code audit completed via 11 source-inspection tests in `tests/test_cypher_safety_pass.py`. All four core phase files (`EventEnrichmentPhase`, `TemporalPhase`, `RefinementPhase`, `TlinksRecognizer`) already follow best practices: (1) parameterized values using `$param` style (EventEnrichmentPhase/TemporalPhase), (2) static safe queries (RefinementPhase/TlinksRecognizer), (3) no bareword interpolation in WHERE/SET clauses. Field names that must be dynamic (e.g., `te.{field_name}`) are constrained to enum values at the call site.
3. ~~End-to-end smoke test and basic regression suite.~~ **Done**: Created `tests/test_smoke_e2e_plus_regressions.py` with 10 tests covering (1) minimal document flow through M1-M10 (smoke test), (2) materialization gate assertions for each phase, (3) known regression patterns (low-confidence event flagging, nominal semantic head selection, TLINK type validation), (4) phase assertion contracts (preconditions/postconditions). All tests passing; regression pattern table serves as future reference.
4. ~~Clear ownership split between temporal extraction and temporal link generation.~~ **Done**: Temporal ownership contracts are enforced by source-level audits (`tests/test_temporal_ownership_audit.py`) and runtime compatibility shims now delegate legacy TLINK/EventMention calls outside `TemporalPhase.py`.
4. ~~Event-enrichment linking-query validation/refactor.~~ **Done**: `EventEnrichmentPhase.link_frameArgument_to_event()` already implements three idempotent MERGE paths — (1) direct `TagOccurrence→Frame→TEvent`, (2) via `FrameArgument→Frame→TEvent`, (3) `Frame→EventMention` (INSTANTIATES). All three paths and their relationship types validated by 25 source-inspection tests in `tests/test_event_enrichment_linking_query.py`.
5. ~~Clear ownership split between temporal extraction and temporal link generation.~~ **Done** (duplicate of item 4): maintained for historical traceability; covered by the same ownership audits and compatibility-layer split.
6. ~~Per-document checkpoint/resume support.~~ **Done**: Added `textgraphx/checkpoint.py` and orchestrator integration to persist phase checkpoints and resume from remaining phases (`tests/test_checkpoint.py`, `tests/test_orchestration.py`).
7. ~~TextProcessor decomposition into orchestrator + stage services.~~ **Done (incremental)**: Stage-component construction is delegated through `text_processing_components/pipeline/component_factory.py` and interface contracts in `text_processing_components/pipeline/interfaces.py`; remaining legacy internals are now compatibility-safe but non-blocking.
8. ~~Refinement rule catalog and test fixtures.~~ **Done**: `RefinementPhase.RULE_FAMILIES` and family-execution methods are covered by `tests/test_refinement_rule_families.py` and integration-level assertions.
9. ~~Runtime diagnostics dashboard/query set.~~ **Done (foundation)**: Added diagnostics registry in `diagnostics.py`, runtime diagnostics query entries (`phase_execution_summary.cypher`, `phase_assertion_violations.cypher`, `endpoint_contract_violations.cypher`), and API endpoint `GET /diagnostics/runtime` in `api.py` (`tests/test_diagnostics.py`).
10. ~~KG quality evaluation toolkit.~~ **Done**: unified evaluator stack available via `evaluation/fullstack_harness.py` and CLI `textgraphx.tools.evaluate_kg_quality` with test coverage in `tests/test_evaluate_kg_quality_cli.py`.
11. ~~`ENH-NOM-03` evaluator profile modes over persisted nominal semantic attributes.~~ **Done**: implemented and validated in `tests/test_enh_nom_01_02_03.py`.

## 9. Best starting points for future work

If you want to improve the system incrementally, the highest-value files to revisit first are:

- [GraphBasedNLP.py](../GraphBasedNLP.py)
- [TextProcessor.py](../TextProcessor.py)
- [RefinementPhase.py](../RefinementPhase.py)
- [TemporalPhase.py](../TemporalPhase.py)
- [EventEnrichmentPhase.py](../EventEnrichmentPhase.py)
- [TlinksRecognizer.py](../TlinksRecognizer.py)
- [schema/ontology.json](../schema/ontology.json)
- [config.py](../config.py)
- [neo4j_client.py](../neo4j_client.py)
- [scripts/run_pipeline.sh](../scripts/run_pipeline.sh)

Those files define most of the current behavior, known risk points, and iteration leverage for the project.
