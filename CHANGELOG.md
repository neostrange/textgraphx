# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-04-30

### Added

#### M1: Unified Evaluation Schema
- **File:** [docs/MILESTONE1_UNIFIED_EVALUATION_SCHEMA.md](docs/MILESTONE1_UNIFIED_EVALUATION_SCHEMA.md)
- Unified evaluation schema across all phases (M1–M10)
- Run-metadata hashing for reproducible evaluation tracking
- Determinism verification framework (`evaluation/determinism.py`)
- See: [src/textgraphx/evaluation/unified_metrics.py](src/textgraphx/evaluation/unified_metrics.py)

#### M2: Mention Layer Evaluator
- **File:** [MILESTONES_2_7_PHASE_EVALUATORS.md](docs/MILESTONES_2_7_PHASE_EVALUATORS.md)
- Mention-layer quality evaluation (`NamedEntity`, `EventMention`, `TimexMention`)
- Surface-form normalization and canonical resolution assessment
- See: [src/textgraphx/evaluation/mention_layer_evaluator.py](src/textgraphx/evaluation/mention_layer_evaluator.py)

#### M3: Edge Semantics Evaluator
- Relationship validity and semantic-correctness assessment
- Cross-phase edge traceability
- See: [src/textgraphx/evaluation/edge_semantics_evaluator.py](src/textgraphx/evaluation/edge_semantics_evaluator.py)

#### M4: Phase Assertion Evaluator
- Phase-contract assertions for ingestion, refinement, temporal, event-enrichment, and TLINK phases
- Input/output contract validation per [docs/architecture-overview.md](docs/architecture-overview.md)
- See: [src/textgraphx/evaluation/phase_assertion_evaluator.py](src/textgraphx/evaluation/phase_assertion_evaluator.py)

#### M5: Semantic Category Evaluator
- Entity, Event, TIMEX, and Frame category quality
- Semantic consistency across annotations
- See: [src/textgraphx/evaluation/semantic_category_evaluator.py](src/textgraphx/evaluation/semantic_category_evaluator.py)

#### M6: Legacy Layer Evaluator
- Backward-compatibility validation for deprecated API surface
- Shim function verification (GraphBasedNLP, RefinementPhase, etc.)
- See: [src/textgraphx/evaluation/legacy_layer_evaluator.py](src/textgraphx/evaluation/legacy_layer_evaluator.py)

#### M8: MEANTIME Bridge Validator
- MEANTIME gold-standard corpus bridge
- Cross-phase consistency validation
- TEvent/TIMEX/TLINK alignment with MEANTIME annotations
- See: [src/textgraphx/evaluation/meantime_bridge.py](src/textgraphx/evaluation/meantime_bridge.py) and [docs/MILESTONE8_BRIDGE_VALIDATOR.md](docs/MILESTONE8_BRIDGE_VALIDATOR.md)

#### M9–M10: Regression Detection & CI Integration
- Regression baseline tracking
- Golden-baseline comparison
- CI quality gates
- See: [src/textgraphx/evaluation/regression_detector.py](src/textgraphx/evaluation/regression_detector.py), [ci_integration.py](src/textgraphx/evaluation/ci_integration.py)

#### Evaluation Framework Documentation
- [COMPREHENSIVE_EVALUATION_FRAMEWORK.md](docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md) — Full M1–M10 roadmap
- [EVALUATION_ROADMAP_M1_TO_M10.md](docs/EVALUATION_ROADMAP_M1_TO_M10.md) — Milestone sequencing
- [EVALUATION_DIAGNOSTICS.md](docs/EVALUATION_DIAGNOSTICS.md) — Troubleshooting and diagnostic tooling

### Schema & Migrations

#### 27 Applied Schema Migrations (0001–0027)
- **Repository:** [src/textgraphx/schema/migrations/](src/textgraphx/schema/migrations/)

**Recent key migrations:**
- `0025_nounchunk_uniqueness.cypher` — Entity uniqueness constraints
- `0026_add_mention_superlabel.cypher` — Explicit Mention-layer formalization
- `0027_graph_native_edges.cypher` — Graph-native edge encoding (latest applied)

**Schema authority:** Migration precedence enforced per [PROVENANCE_AUTHORITY_POLICY.md](docs/PROVENANCE_AUTHORITY_POLICY.md)
- Runtime write paths (pipeline phases) take precedence over migrations
- Applied migrations take precedence over schema documentation

### Pipeline & Orchestration

#### Ingestion Phase (Stage 1)
- Token-graph construction via `GraphBasedNLP`
- Sentence and syntactic dependency annotation
- Named entity and SRL frame extraction

#### Refinement Phase (Stage 2)
- Mention normalization and canonical resolution
- Coreference linking to canonical `Entity` nodes

#### Temporal Phase (Stage 3)
- TIMEX extraction and normalization
- TEvent creation and annotation
- Temporal anchoring

#### Event Enrichment Phase (Stage 4)
- EventMention linking to extracted TEvents
- Frame attachment and argument role assignment

#### TLINK Recognition Phase (Stage 5)
- Inter-event and event-timex temporal relations
- TLINK inference and annotation

#### Orchestration Features
- Checkpoint-based recovery (phase-level granularity)
- Execution history tracking
- Deterministic scheduling (sorted file processing)
- Phase completion markers for idempotency

See: [docs/RUNNING_PIPELINE.md](docs/RUNNING_PIPELINE.md), [PIPELINE_INTEGRATION.md](docs/PIPELINE_INTEGRATION.md)

### Documentation & Governance

#### Canonical Documentation
- [docs/architecture-overview.md](docs/architecture-overview.md) — Pipeline design and phase contracts
- [docs/schema.md](docs/schema.md) — Schema reference with all canonical labels and properties
- [docs/ontology.yaml](docs/ontology.yaml) — Human-readable ontology
- [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) — Narrative project context
- [CONTRIBUTING.md](CONTRIBUTING.md) — Branch, PR, and documentation workflow
- [.github/copilot-instructions.md](.github/copilot-instructions.md) — Project-wide architecture and engineering discipline (canonical reference)

#### Governance Documentation
- [DOCUMENTATION.md](DOCUMENTATION.md) — Documentation gateway and link authority
- [DEPRECATION.md](DEPRECATION.md) — Deprecation schedule for root-level backward-compatibility shims
- [PROVENANCE_AUTHORITY_POLICY.md](docs/PROVENANCE_AUTHORITY_POLICY.md) — Schema authority precedence
- [PRODUCTION_VALIDATION.md](docs/PRODUCTION_VALIDATION.md) — Production readiness checklist

### Testing Infrastructure

#### Comprehensive Test Suite (~143 tests)
- **Unit tests** (`@pytest.mark.unit`) — Isolated component tests
- **Integration tests** (`@pytest.mark.integration`) — Cross-component tests with live Neo4j
- **Contract tests** (`@pytest.mark.contract`) — Hard-contract schema invariants
- **Regression tests** (`@pytest.mark.regression`) — Golden-baseline tests
- **Scenario tests** (`@pytest.mark.scenario`) — End-to-end orchestration workflows
- **Orchestration tests** (`@pytest.mark.orchestration`) — Orchestrator-specific

**Test infrastructure:**
- [src/textgraphx/tests/conftest.py](src/textgraphx/tests/conftest.py) — Neo4j reachability probe and fixtures
- [src/textgraphx/tests/README_TESTS.md](src/textgraphx/tests/README_TESTS.md) — Test organization and quick-start

### Backward Compatibility & Deprecation

#### Root-Level Compatibility Shims (Deprecated)
All of the following re-export from canonical paths with `DeprecationWarning`:
- `GraphBasedNLP.py` → `pipeline.ingestion.graph_based_nlp`
- `RefinementPhase.py` → `pipeline.phases.refinement`
- `TemporalPhase.py` → `pipeline.phases.temporal`
- `EventEnrichmentPhase.py` → `pipeline.phases.event_enrichment`
- `TlinksRecognizer.py` → `pipeline.phases.tlinks_recognizer`
- `PipelineOrchestrator.py` → `orchestration.orchestrator`

**Migration path:** All new code must import from canonical paths per [.github/copilot-instructions.md](.github/copilot-instructions.md) §4.

### Repository Hygiene

- Enforced `.gitignore` for runtime artifacts (evaluation outputs, checkpoints, mock artifacts)
- Evaluation artifacts written exclusively to `src/textgraphx/datastore/evaluation/`
- No machine-local absolute paths in committed source code
- Secrets audit: no API keys or credentials in source

---

## [Unreleased] (current: `feature/entity-extraction-refinement-2026`)

### In Progress

#### Entity Extraction & Refinement Enhancements
- Targeted refinement to entity mention normalization
- See branch: `feature/entity-extraction-refinement-2026`

---

## References

- **Evaluation Framework:** [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md)
- **Schema Design:** [docs/schema.md](docs/schema.md), [docs/schema-evolution-plan.md](docs/schema-evolution-plan.md)
- **Architecture:** [docs/architecture-overview.md](docs/architecture-overview.md)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
