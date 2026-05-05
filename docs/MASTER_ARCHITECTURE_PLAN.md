# TextGraphX: Master Architectural Blueprint & Comprehensive Transformation Plan

**Date:** May 2026  
**Status:** Living document — update on each major milestone completion  
**Author:** Senior Architecture Review  
**Scope:** Full-stack analysis of current architecture, enumerated technical debt, phase-by-phase transformation roadmap, DAG orchestration design, discourse engine integration, schema evolution, and governance rules.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Contextual Framing: What This System Is Trying to Do](#2-contextual-framing)
3. [Critical Analysis of Current Architecture](#3-critical-analysis)
   - 3.1 Structural Problems
   - 3.2 Orchestration Problems
   - 3.3 Linguistic Capability Gaps
   - 3.4 Schema & Provenance Problems
4. [What the System Gets Right (Preserve These)](#4-what-the-system-gets-right)
5. [Transformation Roadmap: Three Structural Phases](#5-transformation-roadmap)
   - Phase A: Contract-Driven Decomposition
   - Phase B: DAG Orchestration
   - Phase C: Discourse & Situational Awareness Engine
6. [Target Architecture: Annotated Component Diagram](#6-target-architecture)
7. [Detailed Phase Design](#7-detailed-phase-design)
   - 7.1 Ingestion Layer
   - 7.2 Refinement Decomposition
   - 7.3 Temporal Extraction
   - 7.4 Event Enrichment
   - 7.5 TLINK Recognition
   - 7.6 Discourse Engine (New)
   - 7.7 Reasoning & Fusion Layer
8. [DAG Orchestrator Design](#8-dag-orchestrator-design)
9. [Schema Evolution Plan](#9-schema-evolution-plan)
10. [Testing & Evaluation Strategy](#10-testing--evaluation-strategy)
11. [Architecture Governance Rules](#11-architecture-governance-rules)
12. [Implementation Sequencing & Milestones](#12-implementation-sequencing--milestones)
13. [Risk Register](#13-risk-register)

---

## 1. Executive Summary

TextGraphX is a temporally-grounded knowledge graph construction system that converts unstructured natural-language documents into a queryable Neo4j labelled property graph. Its differentiating goal — event-centric representation grounded at the token level with full provenance — is sound and worth pursuing. However, the path to achieving **situational awareness** (Endsley's three levels: perception, comprehension, projection) is blocked by four categories of architectural debt that this document analyzes and resolves.

**The core problem in one sentence:** the system extracts *what* happened (entities, events, arguments) with reasonable fidelity, but cannot reliably infer *why*, *how*, or *what happens next* — the inferential glue required for situational awareness — because: (a) phases are too tightly coupled to allow feedback-driven refinement, (b) the orchestrator enforces a linear sequence that violates linguistic layer dependencies, (c) discourse-level structure (RST trees, PDTB relations, event coreference) is entirely absent, and (d) the `RefinementPhase` God Object blocks compositional evolution.

This plan is not a rewrite. It is a disciplined, phased transformation that preserves what works, eliminates what blocks progress, and adds the missing layers in priority order.

---

## 2. Contextual Framing: What This System Is Trying to Do

To evaluate architecture correctly, we must hold the system's functional goals clearly:

| Goal | Current Capability | Gap |
|------|--------------------|-----|
| Extract entities, events, and temporal expressions from text | Strong — MEANTIME-aligned, token-grounded | Minor property enrichment gaps |
| Ground each extraction to a token span with provenance | Strong — `doc_id`, `start_tok`, `end_tok` on all nodes | Provenance on inferred/discourse edges is missing |
| Establish temporal ordering between events (TLINK) | Moderate — heuristics + rule-based | Missing cross-sentence temporal reasoning |
| Establish causal and subordinating relations between events (CLINK) | Weak — sparse signal-based heuristics only | No PDTB, no causal signal extractor |
| Understand *why* events occur and their consequences | Absent | Requires PDTB/RST discourse layer |
| Project likely future event sequences (situational awareness Level 3) | Absent | Requires event coreference + script theory |
| Support multi-document reasoning over a corpus | Partial — `SAME_AS`/`CO_OCCURS_WITH` entity fusion | No cross-document event linking |
| Self-correct contradictions and update beliefs | Absent | Requires agentic repair loop |

The architectural transformation is ordered to close these gaps sequentially without disrupting existing extraction quality.

---

## 3. Critical Analysis of Current Architecture

### 3.1 Structural Problems

#### 3.1.1 The `RefinementPhase` God Object

`src/textgraphx/pipeline/phases/refinement.py` is a single class exceeding 3,000 lines. It contains:

- Head-token assignment for `NamedEntity`, `CorefMention`, `Antecedent`, and `FrameArgument` nodes (16+ methods in the `head_assignment` family)
- Frame–entity linking for 12+ different syntactic configurations
- Numeric entity promotion
- Coreference chain resolution
- SRL argument normalization
- Entity type coercion
- Cross-document entity linking stubs

This violates the Single Responsibility Principle at every level. The consequence is not merely aesthetic: the file cannot be unit-tested in isolation, changes to head-assignment logic silently break frame-linking paths, and the extraction order within the class is implicit and brittle.

**Critical fact:** the file declares a `RULE_FAMILIES` dictionary that groups methods into logical families (`head_assignment`, `linking`, etc.). This is an unused taxonomy that signals the original intent was decomposition — it was never executed.

#### 3.1.2 Root-Level Shims

The repository root contains `GraphBasedNLP.py`, `RefinementPhase.py`, `TemporalPhase.py`, `EventEnrichmentPhase.py`, `TlinksRecognizer.py`, and `PipelineOrchestrator.py` as re-export shims. These shims exist because the canonical modules were relocated under `src/textgraphx/pipeline/` but external callers were not updated. They are a maintenance liability: they prevent the import graph from being accurate, they shadow canonical paths in IDE tooling, and they will accumulate divergence over time.

#### 3.1.3 Database as the Sole Inter-Phase Communication Medium

Phases have no typed output contract. A phase finishes when it has executed its Cypher queries; the next phase begins with no guarantees about what the graph contains beyond an informal convention. Concretely:

- `IngestionPhase` must complete before `RefinementPhase` reads its output, but nothing enforces this except execution order.
- `RefinementPhase` must complete before `TemporalPhase`, but if Refinement partially fails, Temporal continues against a corrupt intermediate graph.
- `EventEnrichmentPhase` depends on TIMEX and TEvent nodes created by `TemporalPhase`, but there is no contract object describing this dependency.

The `PhaseResult` dataclass exists in `orchestrator.py` but carries only execution metadata (`status`, `duration`, `documents_processed`). It does not carry graph output contracts. This is an audit stamp, not a contract.

#### 3.1.4 Raw Cypher Strings Embedded in Business Logic

Across ingestion and refinement, Cypher strings are constructed directly in method bodies with `MATCH`/`MERGE`/`CREATE` statements. While the project's Cypher instruction file mandates parameterization, many legacy methods use string interpolation or concatenation rather than parameterized queries. This conflates data access logic with business rules and makes Cypher optimization (index hints, query plan tuning) impossible without modifying phase logic.

### 3.2 Orchestration Problems

#### 3.2.1 Hardcoded Linear Phase Sequence

`PipelineOrchestrator.default_phases()` returns the fixed list:

```python
["ingestion", "refinement", "temporal", "event_enrichment", "tlinks"]
```

This sequence violates the actual dependency structure of linguistic analysis in two ways:

1. **Temporal extraction depends on event enrichment, not just on refinement.** TIMEX normalization benefits from knowing event class and aspect (PERFECTIVE events anchor differently than PROGRESSIVE ones). Running `temporal` before `event_enrichment` means temporal reasoning operates on structurally incomplete events.

2. **Event coreference (which is a refinement operation) depends on TLINKs.** Two events that appear to be distinct (`the attack` and `the bombing`) may only be identifiable as coreferential after their temporal positions are established. The rigid sequence prevents this feedback.

3. **PropBank/NomBank SRL are run sequentially inside Ingestion** even though they are independent services (ports 8010 and 8011). There is no design reason these cannot run in parallel.

#### 3.2.2 No Bounded Iterative Refinement

Modern NLP systems for temporal reasoning (e.g., CAEVO, SynTime+) achieve better precision through multiple passes: a first pass extracts candidates, a second pass resolves conflicts and propagates constraints. TextGraphX has no mechanism for bounded re-execution of a phase on a subset of documents or nodes. If a `TEvent` receives a conflicting TLINK, the system has no way to trigger a localized re-evaluation.

#### 3.2.3 Checkpoint Granularity

The current `CheckpointManager` writes completion flags at the document-level for phase-level transitions. This is coarse. If `RefinementPhase` succeeds for documents 1–18 and fails on document 19, the checkpoint shows `refinement=incomplete` and re-runs all 19 documents. A finer-grained checkpoint (per-document, per-phase) would enable efficient resume-on-failure, which is critical for production-scale corpora.

### 3.3 Linguistic Capability Gaps

This section maps the gap analysis from `docs/research/2026-05-02-discourse-and-large-context-rnd.md` to concrete architectural implications.

#### 3.3.1 No Discourse Structure

The system has no Elementary Discourse Unit (EDU) segmenter and no RST parser. Rhetorical structure determines what text is central (Nucleus) versus supporting (Satellite) — this directly affects event salience scoring and contradiction detection. Without it, all sentences are structurally flat and equally weighted.

**Practical consequence:** a TLINK between `event A` and `event B` may be drawn across a contrastive satellite clause (e.g., "Although the ceasefire held, violence continued"), inverting the intended polarity. The system cannot detect this.

#### 3.3.2 No PDTB Discourse Relation Extraction

PDTB (Penn Discourse Treebank) annotates explicit and implicit discourse connectives and their arguments. Explicit connectives (`because`, `although`, `in order to`, `as a result`) are T1 (deterministic rule) signals. Implicit relations require a sentence-pair classifier. TextGraphX has `CSignal` nodes (for causal signals) but no systematic PDTB-style extraction pipeline. The existing `CLINK` heuristics fire only on a narrow set of lexical triggers; they miss the majority of causal relations in news text.

#### 3.3.3 Event Coreference Is Partial

The system has entity coreference resolution via `spacy-experimental-coref`, but event coreference is handled only through the `EventMention → REFERS_TO → TEvent` bridge established by the `EventEnrichmentPhase`. This bridge only fires when a Frame node is already linked to a TEvent. It does not resolve cases where two different predicates in different sentences refer to the same real-world event (e.g., "the explosion" and "the blast" in the same document). This creates fragmented event timelines.

#### 3.3.4 No Cross-Document Event Linking

`reasoning/fusion.py` implements `fuse_entities_cross_document()` using `kb_id` equality to create `SAME_AS` edges between canonical `Entity` nodes across documents. There is no equivalent mechanism for `TEvent` nodes. Two `TEvent` nodes describing the same real-world event across two news articles (e.g., the same assassination reported in two corpora) will never be linked. This is a fundamental gap for any multi-document or longitudinal reasoning use case.

#### 3.3.5 No Script or Event-Chain Representation

Script theory (Schank & Abelson) proposes that stereotyped event sequences (`AttackScenario`: detection → engagement → aftermath) serve as comprehension frames. Without this layer, the system cannot project likely next events (Endsley Level 3: projection) from the current event state. There is no `Scenario` node type, no `SCRIPT_ROLE` edge, and no mechanism to bind extracted events to scenario templates.

#### 3.3.6 Attribution Modeling Is Shallow

The system partially models factuality (via `FactBank`-style scalar labels on `EventMention` nodes) but does not model the attribution source: who claims this event occurred? What is their reliability? News texts frequently contain embedded attribution (`"officials said..."`, `"witnesses reported..."`). Without first-class `AttributedClaim` nodes carrying speaker, proposition, and stance properties, the system cannot distinguish direct observations from hearsay — a critical requirement for intelligence-grade situational awareness.

### 3.4 Schema & Provenance Problems

#### 3.4.1 Dual-Edge Transitional State

The system is mid-migration between legacy edge types (`PARTICIPANT`, `DESCRIBES`) and canonical types (`EVENT_PARTICIPANT`, `FRAME_DESCRIBES_EVENT`). Both edges co-exist in production graphs. Runtime readers are canonical-first with legacy fallback. While the `strict_transition_gate` in testing mode promotes legacy-dominance warnings to failures, the legacy dual-edge state should be eliminated with a firm deadline. Every additional feature built atop a dual-edge schema doubles the query surface and complicates evaluation.

#### 3.4.2 Inferred Edge Provenance Is Inconsistent

Hard-contract edges (those written by deterministic extraction rules) carry `source`, `confidence`, and `rule_id` properties consistently. Inferred edges (those written by heuristic fusion methods such as `CO_OCCURS_WITH` and discourse-level edges) apply these properties inconsistently. When an edge is written by `fuse_entities_cross_document()`, it receives `evidence_source` and `rule_id`. When a `TLINK` is written by heuristic, it may not receive `rule_id`. This makes automated provenance audits partial.

---

## 4. What the System Gets Right (Preserve These)

Before prescribing changes, it is essential to enumerate what is working well. These are architectural assets, not liabilities.

| Asset | Why It Matters |
|-------|----------------|
| **Deterministic node identity** (hash → stable integer) | Reproducibility guarantees; enables safe re-runs and regression tests |
| **Token-span grounding on all canonical nodes** (`start_tok`, `end_tok`, `doc_id`) | First-class provenance; every claim traces to source text |
| **Mention / Canonical layer separation** (`NamedEntity` ↔ `Entity`, `EventMention` ↔ `TEvent`) | Prerequisite for coreference, entity linking, and claim attribution |
| **Three-tier extraction methodology** (T1 rules → T2 ML → T3 LLM) | Cost-aware extraction with explicit escalation policy |
| **Phased schema migrations** (`schema/migrations/`) | Auditable, versioned schema evolution |
| **MEANTIME M1–M10 evaluation framework** | Quantitative quality gates against gold annotations |
| **Dual-SRL framework** (PropBank + NomBank) | Verbal + nominal predicates both captured; unusual in open-source stacks |
| **`PhaseResult` checkpoint infrastructure** | Foundation for per-document fault isolation (needs extension, not replacement) |
| **`strict_transition_gate`** | Prevents regressions during active schema migration windows |

---

## 5. Transformation Roadmap: Three Structural Phases

The transformation is organized into three sequential phases. Each phase has clear entry and exit criteria linked to the M1–M10 evaluation milestones. No phase starts until the previous phase's exit criteria are met.

```
Phase A: Contract-Driven Decomposition      (M1–M4 exit gate)
Phase B: DAG Orchestration                  (M5–M6 exit gate)  
Phase C: Discourse & Situational Awareness  (M7–M10 exit gate)
```

### Phase A: Contract-Driven Decomposition

**Objective:** Eliminate the God Object, enforce typed inter-phase contracts, remove root shims, and isolate Cypher in a data access layer.

**Entry criteria:** Current test suite passing (`pytest -m "not slow" -q` green).

**Exit criteria:**
- `refinement.py` is replaced by five or more `RefinementStrategy` modules each under 600 lines
- All root-level shim files removed
- All phase communication uses typed `PhaseContract` dataclasses
- All Cypher strings are in `repository/` or `schema/` modules, not in phase logic
- `pytest -m "unit or contract" -q` green with no regressions

**Duration:** 6–10 weeks

### Phase B: DAG Orchestration

**Objective:** Replace the linear phase sequence with a dependency-driven DAG, enable parallel SRL execution, and introduce bounded iterative refinement.

**Entry criteria:** Phase A exit criteria met.

**Exit criteria:**
- `DagOrchestrator` replacing linear `PipelineOrchestrator` for new runs
- PropBank and NomBank SRL tasks run in parallel within Ingestion DAG
- Temporal and Event Enrichment phases execute in the correct dependency order (enrichment informs temporal normalization on a second pass)
- Checkpoint granularity: per-document per-phase
- End-to-end MEANTIME evaluation scores equal to or better than pre-transformation baseline

**Duration:** 8–12 weeks

### Phase C: Discourse & Situational Awareness Engine

**Objective:** Add the missing linguistic layers in the three-horizon order defined in `docs/research/2026-05-02-discourse-and-large-context-rnd.md`.

**Entry criteria:** Phase B exit criteria met.

**Exit criteria (Horizon 1):**
- Explicit discourse connective extraction producing typed `DiscourseRelation` edges
- Within-document event coreference producing `EVENT_COREF` cluster nodes
- PDTB explicit sense taxonomy applied to `DiscourseRelation` nodes

**Exit criteria (Horizon 2):**
- Document-level relation extraction (DocRED-style) complementing sentence-level SRL
- Cross-document event linking for `TEvent` nodes parallel to existing entity `SAME_AS`

**Exit criteria (Horizon 3):**
- EDU segmentation and RST rhetorical tree represented in graph
- Scenario template matching binding `TEvent` clusters to high-level `Scenario` nodes

**Duration:** 4–8 months (iterative, horizon by horizon)

---

## 6. Target Architecture: Annotated Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      DagOrchestrator                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                   DAG Task Graph                       │  │
│  │                                                        │  │
│  │  [IngestionTask]──┬──[PropBankSRLTask] (parallel)      │  │
│  │                   └──[NomBankSRLTask]  (parallel)      │  │
│  │                        │                               │  │
│  │                   [CoreferenceTask]                    │  │
│  │                        │                               │  │
│  │              ┌─────────┴──────────┐                    │  │
│  │   [EventEnrichmentTask]    [TemporalExtractionTask]     │  │
│  │              │                    │                    │  │
│  │              └──────────┬─────────┘                    │  │
│  │               [TemporalNormalizationTask] (pass 2)      │  │
│  │                         │                               │  │
│  │              [RefinementStrategyTasks] ──┐              │  │
│  │              │  HeadAssignment           │              │  │
│  │              │  EntityLinking            │ bounded loop │  │
│  │              │  MentionNormalization      │ max=2        │  │
│  │              └───────────────────────────┘              │  │
│  │                         │                               │  │
│  │                [TLinkRecognitionTask]                   │  │
│  │                         │                               │  │
│  │            [DiscourseRelationTask] (Phase C)            │  │
│  │                         │                               │  │
│  │            [EventCoreferenceTask]  (Phase C)            │  │
│  │                         │                               │  │
│  │            [ScenarioTemplateTask]  (Phase C H3)         │  │
│  └────────────────────────────────────────────────────────┘  │
│                             │                                 │
│              ┌──────────────▼──────────────┐                 │
│              │   IntermediateStateStore     │                 │
│              │  (in-memory graph diff buffer│                 │
│              │   committed atomically to    │                 │
│              │   Neo4j on DAG completion)   │                 │
│              └──────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    Neo4j LPG    │
                    │  (canonical KG) │
                    └─────────────────┘
```

**Key design principles encoded in this diagram:**

- PropBank and NomBank SRL tasks run in **parallel** (no dependency between them).
- `EventEnrichmentTask` and `TemporalExtractionTask` run in parallel on the first pass, then a second `TemporalNormalizationTask` runs after enrichment completes (feedback loop).
- `RefinementStrategyTasks` execute as a bounded loop (maximum 2 iterations) to allow convergence.
- All tasks write to an `IntermediateStateStore` (in-memory or Redis-backed). The final commit to Neo4j is atomic. This enables dry-run validation and rollback on failure.
- Phase C tasks (`DiscourseRelationTask`, `EventCoreferenceTask`, `ScenarioTemplateTask`) are additions, not replacements — they layer on top of the existing pipeline output.

---

## 7. Detailed Phase Design

### 7.1 Ingestion Layer

**Current location:** `src/textgraphx/pipeline/ingestion/graph_based_nlp.py`

**Problem:** `GraphBasedNLP` is a subclass of `GraphDBBase` and carries Neo4j connection management, spaCy model loading, document import orchestration, entity processing, SRL calls, and coreference — all in one class. This violates separation of concerns.

**Target design:**

```
pipeline/ingestion/
├── document_loader.py        # MeantimeXMLImporter, NAF text normalization
├── nlp_processor.py          # spaCy model loading, tokenization, sentence splitting
├── srl_processor.py          # PropBank SRL caller (async)
├── nom_srl_processor.py      # NomBank SRL caller (async)
├── entity_processor.py       # NER, entity fusion, entity disambiguation
├── coref_processor.py        # spacy-experimental-coref, cluster builder
├── graph_writer.py           # All Cypher MERGE/CREATE for ingestion output
└── contracts.py              # IngestionInput, IngestionOutput PhaseContract types
```

**Contract specification:**

```python
@dataclass
class IngestionOutput:
    doc_id: str
    annotated_text_id: int          # deterministic hash
    sentence_count: int
    token_count: int
    entity_mentions: List[EntityMentionRecord]
    frame_records: List[FrameRecord]  # PropBank + NomBank
    coref_clusters: List[CorefClusterRecord]
    timex_candidates: List[TimexRecord]   # pre-normalization
    completion_marker: str              # written to graph
```

The `IngestionOutput` becomes the typed input to `RefinementStrategyTasks` and `EventEnrichmentTask`. No phase reads directly from Neo4j to discover what Ingestion produced.

### 7.2 Refinement Decomposition

**Current location:** `src/textgraphx/pipeline/phases/refinement.py` (3,000+ lines)

The existing `RULE_FAMILIES` dictionary already classifies the methods into logical groups:

| Rule Family | Methods | New Module |
|-------------|---------|------------|
| `head_assignment` | 16 methods | `refinement/head_assignment.py` |
| `linking` | 12+ methods | `refinement/frame_entity_linker.py` |
| `canonicalization` | entity type, numeric promotion | `refinement/entity_canonicalizer.py` |
| `coreference_propagation` | antecedent/CorefMention chains | `refinement/coref_propagator.py` |
| `srl_argument_normalization` | C-/R-/PRD prefix handling | `refinement/srl_normalizer.py` |

Each module implements the `RefinementStrategy` interface:

```python
class RefinementStrategy(Protocol):
    def run(self, input: RefinementInput) -> RefinementResult:
        """Execute idempotent refinement rules; return structured diff."""
        ...
```

The `RefinementPhase` orchestrator (`refinement/__init__.py`) iterates strategies, aggregates `RefinementResult` objects, and applies them in a single batched write. This removes the current pattern of each strategy firing individual Cypher queries directly against the live graph.

### 7.3 Temporal Extraction

**Current location:** `src/textgraphx/pipeline/phases/temporal.py`

**Existing strengths:** `TemporalPhase.materialize_signals()` correctly creates `Signal` and `CSignal` nodes with span properties. TIMEX normalization via Heideltime and TTK is functioning.

**Gaps to address:**

1. **Anchoring TIMEX to events by class.** A `TIMEX3 TYPE="DURATION"` that describes a PERFECTIVE event (completed action) should anchor to the event's start/end differently than one describing a PROGRESSIVE event. The current anchoring logic does not condition on `TEvent.aspect`.
2. **Second-pass normalization.** After `EventEnrichmentTask` assigns class and aspect to `TEvent` nodes, a second `TemporalNormalizationPass` should re-evaluate ambiguous TIMEX anchors.
3. **Signal coverage.** The existing signal detection fires on Heideltime/TTK output only. Explicit PDTB temporal connectives (`before`, `after`, `when`, `while`) should also trigger signal nodes in the DAG Horizon 1 pass.

### 7.4 Event Enrichment

**Current location:** `src/textgraphx/pipeline/phases/event_enrichment.py`

**Existing strengths:** `EventMention` nodes are correctly created and linked to canonical `TEvent` via `REFERS_TO`. Frame-to-EventMention linking via `INSTANTIATES` is in place.

**Gaps to address:**

1. **Within-document event coreference.** Two distinct `EventMention` nodes that refer to the same real-world event (e.g., `"the explosion"` and `"the blast"`) are not currently detected. This requires a dedicated `EventCoreferenceTask` (Phase C, Horizon 1) that scores `EventMention` pairs on: predicate lemma similarity, shared participants, temporal proximity, and head-noun overlap.
2. **Factuality and attribution.** The `certainty` and `polarity` properties on `EventMention` exist but are populated by scalar rules. They should be backed by an `AttributedClaim` node when the event is introduced by an attribution verb (`said`, `reported`, `confirmed`).

### 7.5 TLINK Recognition

**Current location:** `src/textgraphx/pipeline/phases/tlinks_recognizer.py`

**Existing strengths:** Rule-based TLINK heuristics cover the most common syntactic patterns. `CLINK` and `SLINK` are both implemented and tested.

**Critical problem:** TLINK recognition runs before event coreference is complete (because event coreference requires a Phase C component that does not yet exist). Until event coreference is resolved, TLINKs written between non-coreferential `TEvent` nodes may produce conflicting or redundant temporal chains.

**Target behavior:** In the DAG orchestrator, `TLinkRecognitionTask` should take an explicit dependency on `EventCoreferenceTask`. Until Phase C delivers event coreference, TLINK recognition should write a flag (`provisional=true`) on any TLINK that spans an `EventMention` pair that has not been coreference-checked.

### 7.6 Discourse Engine (New — Phase C)

This is the largest new capability block. It is layered above the existing pipeline, not woven into it. Its inputs are the outputs of TLINK recognition; its outputs are new node/edge types added to the existing graph.

#### 7.6.1 Explicit Discourse Connective Extraction (Horizon 1)

**Implementation:** T1 (deterministic rule, Tier 1 methodology).

A lexical lookup over `TagOccurrence` tokens identifies PDTB-style explicit connectives:

| Sense Class | Example Connectives |
|-------------|---------------------|
| Causal | because, since, as, due to, given that |
| Contrastive | although, however, but, whereas, while |
| Conditional | if, unless, provided that, only if |
| Temporal | before, after, when, while, once, until |
| Elaborative | specifically, in particular, for example |
| Result | therefore, thus, consequently, as a result |

Each detected connective creates a `DiscourseSignal` node (subtype of `Signal`) with:
- `connective_text`, `start_tok`, `end_tok`, `doc_id` (span-grounded)
- `pdtb_sense` (from the taxonomy above)
- `arg1_span`, `arg2_span` (the two text arguments bridged by the connective)

A `DISCOURSE_LINK` edge is written between the `TEvent` or `Sentence` nodes identified as Arg1 and Arg2:

```
(:TEvent {id: "e1"})-[:DISCOURSE_LINK {
    sense: "Causal.Reason",
    connective: "because",
    direction: "Arg1->Arg2",
    source: "pdtb_explicit_extractor_v1",
    confidence: 1.0
}]->(:TEvent {id: "e2"})
```

#### 7.6.2 Implicit Discourse Relation Classification (Horizon 2)

**Implementation:** T2 (specialized ML, Tier 2 methodology).

Sentence pairs that do not share an explicit connective are passed through a fine-tuned classifier (e.g., RoBERTa fine-tuned on PDTB3 implicit relations). The classifier outputs a sense from the PDTB3 level-2 taxonomy and a confidence score. Relations below `config.discourse.implicit_min_confidence` (default 0.60) are not written to avoid polluting the graph with low-quality edges.

The `DISCOURSE_LINK` edge receives `implicit=true` and `confidence=<model_score>` to differentiate from explicit (deterministic) relations.

#### 7.6.3 Within-Document Event Coreference (Horizon 1)

**Implementation:** T1 + T2 hybrid.

An `EventCoreferenceTask` scores all pairs of `EventMention` nodes within a document using a feature vector:

| Feature | Weight rationale |
|---------|-----------------|
| Head lemma equality | Strong lexical identity signal |
| Predicate frame equality (`attack.01` == `attack.01`) | Strong semantic identity signal |
| Participant overlap (shared `ARG0`/`ARG1` entities) | Strong situational identity signal |
| Temporal window (`start_tok` distance ≤ N) | Reduces false positives across distant mentions |
| Aspect compatibility (PERFECTIVE + PERFECTIVE > PROGRESSIVE + PERFECTIVE) | Grammatical consistency check |

Pairs above a threshold form coreference clusters. A `EventCoreferenceCluster` node is created for each cluster, and `EventMention` nodes are linked to it via `MEMBER_OF_CLUSTER`. The cluster's canonical representative is the `EventMention` with the highest confidence Frame link.

```
(:EventMention)-[:MEMBER_OF_CLUSTER {rank: 1}]->(:EventCoreferenceCluster)
(:EventMention)-[:MEMBER_OF_CLUSTER {rank: 2}]->(:EventCoreferenceCluster)
```

#### 7.6.4 RST Rhetorical Tree (Horizon 3)

**Implementation:** T2 (specialized ML — RST parser such as `rstdt` or `isanlp_rst`).

Documents are segmented into Elementary Discourse Units (EDUs) — clause-like text spans that are the atoms of RST analysis. Each EDU becomes a `DiscourseUnit` node with span properties. The RST parser assigns nucleus/satellite roles and rhetorical relation labels (Elaboration, Contrast, Cause, Condition, etc.) between adjacent EDUs.

The graph representation:

```
(:DiscourseUnit {id: "edu_1", text: "...", start_tok: 0, end_tok: 5})
  -[:RST_RELATION {label: "Elaboration", nucleus: true}]->
(:DiscourseUnit {id: "edu_2", text: "...", start_tok: 6, end_tok: 12})
```

`DiscourseUnit` nodes are linked to their containing `Sentence` and their constituent `TagOccurrence` nodes via `SPANS` edges. `TEvent` nodes within an EDU are linked to that EDU via `OCCURS_IN_EDU`.

This enables queries such as: *"Which events occur in satellite clauses (peripheral information) versus nucleus clauses (main content)?"* — directly informing event salience scoring for downstream GraphRAG applications.

#### 7.6.5 Scenario Template Matching (Horizon 3)

**Implementation:** T1 + T3 hybrid (rule templates + optional LLM disambiguation).

A `ScenarioRegistry` holds typed scenario templates. Each template specifies:
- A set of required event classes and participant role patterns (e.g., `AttackScenario` requires: an OCCURRENCE event with ARG0=AGENT, ARG1=PATIENT, a TIMEX anchor, a LOCATION participant)
- An optional RST structural expectation (e.g., the aftermath events appear in satellite clauses)

The `ScenarioTemplateTask` matches the document's `TEvent` cluster against registered templates. A match creates a `Scenario` node linked to the matching `TEvent` nodes:

```
(:Scenario {type: "AttackScenario", confidence: 0.87, doc_id: "..."})
  -[:CONTAINS_EVENT {role: "perpetration_event"}]->(:TEvent)
  -[:CONTAINS_EVENT {role: "victim_event"}]->(:TEvent)
  -[:CONTAINS_EVENT {role: "aftermath_event"}]->(:TEvent)
```

This layer directly enables **Endsley Level 3 projection**: given a detected `AttackScenario` with phases 1 and 2 populated, the system can project that an `aftermath_event` is expected and flag its absence or presence.

### 7.7 Reasoning & Fusion Layer

**Current location:** `src/textgraphx/reasoning/fusion.py`

**Current capabilities:** `CO_OCCURS_WITH` (cross-sentence entity co-occurrence) and `SAME_AS` (cross-document entity linking via `kb_id`).

**Additions required:**

1. `fuse_events_cross_document()` — mirrors the entity fusion function; links `TEvent` nodes sharing predicate lemma, participant identity (`SAME_AS` entities), and compatible temporal expressions across documents.
2. `detect_contradictions()` — identifies pairs of `TEvent` nodes where the same event is asserted with opposite polarity (`POS` vs `NEG`) or incompatible TLINK ordering (A before B, but also B before A).
3. `score_salience()` — assigns a `salience` score to `TEvent` nodes based on RST nucleus status, number of `DISCOURSE_LINK` edges, coreference cluster size, and participant count.

---

## 8. DAG Orchestrator Design

### 8.1 Core Abstractions

```python
@dataclass
class ExtractionTask:
    """A single unit of work in the DAG."""
    task_id: str                          # deterministic, based on phase name + doc_id
    phase: str                            # e.g. "propbank_srl"
    depends_on: List[str]                 # task_ids of prerequisite tasks
    contract_in: Type[PhaseContract]      # expected input type
    contract_out: Type[PhaseContract]     # declared output type
    max_retries: int = 1
    is_cyclic_member: bool = False        # True if part of a bounded iteration group
    cycle_group_id: Optional[str] = None  # groups tasks that may repeat together

@dataclass
class PhaseContract:
    """Base class for all typed inter-phase contracts."""
    doc_id: str
    run_id: str
    phase: str
    timestamp: datetime
    completion_marker: str    # written to graph on success
```

### 8.2 Graph Mutation Buffer

Instead of phases writing directly to Neo4j, each task produces a `GraphMutationBatch`:

```python
@dataclass
class GraphMutation:
    operation: Literal["MERGE_NODE", "MERGE_EDGE", "SET_PROPERTY", "DELETE"]
    label: str
    key_props: Dict[str, Any]    # used for MERGE identity
    set_props: Dict[str, Any]    # additional properties to set
    source: str                  # provenance: which task generated this
    run_id: str

@dataclass
class GraphMutationBatch:
    doc_id: str
    task_id: str
    mutations: List[GraphMutation]
```

The `DagOrchestrator` accumulates `GraphMutationBatch` objects from all completed tasks and applies them in a single transaction per document on DAG completion. This provides:

- **Atomicity:** Either all mutations for a document succeed or none do.
- **Dry-run support:** The mutation batch can be inspected without executing it.
- **Rollback:** On DAG failure, uncommitted batches are discarded; the graph remains at the last committed checkpoint.
- **Audit trail:** The mutation log is persisted alongside the checkpoint for forensic analysis.

### 8.3 Parallel SRL Execution

```python
# DAG fragment: parallel SRL tasks
ingestion_task = ExtractionTask(
    task_id=f"ingestion::{doc_id}",
    phase="ingestion",
    depends_on=[]
)

propbank_task = ExtractionTask(
    task_id=f"propbank_srl::{doc_id}",
    phase="propbank_srl",
    depends_on=[f"ingestion::{doc_id}"]  # only needs tokens
)

nombank_task = ExtractionTask(
    task_id=f"nombank_srl::{doc_id}",
    phase="nombank_srl",
    depends_on=[f"ingestion::{doc_id}"]  # independent of PropBank
)

coref_task = ExtractionTask(
    task_id=f"coref::{doc_id}",
    phase="coreference",
    depends_on=[f"propbank_srl::{doc_id}", f"nombank_srl::{doc_id}"]
    # coref benefits from knowing which spans are frame arguments
)
```

The executor (a thread pool or `asyncio` event loop) inspects each task's `depends_on` list and schedules tasks as soon as their dependencies complete. PropBank and NomBank SRL tasks execute concurrently against their respective services (ports 8010 and 8011).

### 8.4 Bounded Iterative Refinement

```python
# Bounded cycle: EventEnrichment → TemporalNormalization (max 2 iterations)
event_enrichment_v1 = ExtractionTask(
    task_id=f"event_enrichment_v1::{doc_id}",
    phase="event_enrichment",
    depends_on=[f"coref::{doc_id}"],
    is_cyclic_member=True,
    cycle_group_id=f"enrich_temporal_loop::{doc_id}"
)

temporal_normalization_v1 = ExtractionTask(
    task_id=f"temporal_normalization_v1::{doc_id}",
    phase="temporal_normalization",
    depends_on=[f"event_enrichment_v1::{doc_id}"],
    is_cyclic_member=True,
    cycle_group_id=f"enrich_temporal_loop::{doc_id}"
)
```

The `DagOrchestrator` detects cycle groups and enforces the `max_cycles` bound. After iteration 2, it proceeds downstream regardless of whether the loop has fully converged, flagging non-converged nodes with `converged=false` for human review.

### 8.5 Checkpoint Granularity

```
checkpoints/
└── run_<run_id>/
    └── doc_<doc_id>/
        ├── ingestion.complete
        ├── propbank_srl.complete
        ├── nombank_srl.complete
        ├── coref.complete
        ├── event_enrichment_v1.complete
        ├── temporal_normalization_v1.complete
        ├── refinement.complete
        ├── tlinks.complete
        └── mutations.jsonl    # the accumulated graph mutation log
```

On restart, the orchestrator reads existing `.complete` markers and skips those tasks, resuming only incomplete tasks within each document. This reduces re-processing to the failed task and its dependents.

---

## 9. Schema Evolution Plan

### 9.1 Immediate Actions (Phase A)

1. **Set a deadline for dual-edge elimination.** The legacy `DESCRIBES` and `PARTICIPANT` edges must be removed no later than the Phase A exit gate. Migration `0016_remove_legacy_describes.cypher` and `0017_remove_legacy_participant.cypher` must be written and scheduled.
2. **Add `rule_id` to all inferred edges.** `CO_OCCURS_WITH`, `SAME_AS`, and any other edges written by fusion methods must carry `rule_id` to complete the provenance lineage.
3. **Define `PhaseContract` node types in the schema.** Each `ExtractionTask`'s `completion_marker` should be a typed `CompletionMarker` node with `run_id`, `phase`, `doc_id`, `timestamp`, and `mutation_count` properties — not just a property on `AnnotatedText`.

### 9.2 Phase C New Node/Edge Types

| Type | Label | Key Properties | Migration |
|------|-------|---------------|-----------|
| Elementary Discourse Unit | `DiscourseUnit` | `doc_id`, `edu_id`, `start_tok`, `end_tok`, `text` | `0018_introduce_discourse_unit.cypher` |
| Discourse Relation (explicit) | `DISCOURSE_LINK` | `sense`, `connective`, `direction`, `source`, `confidence` | `0019_introduce_discourse_link.cypher` |
| Discourse Relation (implicit) | `DISCOURSE_LINK` | `implicit=true`, `sense`, `confidence`, `model_version` | same migration |
| Event Coreference Cluster | `EventCoreferenceCluster` | `doc_id`, `cluster_id`, `canonical_member_id`, `size` | `0020_introduce_event_coref_cluster.cypher` |
| Scenario | `Scenario` | `doc_id`, `type`, `confidence`, `template_version` | `0021_introduce_scenario.cypher` |
| Attributed Claim | `AttributedClaim` | `doc_id`, `speaker_entity_id`, `proposition_event_id`, `certainty`, `source` | `0022_introduce_attributed_claim.cypher` |

All new migrations follow the existing migration convention: idempotent Cypher with `CREATE CONSTRAINT IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements before any data writes.

### 9.3 Ontology Update Protocol

For each new node/edge type above:
1. Add the entry to `schema/ontology.json` under the appropriate section.
2. Update `docs/ontology.yaml` with the human-readable description.
3. Update `docs/schema.md` Section 4 (canonical labels) and Section 5 (relationships).
4. Link the new schema page from `DOCUMENTATION.md` and `docs/README.md`.

---

## 10. Testing & Evaluation Strategy

### 10.1 Contract Tests for Each RefinementStrategy

Each new `RefinementStrategy` module requires a `test_<strategy_name>_contract.py` file that:
- Instantiates the strategy with a mock graph (no live Neo4j)
- Feeds it a fixed `RefinementInput` fixture
- Asserts the shape and properties of the returned `RefinementResult`
- Verifies idempotency: running the strategy twice produces the same `RefinementResult`

### 10.2 DAG Orchestrator Tests

```python
@pytest.mark.unit
def test_dag_parallel_srl_tasks_have_no_shared_dependency():
    """PropBank and NomBank tasks must both depend only on ingestion."""
    dag = build_document_dag(doc_id="test_doc")
    propbank = dag.get_task("propbank_srl::test_doc")
    nombank = dag.get_task("nombank_srl::test_doc")
    assert propbank.depends_on == ["ingestion::test_doc"]
    assert nombank.depends_on == ["ingestion::test_doc"]
    assert "nombank_srl::test_doc" not in propbank.depends_on
    assert "propbank_srl::test_doc" not in nombank.depends_on

@pytest.mark.unit
def test_bounded_cycle_enforced():
    """Iterative refinement loop must not exceed max_cycles."""
    orchestrator = DagOrchestrator(max_cycles=2)
    result = orchestrator.run_cycle_group("enrich_temporal_loop::test_doc")
    assert result.iterations_executed <= 2
```

### 10.3 Discourse Layer Tests

For each new Horizon 1 component:

```python
@pytest.mark.unit
def test_explicit_causal_connective_detected():
    """'because' triggers a Causal.Reason DISCOURSE_LINK."""
    task = DiscourseConnectiveTask()
    output = task.run(IngestionOutput(
        doc_id="test",
        tokens=[...],  # fixture: "X happened because Y occurred"
        ...
    ))
    assert any(
        m.operation == "MERGE_EDGE"
        and m.label == "DISCOURSE_LINK"
        and m.set_props.get("sense") == "Causal.Reason"
        for m in output.mutations
    )
```

### 10.4 MEANTIME Regression Baseline

Before executing any Phase A change, run the full MEANTIME evaluation harness and save the baseline:

```bash
pytest src/textgraphx/tests -m "regression" -q \
  --baseline-save src/textgraphx/datastore/evaluation/baseline/pre_phase_a.json
```

After each phase, run the comparison:

```bash
pytest src/textgraphx/tests -m "regression" -q \
  --baseline-compare src/textgraphx/datastore/evaluation/baseline/pre_phase_a.json
```

A regression gate prevents merge if any M1–M8 score drops by more than 2 percentage points without an explicit override signed by the architecture owner.

---

## 11. Architecture Governance Rules

These rules are binding for all new code in this repository. They are the minimum set required to prevent the current architectural debt from re-accumulating.

### Rule G1: Zero Raw Cypher in Phase Logic

All Cypher strings must be declared in `src/textgraphx/database/repository/` or `src/textgraphx/schema/` modules. Phase logic calls repository methods by name; it does not construct Cypher strings. No exceptions.

**Enforcement:** A `ruff` or `grep` pre-commit hook that flags `MATCH`, `MERGE`, `CREATE`, or `RETURN` strings appearing in files under `pipeline/phases/` or `pipeline/ingestion/`.

### Rule G2: Every Edge Carries Full Provenance

Every edge written to Neo4j — including inferred edges from fusion, discourse, and coreference — must carry:
- `source`: the module or service that created it (string)
- `confidence`: a float in `[0.0, 1.0]`
- `rule_id`: a stable string identifier for the rule or model version that produced it
- `run_id`: the execution ID of the orchestrator run

**Enforcement:** A contract test in `tests/contract/test_edge_provenance.py` that runs a Cypher query for edges missing any of these properties.

### Rule G3: No Phase Reads Another Phase's Output Directly From Neo4j

Phases communicate through `PhaseContract` dataclass objects passed by the `DagOrchestrator`. If a phase needs data from a previous phase, that data must be declared in the contract type. Reading neo4j "to check what a previous phase did" is forbidden.

**Enforcement:** Code review; flagged by architecture owner during PR review.

### Rule G4: Root Shims Must Not Be Added

The root-level shim files (`GraphBasedNLP.py`, etc.) are scheduled for deletion in Phase A. No new root-level shims may be created. All new modules are created under `src/textgraphx/`.

### Rule G5: Every New Node Label Has a Migration

No node label may be written by a phase unless a corresponding `CREATE CONSTRAINT IF NOT EXISTS` statement exists in an applied migration file. New phases that create node labels must include their migration in the same PR.

### Rule G6: LLM Calls Require a Signed Justification

Any new code path that invokes an LLM (T3 tier) must include a code comment block:

```python
# T3-JUSTIFICATION:
# Task: <what this LLM call does>
# T1 coverage: <why deterministic rules are insufficient>
# T2 coverage: <why specialized ML is insufficient>
# Fallback: <what the system does when the LLM is unavailable>
```

### Rule G7: Scenario Templates Are Versioned

`ScenarioRegistry` entries carry a `template_version` string. When a template changes, its version is incremented. All `Scenario` nodes in the graph carry the `template_version` under which they were created. This enables selective re-matching when templates are updated without full re-ingestion.

---

## 12. Implementation Sequencing & Milestones

### Phase A: Contract-Driven Decomposition

| Step | Action | Owner Area | Exit Check |
|------|--------|-----------|------------|
| A1 | Audit `refinement.py` RULE_FAMILIES and map each to a target module | Architecture | Module list agreed |
| A2 | Define `PhaseContract` base classes and all concrete subtypes | Core | Type stubs pass mypy |
| A3 | Extract `HeadAssignmentStrategy` from refinement | Ingestion/Refine | Unit tests green |
| A4 | Extract `FrameEntityLinker` | Ingestion/Refine | Unit tests green |
| A5 | Extract `EntityCanonicalizer` | Ingestion/Refine | Unit tests green |
| A6 | Extract `CorefPropagator` | Ingestion/Refine | Unit tests green |
| A7 | Extract `SrlNormalizer` | Ingestion/Refine | Unit tests green |
| A8 | Move all Cypher to `repository/` | Database | G1 hook passes |
| A9 | Write `test_edge_provenance.py` contract test | Testing | G2 enforced |
| A10 | Delete root shims | Cleanup | Import graph clean |
| A11 | Write `0016_remove_legacy_describes.cypher` and apply | Schema | Legacy edges zero |
| A12 | Run MEANTIME baseline; save `pre_phase_a.json` | Evaluation | Baseline recorded |

### Phase B: DAG Orchestration

| Step | Action | Owner Area | Exit Check |
|------|--------|-----------|------------|
| B1 | Define `ExtractionTask` and `GraphMutationBatch` types | Orchestration | Types pass mypy |
| B2 | Implement `DagOrchestrator` with topological sort | Orchestration | Unit tests green |
| B3 | Wire PropBank and NomBank SRL as parallel tasks | Ingestion | Integration test: both fire |
| B4 | Implement `GraphMutationBatch` accumulator and atomic commit | Database | Atomicity test green |
| B5 | Implement per-document per-phase checkpointing | Orchestration | Resume-on-failure test green |
| B6 | Implement bounded cycle group (`max_cycles=2`) | Orchestration | Cycle bound test green |
| B7 | Re-order: EventEnrichment before TemporalNormalization | Pipeline | MEANTIME scores ≥ baseline |
| B8 | Dry-run mode: log mutations without committing | Orchestration | Dry-run test green |

### Phase C: Discourse Engine (Horizon 1)

| Step | Action | Owner Area | Exit Check |
|------|--------|-----------|------------|
| C1 | Implement explicit connective detector (T1 rule, PDTB sense map) | Discourse | Unit test: "because" → Causal.Reason |
| C2 | Write `0018_introduce_discourse_unit.cypher`, `0019_introduce_discourse_link.cypher` | Schema | Constraints created |
| C3 | Implement `EventCoreferenceTask` (feature vector scorer) | Discourse | Within-doc event coref test |
| C4 | Write `0020_introduce_event_coref_cluster.cypher` | Schema | Constraints created |
| C5 | Harden attribution modeling: `AttributedClaim` nodes for attribution verbs | Discourse | Attribution extraction test |
| C6 | Write `0022_introduce_attributed_claim.cypher` | Schema | Constraints created |
| C7 | Run MEANTIME evaluation; compare to pre_phase_a baseline | Evaluation | Scores ≥ baseline on all M1–M8 |

---

## 13. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Phase A breaks integration tests that depend on `RefinementPhase` class name | High | Medium | Write adapter shim *inside* the new module structure for the duration of Phase A; delete at Phase A exit |
| Parallel SRL tasks cause Neo4j write contention if mutation buffer is not used | Medium | High | Do not implement parallel SRL until `GraphMutationBatch` (Step B4) is in place |
| MEANTIME scores drop during Phase B re-ordering (temporal before vs. after enrichment) | Medium | High | Run MEANTIME evaluation after every B-step; rollback re-ordering if scores drop >2pp |
| Discourse connective detector fires on negated connectives (e.g., "not because") | Medium | Medium | Add negation detection to the T1 rule; flag `negated=true` on `DISCOURSE_LINK` edge |
| RST parser latency makes Phase C Horizon 3 impractical at scale | Medium | Low | Scope RST to a separate asynchronous enrichment service; make it opt-in via config flag |
| Schema migration drift: new node labels written before migration is applied | Low | High | Enforce G5 via CI check: phase code may not reference labels not present in applied migrations |
| Bounded cycle does not converge within 2 iterations for complex documents | Low | Low | Flag non-converged nodes with `converged=false`; monitor proportion in evaluation reports |

---

*End of document. Next review scheduled after Phase A exit gate is confirmed.*