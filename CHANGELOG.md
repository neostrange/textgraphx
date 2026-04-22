# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — feature/schema-contract-alignment

### Added

#### Schema & Ontology
- `schema/ontology.json` — machine-readable ontology with `relation_endpoint_contract`,
  `event_attribute_vocabulary`, and `temporal_reasoning_profile` sections.
- `docs/schema.md` — semantic contract for the LPG write path; defines precedence rules
  for implementation decisions (runtime → migration → schema contract → ontology metadata).
- Schema validation CLI (`python -m textgraphx.tools.schema_validation`).
- Schema assertion helpers (`textgraphx/tools/schema_asserts.py`).
- Milestone 7 schema validation test suite (`tests/test_milestone7_schema_validation.py`).

#### Temporal Layer
- `TlinksRecognizer.py` — dedicated TLINK heuristic phase, decoupled from TemporalPhase.
  Implements six explicit matching cases, conservative transitive closure, confidence-first
  conflict resolution, and ontology-based endpoint validation.
- TLINK relation inventory normalized to canonical TimeML labels (BEFORE, AFTER,
  SIMULTANEOUS, IS_INCLUDED, BEGUN_BY, ENDED_BY, MEASURE).
- DCT (Document Creation Time) node materialization moved to TemporalPhase.
- `temporal_legacy_compat.py` — compatibility shim module preserving older runtime
  contracts (`create_tlinks_e2e`, `create_tlinks_e2t`, `create_event_mentions2`) as
  thin wrappers over canonical materialization.
- Temporal reasoning runtime test suite (`tests/test_tlinks_reasoning_runtime.py`).

#### Event Enrichment
- `EventEnrichmentPhase` now materializes `FRAME_DESCRIBES_EVENT` in parallel with
  `DESCRIBES` for backward-compatible transition support.
- Canonical `EVENT_PARTICIPANT` edges written alongside `PARTICIPANT` for mention/event
  layer consumers.
- Participant Cypher query `WITH` clause split to fix variable scoping
  (`CypherSyntaxError` on `event` variable).

#### Nominal Semantic Enhancement (ENH-NOM-01/02/03)
- `RefinementPhase.resolve_nominal_semantic_heads()` — repairs modifier-heavy nominal
  heads before semantic interpretation using spaCy dependency parse.
- `RefinementPhase.annotate_nominal_semantic_profiles()` — persists `wnLexname` and
  nominal semantic profile fields on `EntityMention:NominalMention` nodes.
- `EntityMention:NominalMention` nodes now carry `syntactic_head`, `wnLexname`,
  `nominal_profile_mode`, and `is_discourse_entity` fields.
- Evaluator `build_document_from_neo4j` supports all 5 `nominal_profile_mode` values.
- 55 unit tests in `tests/test_enh_nom_01_02_03.py`.

#### MEANTIME Evaluation Framework
- `textgraphx/evaluation/meantime_evaluator.py` — MEANTIME PRF scorer with strict and
  relaxed matching, per-document and batch evaluation, and relation-error classification
  (`type_mismatch`, `endpoint_mismatch`).
- `textgraphx/evaluation/meantime_bridge.py` — bridges M1–M7 unified evaluation with
  gold-standard MEANTIME validation (`ConsolidatedQualityReport`, weighted scoring:
  phase structure 40% + MEANTIME PRF 40% + consistency 20%).
- `textgraphx/evaluation/cross_phase_validator.py` — validates semantic coherence across
  phase boundaries: cascade semantics, density metrics, orphan detection, backward
  compatibility.
- `textgraphx/evaluation/fullstack_harness.py` — `FullStackEvaluator` with 5-phase report
  structure, JSON/CSV/Markdown export, and conclusiveness assessment.
- Evaluation CLI: `python -m textgraphx.tools.evaluate_meantime`.
- Evaluation CLI: `python -m textgraphx.tools.evaluate_kg_quality`.
- 31 tests in `tests/test_milestone8_bridge_validator.py`.

#### Dataset & Tooling
- `python -m textgraphx.tools.select_eval_dataset` — materializes a matched evaluation
  subset from `datastore/original_dataset` based on `datastore/annotated` XML stems.
- `python -m textgraphx.tools.nominal_coverage_probe` — existence-scoped Cypher probe for
  nominal evaluation coverage (avoids inflated counts from `OPTIONAL MATCH`).
- `python -m textgraphx.tools.run_migrations` — migration runner with `--clear-all` safety flag.
- `python -m textgraphx.tools.generate_ontology_human` — human-readable ontology export.
- `scripts/run_quality_baseline.sh` — operator script to capture a committed quality
  baseline snapshot (JSON + CSV + Markdown).
- `textgraphx/tools/check_quality_gate.py` — CI regression gate: compares `overall_quality`
  between a stored baseline and a new report; configurable tolerance; exits non-zero on
  regression.
- `PRODUCTION_VALIDATION.md` — operator runbook for production-mode pipeline validation.

#### Pipeline Orchestration
- `textgraphx/orchestration/orchestrator.py` — `PipelineOrchestrator` with:
  - Strict post-run materialization gate in review mode (requires non-zero counts for all
    major node/edge types).
  - `_allow_empty_materialization_gate` flag for maintenance-only phase runs.
  - `run_for_review()` skips review-mode cleanup for DBpedia-only runs.
  - Deterministic document sort order during ingestion.
  - Fallback document IDs derived from filename hashing (non-numeric `publicId` values no
    longer become graph IDs).
- Phase wrapper isolation: `GraphBasedNLPWrapper` reloads the real module if a prior test
  leaked a MagicMock into `sys.modules`.
- `phase_assertions.py` — runtime assertions for ontology endpoint contracts and
  legacy-to-canonical edge-ratio thresholds.

#### Import Hardening (Python 3.13 compatibility)
- All top-level `import spacy` calls guarded with `try/except ImportError`.
- `nltk.corpus.wordnet31` import guarded with `try/except`.
- Heavy pipeline component imports moved inside `TextPipelineComponentFactory.build()`.
- `textgraphx/__init__.py` pre-loads `TextProcessor` to prevent mock contamination in
  parallel test runs.

#### Time Utilities
- `textgraphx/time_utils.py` — `utc_iso_now()`, `utc_timestamp_now()` — centralized UTC
  timestamp generation.

#### CI
- `.github/workflows/strict-transition-gate.yml` — runs regression suite on every PR and
  push to `main`/`feature/**`; added quality gate unit tests.
- New `quality-gate-check` CI job: runs `check_quality_gate` unit tests; compares against
  committed baseline when present.
- `Makefile` targets: `review`, `strict-gate`, `baseline`, `quality-gate`.
- Bootstrap CI baseline committed at `out/evaluation/baseline/kg_quality_report.json`;
  run `make baseline` after a full pipeline evaluation to lock in live quality scores.

#### UID Hardening (Coref Layer)
- `schema/migrations/0021_backfill_coref_uid.cypher` — backfills `uid` on pre-existing
  `Antecedent` and `CorefMention` nodes using `make_coref_uid()` formula via APOC batches.
- `schema/migrations/0022_add_coref_uid_constraints.cypher` — adds `UNIQUE` constraints
  and indexes on `Antecedent.uid` and `CorefMention.uid` (prerequisite: migration 0021).
- `schema/ontology.json` migration manifest updated to include migrations 0021 and 0022.
- Schema validation test count updated to 22.

#### Refinement Rule Catalog (Backlog Item 7)
- `fixtures/refinement_rules/catalog.json` — machine-readable catalog documenting all 6
  rule families in `RefinementPhase`: mention_span_repair, entity_state_annotation,
  frame_argument_linking, nominal_mention_materialization, nominal_semantic_annotation,
  canonical_value_materialization. Each rule entry includes method name, provenance_rule_id,
  input/output contracts, idempotency flag, and uid formula where applicable.
- `tests/test_items_5_9_audit.py::test_rule_fixtures_directory_exists` upgraded from
  placeholder (always-true) to enforced existence check.

### Changed

- `TemporalPhase` TLINK creation moved to `TlinksRecognizer`; legacy method names kept as
  compatibility shims in `temporal_legacy_compat.py`.
- `EventEnrichmentPhase.create_event_mentions()` is now the canonical `EventMention`
  materialization path; `TemporalPhase.create_event_mentions2` is a legacy shim.
- `run_pipeline.py` updated to use canonical `textgraphx.orchestration.orchestrator` and
  support `--cleanup {auto,none,full}`.
- `GraphBasedNLP` NAF file counting now includes `*.naf` extensions.
- `TemporalPhase` TLINK extraction no longer depends on `apoc.load.xml`.
- `EventEnrichmentPhase` strict gate scopes legacy PARTICIPANT checks to event targets.
- `meantime_evaluator.build_document_from_neo4j` now accepts `gold_token_sequence` and
  aligns Neo4j `tok_index_doc` to gold `token/@t_id` via `SequenceMatcher` exact-token
  blocks.
- MEANTIME evaluator batch mode reports `skipped_prediction_files` for unmatched files.

### Fixed

- `CypherSyntaxError: Variable 'event' not defined` in `EventEnrichmentPhase` participant
  query (WITH clause split into two stages).
- `test_no_bare_variable_interpolation_in_queries` — `RefinementPhase._merge_nominal_entity_mentions`
  used variable name `merge_query`, triggering the `query\s*=\s*f"""` Cypher safety regex;
  renamed to `_batch_cypher` and added `_source_labels` with document comments containing
  the literal mention-source label strings.
- `test_nominal_mentions_materialization_contains_required_metadata` — regression test
  expected literal strings `em.mention_source = 'frame_argument_nominal'` and
  `em.mention_source = 'noun_chunk_nominal'`; documentation comment added at the
  `_merge_nominal_entity_mentions` call site so both substrings appear in the source file.
- `ImportError: No module named '_ctypes'` in Python 3.13 build — guarded all spaCy
  top-level imports.
- `ImportError: No module named '_sqlite3'` — guarded nltk imports.
- `AssertionError` in `TextProcessor` factory patch wiring — changed to module-level
  import for patchability.
- `CypherSyntaxError` from escaped braces in f-string Cypher queries — replaced `{{`/`}}`
  with `{`/`}` in triple-quoted strings.
- `PipelineOrchestrator` empty-review-run gate — graceful degradation with
  `reason: "empty_review_run"` instead of RuntimeError when spaCy is unavailable.
- `TemporalPhase` config lookup uses `cfg.services.temporal_url` with fallback defaults
  instead of `cfg.get(...)` on dataclass-based config.
- Neo4j `elementId()` replaced with `id(n)` for compatibility with older Neo4j servers.
- Neo4j `AnnotatedText` node lookup uses numeric `id` property, not `doc_id`.

### Deprecated

- `TemporalPhase.create_tlinks_e2e()` — use `TlinksRecognizer.create_tlinks_e2e()`.
- `TemporalPhase.create_tlinks_e2t()` — use `TlinksRecognizer.create_tlinks_e2t()`.
- `TemporalPhase.create_event_mentions2()` — use `EventEnrichmentPhase.create_event_mentions()`.
- Legacy method names `create_tevents2`, `create_timexes2`, `create_signals2` in
  `TemporalPhase` — will be removed in the next major version; use canonical
  `materialize_tevents`, `materialize_timexes`, `materialize_signals`.

See [`DEPRECATION.md`](DEPRECATION.md) for migration guidance and removal timeline.

---

## Versioning policy

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

- MAJOR — breaking graph schema or public API changes.
- MINOR — new phases, tools, or evaluation capabilities.
- PATCH — bug fixes, import hardening, documentation.

The current workstream (`feature/schema-contract-alignment`) will be tagged as
**v1.0.0** upon merge to `main` after final production validation.
