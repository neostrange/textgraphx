<!--
  textgraphx — GitHub Copilot Workspace Instructions
  Audience: Copilot and human contributors
  Scope: Project-wide conventions, architecture, and engineering discipline
-->

# textgraphx — Copilot Instructions

## 1. Project Identity

**textgraphx** is an event-centric, temporally-grounded knowledge graph (KG) construction system. It transforms unstructured natural-language text into a Neo4j labelled property graph (LPG) in which linguistic structure (morphology, syntax, semantics, discourse) is represented as a queryable substrate, and higher-order semantic objects — entities, events, temporal expressions, frames, and temporal relations — are extracted as first-class graph elements.

Every inference is **token- and span-grounded** to guarantee provenance, traceability, and reproducibility. The reference evaluation standard is the **MEANTIME** corpus, against which all extraction phases are measured (M1–M10 evaluation framework).

### 1.1 Differentiators

textgraphx distinguishes itself from generic NLP-to-graph stacks (e.g., spaCy + Neo4j cookbooks, LangChain GraphRAG, RebelKG) along four dimensions:

1. **Temporal rigor** — first-class TEvents, TIMEX, and TLINK relations evaluated against MEANTIME gold annotations.
2. **Deterministic provenance** — node identity is derived from document content, not random IDs; every edge carries source attribution.
3. **Tiered extraction methodology** — deterministic rules, specialized ML models, and LLMs are layered by cost and necessity (see §3).
4. **Phase-contract evaluation** — each pipeline phase has explicit input/output contracts validated by CI quality gates.

### 1.2 Target Applications

- Knowledge-graph-backed retrieval-augmented generation (**GraphRAG**)
- Ontology learning and population
- Neuro-symbolic reasoning
- Temporal question answering
- Data lineage and provenance auditing over textual corpora

---

## 2. Tech Stack

| Layer | Technology | Version |
|------|-----------|---------|
| Language | Python | ≥ 3.8 |
| NLP | spaCy | ≥ 3.8 |
| Auxiliary NLP | NLTK | ≥ 3.8 |
| Graph database | Neo4j | ≥ 5.9 |
| API | FastAPI + uvicorn | ≥ 0.104 / ≥ 0.24 |
| Scheduling | APScheduler | ≥ 3.10 |
| Logging | python-json-logger | ≥ 2.0 |
| Testing | pytest + pytest-asyncio + pytest-cov + pytest-mock | ≥ 7.0 |
| Verbal SRL | transformer-srl 2.4.6 | Port 8010 (`/predict`) |
| Nominal SRL | CogComp SRL-English (NomBank) | Port 8011 (`/predict_nom`) |
| Coreference | spacy-experimental-coref | In-process spaCy component |

License posture: **open source, permissively licensed** components preferred. See [pyproject.toml](../pyproject.toml) for the authoritative dependency list.

---

## 3. Extraction Methodology — Three Tiers

textgraphx layers extraction techniques by cost, determinism, and necessity. New code should default to the lowest applicable tier.

| Tier | Technique | When to use |
|------|-----------|-------------|
| **T1 — Deterministic rules** | Cypher patterns, dependency-tree templates, lexical heuristics | Whenever the linguistic signal is structurally explicit |
| **T2 — Specialized ML** | spaCy (NER, SRL, coref), task-specific classifiers | When T1 has insufficient recall or coverage |
| **T3 — LLMs** | Prompted large language models | Only for tasks where T1 and T2 demonstrably underperform |

This layering is enforced by convention: contributions that introduce LLM calls must justify why T1/T2 are insufficient and must include a deterministic fallback path.

---

## 4. Source Layout

```
src/textgraphx/
├── pipeline/ingestion/          # Stage 1: graph construction (GraphBasedNLP, text processors)
├── pipeline/phases/             # Stages 2–5: refinement → temporal → enrichment → tlinks
├── pipeline/temporal/           # Temporal extraction and TLINK inference
├── orchestration/               # PipelineOrchestrator, checkpointing, run history
├── evaluation/                  # M1–M10 quality evaluation framework
├── database/                    # Neo4j connection and schema constraints
├── schema/                      # ontology.json/yaml + versioned migrations
├── tools/                       # CLI diagnostics, quality gates, migration runners
├── reasoning/                   # Semantic reasoning components
├── datastore/                   # Bundled datasets, gold-standard annotations, baselines
├── tests/                       # 140+ tests (conftest.py, README_TESTS.md)
└── utils/ fixtures/             # Shared helpers and test fixtures
```

**Compatibility shims.** Root-level files (`GraphBasedNLP.py`, `RefinementPhase.py`, `TemporalPhase.py`, `EventEnrichmentPhase.py`, `TlinksRecognizer.py`, `PipelineOrchestrator.py`) re-export from the canonical `pipeline/` and `orchestration/` sub-packages. **All new code must import from the canonical paths.**

---

## 5. Architectural Conventions

### 5.1 Identity & Determinism

- Node IDs are deterministic (document-content hash → stable integer fallback). **Never generate random IDs.**
- Files are processed in **sorted order** to guarantee reproducibility across runs.
- Each phase writes a completion marker to the graph for traceability and idempotency.
- Determinism is verified by dedicated tests (`evaluation/determinism.py`).

### 5.2 Schema Layering

Three-tier schema model:

- **Canonical** — required for runtime and evaluation; CI-blocking.
- **Optional** — enrichment and observability signals; advisory.
- **Legacy** — preserved during active migration windows; removed only via explicit migration + coordinated query updates.

### 5.3 Schema Authority Precedence

When schema statements conflict, the higher-precedence source wins:

1. Runtime write paths (`pipeline/ingestion/`, `pipeline/phases/`)
2. Applied migrations (`schema/migrations/`)
3. [docs/schema.md](../docs/schema.md)
4. `schema/ontology.json`
5. Historical / explanatory documentation

### 5.4 Hard Contracts (CI-blocking)

- `doc_id` and type consistency on all document-scoped nodes
- Referential integrity: `Mention → REFERS_TO → Entity / TEvent / TIMEX`
- Required core fields on canonical labels
- Span integrity: `start_tok <= end_tok`

### 5.5 Advisory Contracts (warn only)

- Enrichment-profile completeness
- Optional provenance on inferred edges
- Transitional dual-edge usage (e.g., `PARTICIPANT` vs `EVENT_PARTICIPANT`)

### 5.6 Core Graph Vocabulary

**Node labels.** `AnnotatedText`, `Sentence`, `TagOccurrence`, `NamedEntity`, `Entity`, `TimexMention`, `TIMEX`, `TEvent`, `EventMention`, `Frame`, `FrameArgument`.

**Relationships.** `HAS_TOKEN`, `HAS_NEXT`, `IS_DEPENDENT`, `REFERS_TO`, `EVENT_PARTICIPANT`, `INSTANTIATES`, `TLINK`, `HAS_LEMMA`, `ALIGNS_WITH`.

**Required properties.** `doc_id`, `start_tok`, `end_tok`, `text`, `lemma`, `confidence`, `source`.

### 5.7 Mention vs Canonical Layer

The mention layer is explicitly separated from the canonical layer wherever feasible: e.g., `NamedEntity` (mention surface form) is distinct from `Entity` (canonical referent). Coreference and entity linking populate the `REFERS_TO` bridge.

### 5.8 Semantic Role Labeling (SRL) Frameworks

textgraphx ingests evidence from two SRL frameworks. Both are first-class but must be persisted with explicit framework attribution.

| Framework | Service | Port | Predicates | Sense field |
|-----------|---------|------|------------|-------------|
| PROPBANK | transformer-srl 2.4.6 | 8010 | Verbal | `frame` (e.g., `attack.01`) |
| NOMBANK | CogComp SRL-English | 8011 | Nominal | `sense` (e.g., `attack.01`) |

**Rules for all SRL code:**

- Every `Frame` node **must** carry `framework ∈ {PROPBANK, NOMBANK}`. Default `PROPBANK` is permitted only for the verbal writer path.
- `sense` and `sense_conf` are advisory-tier properties; they are mandatory when the upstream service supplies them, otherwise omitted (never `null`).
- `provisional = true` is set on frames whose `sense_conf` is below `config.ingestion.frame_confidence_min` (default 0.50).
- Argument labels are **normalized at ingestion**: `C-`/`R-` prefixes become edge properties (`is_continuation`, `is_relative`); `-PRD` suffix becomes `predicative=true`. The original label is preserved as `raw_role` on the edge.
- Verbal and nominal frames describing the same situation (same headword lemma, head token within `TOKEN_WINDOW=5`) are linked with `(:Frame)-[:ALIGNS_WITH]->(:Frame)`. The higher-confidence frame is the canonical `INSTANTIATES` target.
- Light-verb constructions (make/give/take/have/do/get…) set `is_light_verb_host=true` on the verbal frame; the nominal frame carries the event.
- The SRL service URL defaults are: `srl_url=http://localhost:8010/predict`, `nom_srl_url=http://localhost:8011/predict_nom`. Override with `TEXTGRAPHX_SRL_URL` / `TEXTGRAPHX_NOM_SRL_URL`. An empty `nom_srl_url` disables the nominal pass.
- A legacy-schema warning is emitted (as `WARNING`) when the SRL service returns AllenNLP-style responses (no `frame` field). See `adapters/rest_caller.py::_detect_legacy_srl_schema`.

### 5.9 Coreference Backend Policy

- **Canonical backend:** `spacy-experimental-coref` (in-process spaCy component).
- maverick-coref is **deprecated** due to CPU cost. Setting `MAVERICK_COREF_URL` or `TEXTGRAPHX_MAVERICK_COREF_URL` triggers a `DeprecationWarning` at config load. See [docs/COREF_POLICY.md](../docs/COREF_POLICY.md).
- Every `REFERS_TO` edge written from coref must carry `source='spacy-experimental-coref'` and a deterministic `cluster_id`.
- Do **not** add code paths that depend on maverick-coref without first updating `COREF_POLICY.md` and meeting all re-evaluation criteria defined there.

---

## 6. Pipeline Stages

| Stage | Module | Responsibility |
|------|--------|----------------|
| 1. Ingestion | `pipeline/ingestion/` | Build initial token / sentence / entity / SRL graph |
| 2. Refinement | `pipeline/phases/refinement.py` | Mention normalization and canonical resolution |
| 3. Temporal | `pipeline/phases/temporal.py` | TIMEX and TEvent extraction |
| 4. Event enrichment | `pipeline/phases/event_enrichment.py` | EventMention linking and frame attachment |
| 5. TLINK recognition | `pipeline/phases/tlinks_recognizer.py` | Inter-event temporal relations |

Orchestration, checkpointing, and run-history tracking live in [orchestration/](../src/textgraphx/orchestration/).

---

## 7. Testing

Tests reside in `src/textgraphx/tests/` (~140 files). Markers are declared in [pyproject.toml](../pyproject.toml).

| Marker | Use for |
|--------|---------|
| `@pytest.mark.unit` | Isolated component tests; no DB or external services |
| `@pytest.mark.integration` | Cross-component tests; may require live Neo4j |
| `@pytest.mark.regression` | Golden-baseline tests capturing known-good behavior |
| `@pytest.mark.scenario` | End-to-end orchestration workflows |
| `@pytest.mark.orchestration` | Orchestrator-specific |
| `@pytest.mark.slow` | Long-running tests; excluded from pre-merge runs |

### 7.1 Recommended Commands

```bash
# Fast smoke check (pre-commit)
pytest src/textgraphx/tests -m "unit or contract" -q

# Targeted iteration during development
pytest src/textgraphx/tests -k "test_module_name" -v

# Pre-merge sweep
pytest src/textgraphx/tests -m "not slow" -q

# Full suite (requires live Neo4j)
pytest src/textgraphx/tests -m "integration or scenario" -v
```

### 7.2 Test Discipline

- **Contract tests** validate hard-contract schema invariants.
- **Phase-assertion tests** verify each phase's declared output contract.
- **Regression tests** lock in behavior across refactors (golden baselines in `datastore/evaluation/baseline`).
- **Determinism tests** verify identical outputs across repeated runs.

---

## 8. Evaluation Framework (M1–M10)

Located in [src/textgraphx/evaluation/](../src/textgraphx/evaluation/). See [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](../docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md).

| Milestone | Scope |
|-----------|-------|
| M1 | Unified evaluation schema, run-metadata hashing, determinism verification |
| M2 | Mention-layer quality |
| M3 | Edge-semantics quality |
| M4 | Phase-contract assertions |
| M5 | Semantic-category quality |
| M6 | Legacy-layer / backward compatibility |
| M7 | Full-stack end-to-end harness |
| M8 | MEANTIME bridge + cross-phase consistency validator |
| M9–M10 | Regression baselines + CI quality gates |

---

## 9. Documentation Discipline

- Any behavioral change requires a corresponding documentation update — the **Docs-update-required** rule (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
- New documents must be linked from [DOCUMENTATION.md](../DOCUMENTATION.md) and [docs/README.md](../docs/README.md).
- Outdated documents are moved to [docs/archive/](../docs/archive/); they are **never deleted**.
- CHANGELOG entries must link to updated docs.

---

## 10. Repository Hygiene

**Do NOT commit:**

- Runtime checkpoints or evaluation JSON/CSV files at the repo root
- Dataset copies outside `src/textgraphx/datastore/`
- Machine-local absolute paths
- LLM API keys, Neo4j credentials, or any secrets

**Datastore paths (canonical):**

```
src/textgraphx/datastore/dataset             # Evaluation datasets
src/textgraphx/datastore/annotated           # Gold standard annotations
src/textgraphx/datastore/evaluation/latest   # Latest evaluation results
src/textgraphx/datastore/evaluation/baseline # Regression baselines
```

---

## 11. Forward-Looking Vision (Roadmap, Not Current State)

The sections above describe the **current** system. The following are stated **roadmap objectives** to inform architectural reasoning; they should *not* be assumed implemented when generating code or tests.

### 11.1 Two Autonomy Goals

1. **System autonomy** — unattended ingestion-to-graph operation across the full lifecycle (acquire → extract → integrate → publish → monitor) without human intervention.
2. **KG autonomy** — self-correcting and self-healing graphs that detect contradictions, repair broken references, prune stale facts, and reconcile new evidence with existing claims.

### 11.2 Likely Implementation Strategy

The current procedural orchestration is expected to evolve toward an **agentic architecture** in which specialized agents own extraction, validation, repair, and reasoning loops. Agentic design is treated as a likely *implementation strategy* for autonomy — not as a definition of it. Autonomy may also be partially realized through deterministic state machines and scheduled workflows.

### 11.3 Planned Semantic Categories

Beyond the current Entity / Event / TIMEX / Frame ontology, future work targets richer meaning representations:

- **Situations** — modelled with reference to Situation Calculus (McCarthy, Reiter) or Barwise–Perry situation semantics.
- **Scenarios** — frame-semantic and script-theoretic representations of stereotyped event sequences (Fillmore; Schank & Abelson).
- **Procedures** — process-model representations (BPMN-like or PDDL-like) with explicit pre- and post-conditions.

A motivating downstream application is **situational awareness and assessment**, with Endsley's three-level model (perception → comprehension → projection) as a candidate organizing framework.

When implementing any of the above, align schema labels to **one** established framework per concept rather than inventing new vocabulary.

---

## 12. Key Reference Documents

- [docs/architecture-overview.md](../docs/architecture-overview.md) — pipeline design and phase contracts
- [docs/schema.md](../docs/schema.md) — canonical schema and property reference
- [docs/ontology.yaml](../docs/ontology.yaml) — human-readable ontology
- [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](../docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md) — M1–M10 evaluation roadmap
- [docs/PROJECT_CONTEXT.md](../docs/PROJECT_CONTEXT.md) — narrative project context
- [CONTRIBUTING.md](../CONTRIBUTING.md) — branching, PR, and documentation workflow
- [CHANGELOG.md](../CHANGELOG.md) — release-level change history
