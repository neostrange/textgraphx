# TextGraphX Schema Evolution Plan

This document is the implementation plan for hardening the current TextGraphX graph schema into a more stable, explicit, and migration-governed semantic model.

It is based on:

- the implemented schema documented in [schema.md](./schema.md)
- the current pipeline architecture documented in [architecture-overview.md](./architecture-overview.md)
- the stated system goals in [README.md](../README.md): event-centric knowledge graphs, temporal reasoning, entity normalization, explainable text grounding, and downstream analytical querying

This plan assumes the project should keep its current property-graph architecture and improve it incrementally, rather than replacing it with a completely new ontology or external triple-store model.

## 1. Why This Plan Exists

The current schema already has the right conceptual backbone:

- document-grounded token graph
- mention-to-entity normalization
- SRL frame and frame-argument layer
- event and temporal abstraction
- relation and fusion enrichment
- audit and validation support

The main issue is not conceptual weakness. It is schema drift and schema ambiguity:

- identity is not fully normalized across phases
- some predicates are overloaded for unrelated semantics
- some labels are dynamic or legacy but not clearly classified
- temporal writes use inconsistent property shapes and typing
- constraint enforcement is split between bootstrap code and migrations
- some downstream reasoning code expects schema properties that upstream code does not write

If the project’s goal is robust knowledge representation and reasoning, then the next step is schema hardening, not schema expansion.

## 2. Design Goals

The evolved schema should optimize for the project’s stated objectives.

### 2.1 Primary goals

1. Preserve document-grounded explainability.
2. Improve event and temporal reasoning reliability.
3. Strengthen mention, entity, and cross-document identity resolution.
4. Make the graph safer for downstream analytics, evaluation, and inspection.
5. Reduce ambiguity for maintainers and future contributors.
6. Keep iterative research and experimentation possible without destabilizing the core schema.

### 2.2 Industry-aligned modeling principles

These principles are appropriate for semantic modeling in a Neo4j-style property graph:

1. Stable identities must be explicit and deterministic.
2. Coarse semantic classes belong in labels; fine semantic distinctions should prefer governed properties or controlled vocabularies.
3. One relationship type should represent one primary semantic role wherever practical.
4. Canonical schema must be distinguished from optional enrichment and legacy paths.
5. Schema rules must be migration-governed and testable, not only implied by code.
6. Changes must preserve provenance and recoverability from the source text.

## 3. Target Outcome

At the end of this plan, TextGraphX should have:

- a canonical maintained schema layer
- an explicitly documented optional enrichment layer
- a clearly identified legacy layer
- deterministic identity policies for core semantic objects
- one authoritative migration path for constraints and schema evolution
- schema-level regression coverage
- compatibility strategy for existing data and queries

The project should still feel like the same system, but with a much stronger operational and semantic contract.

## 4. Scope Classification

Before changing anything, the schema should be classified into three tiers.

### 4.1 Tier 1: canonical maintained schema

These are the objects and relations that should be treated as the stable semantic core.

Node labels:

- `AnnotatedText`
- `Sentence`
- `TagOccurrence`
- `NamedEntity`
- `Entity`
- `Frame`
- `FrameArgument`
- `Antecedent`
- `CorefMention`
- `TIMEX`
- `TEvent`

Relationship types:

- `CONTAINS_SENTENCE`
- `HAS_TOKEN`
- `HAS_NEXT`
- `IS_DEPENDENT`
- `PARTICIPATES_IN`
- `REFERS_TO`
- `PARTICIPANT`
- `TRIGGERS`
- `DESCRIBES`
- `CREATED_ON`
- `TLINK`
- `COREF`

### 4.2 Tier 2: optional maintained enrichment

These should be supported, but not required for every run.

Node labels:

- `PhaseRun`
- `RefinementRun`

Relationship types:

- `CO_OCCURS_WITH`
- `SAME_AS`

### 4.3 Tier 3: legacy or experimental layer

These should remain available only if explicitly needed, and must not silently define the main semantic contract.

Node labels:

- `Keyword`
- `Evidence`
- `Relationship`

Relationship types:

- `IS_RELATED_TO`
- `SOURCE`
- `DESTINATION`
- `HAS_EVIDENCE`
- `FROM`
- `TO`

## 5. Main Risks and How the Plan Handles Them

### 5.1 Identity migration risk

Problem:

- existing documents may already contain mixed string and integer forms of `doc_id`
- several node classes derive identity from different conventions

Impact if changed naively:

- duplicate semantic objects
- disconnected temporal subgraphs
- broken joins in downstream queries and notebooks

Mitigation:

- additive migration first
- dual-read and dual-write during the transition window
- migration validation queries before destructive cleanup

Fixability:

- high, provided the migration is staged and deterministic

### 5.2 Predicate rename risk

Problem:

- overloaded relationship names are semantically ambiguous

Impact if changed naively:

- query breakage across tests, notebooks, dashboards, and scripts

Mitigation:

- introduce canonical predicates alongside legacy ones
- backfill both representations temporarily
- switch readers first, then writers, then remove legacy edges later

Fixability:

- high

### 5.3 Constraint rollout risk

Problem:

- stricter uniqueness constraints may fail on already-dirty data

Impact if changed naively:

- migration failure in production or shared developer databases

Mitigation:

- preflight duplicate scans
- cleanup scripts before constraint creation
- staged migration rollout with dry-run mode

Fixability:

- high

### 5.4 Legacy feature removal risk

Problem:

- some users may rely on `Keyword`, `Evidence`, `Relationship`, or dynamic labels

Impact if removed too early:

- silent feature loss or broken analytical workflows

Mitigation:

- classify as legacy instead of deleting immediately
- add deprecation notices in docs
- only remove after usage validation and replacement path exist

Fixability:

- high if handled as deprecation, medium if removed abruptly

## 6. Implementation Milestones

### Cross-Milestone TDD Protocol (Mandatory)

All schema work in this plan must follow test-driven development as an execution rule, not as a post-implementation verification step.

Required cycle for every schema task:

1. Write or update a failing test first (unit, regression, integration, or migration).
2. Implement the smallest change needed to make the test pass.
3. Refactor safely while keeping tests green.
4. Add or update diagnostics for observability where the change affects data shape.

Minimum TDD gate per pull request:

1. At least one new failing test was introduced before implementation for each changed schema behavior.
2. The test set includes one happy path and one drift or failure path.
3. Integration coverage exists for any change that affects persisted graph shape.
4. Migration changes include preflight-validation tests.

## Milestone 0: Freeze the Canonical Contract

### Objective

Establish a stable written contract before changing behavior.

### Deliverables

1. Classify schema into canonical, optional, and legacy tiers.
2. Extend [schema.md](./schema.md) with a short canonical-schema section and a deprecation note for legacy features.
3. Align [ontology.yaml](./ontology.yaml) and [../schema/ontology.json](../src/textgraphx/schema/ontology.json) with the canonical tier definitions.
4. Add a schema ownership note in [architecture-overview.md](./architecture-overview.md) stating that migrations define the enforced schema, while `schema.md` defines the maintained semantic contract.

### Acceptance criteria

1. The docs clearly distinguish canonical, optional, and legacy schema features.
2. A maintainer can tell which labels and edges are guaranteed by the maintained pipeline.
3. The machine-readable ontology no longer omits actively maintained schema components such as `PhaseRun` if those remain supported.

### Migration steps

1. No graph data changes.
2. Documentation-only milestone.

### Negative consequences

- This may expose more inconsistency than before.

### Why that is acceptable

- Exposing ambiguity is necessary before safely changing code.

## Milestone 1: Normalize Identity, Document Keys, and Span Coordinates

### Objective

Make document-scoped identity deterministic, type-consistent, and span-compatible across all phases.

### Deliverables

1. Define one canonical document identity policy.
2. Normalize `doc_id` writes in temporal and event-related phases.
3. Add migration support for mixed historical `doc_id` types.
4. Add explicit uniqueness for `TIMEX` natural identity.
5. Introduce a span-coordinate contract for core semantic nodes.

### Proposed design

1. Keep `AnnotatedText.id` as the current operational primary key in the short term.
2. Require that all `doc_id` properties referencing `AnnotatedText.id` use the same type.
3. Introduce one rule: if `AnnotatedText.id` is numeric in storage, all temporal/event `doc_id` values must be numeric too.
4. If the project later adopts `publicId` or `uri` as canonical business id, do that in a separate phase after operational consistency is restored.
5. Adopt a dual-coordinate span standard for span-bearing nodes:
   - token coordinates: `start_tok`, `end_tok`
   - character coordinates: `start_char`, `end_char`
6. Keep legacy span fields during transition, but mark them deprecated in docs and compatibility adapters.

### Code areas

- [TemporalPhase.py](../src/textgraphx/TemporalPhase.py)
- [TlinksRecognizer.py](../src/textgraphx/TlinksRecognizer.py)
- [EventEnrichmentPhase.py](../src/textgraphx/EventEnrichmentPhase.py)
- [text_processing_components/TagOccurrenceCreator.py](../src/textgraphx/text_processing_components/TagOccurrenceCreator.py)
- [text_processing_components/EntityProcessor.py](../src/textgraphx/text_processing_components/EntityProcessor.py)
- [text_processing_components/SRLProcessor.py](../src/textgraphx/text_processing_components/SRLProcessor.py)
- [RefinementPhase.py](../src/textgraphx/RefinementPhase.py)
- any query packs or validation utilities matching `doc_id`

### Acceptance criteria

1. No maintained writer creates both string and integer variants of the same logical `doc_id`.
2. `TIMEX` and `TEvent` nodes for one document are fully joinable across all maintained temporal queries.
3. A migration dry-run can report mixed historical `doc_id` variants before repair.
4. A uniqueness constraint exists for the natural `TIMEX` key, likely `(tid, doc_id)`.
5. All core span-bearing nodes expose the dual coordinate contract (`start_tok`, `end_tok`, `start_char`, `end_char`) either natively or via compatibility mapping.
6. Overlap and containment tests between entity spans and event spans are executable without ad hoc field translation logic.

### Migration steps

1. Add a dry-run diagnostic script or migration query that reports:
   - mixed `doc_id` types on `TIMEX`
   - mixed `doc_id` types on `TEvent`
   - duplicate `(tid, doc_id)` and `(eiid, doc_id)` pairs
2. Add a repair migration that rewrites historical `doc_id` values into canonical type.
3. Add a span preflight report that identifies nodes missing either token or character boundaries.
4. Add backfill migrations for span coordinates where recoverable from existing token anchors.
5. Mark irrecoverable rows with explicit migration flags for manual review.
6. Re-run diagnostics.
7. Only after cleanup, apply uniqueness constraints.

### Negative consequences

- Historical graph snapshots may need data repair.
- Some ad hoc queries expecting string values may need updating.
- Additional storage and query complexity due to dual-coordinate retention during transition.

### Fixability

- high

## Milestone 2: Repair Schema-Code Contradictions

### Objective

Remove the highest-impact inconsistencies that currently cause semantic or operational drift.

### Deliverables

1. Update fusion to use canonical containment edges.
2. Resolve unreachable `ARGM-TMP` non-core mapping logic.
3. Remove or explicitly support `TEvent.modal` assumptions.
4. Audit the remaining write paths for references to stale schema names.

### Code areas

- [fusion.py](../src/textgraphx/fusion.py)
- [EventEnrichmentPhase.py](../src/textgraphx/EventEnrichmentPhase.py)
- [TlinksRecognizer.py](../src/textgraphx/TlinksRecognizer.py)
- any regression and integration tests covering these paths

### Acceptance criteria

1. `fusion.py` queries match the graph produced by the canonical ingestion path.
2. The non-core event-enrichment mapping does not contain unreachable semantic branches.
3. `TlinksRecognizer` does not rely on nonexistent properties unless those properties are explicitly introduced and documented.
4. The schema drift section in [schema.md](./schema.md) shrinks accordingly.

### Migration steps

1. This milestone should be mostly code-level, not graph-data-level.
2. If event argument semantics are corrected, rerun integration tests against a clean graph to confirm expected materialization.

### Negative consequences

- Behavioral differences may surface where old code had been silently failing or under-linking.

### Fixability

- very high

## Milestone 3: Unify Schema Enforcement Under Migrations

### Objective

Move from partially implicit enforcement to a single authoritative schema migration path.

### Deliverables

1. Consolidate constraints and indexes in migration files.
2. Reduce bootstrap-time constraint creation in application code or make it a compatibility fallback only.
3. Add missing constraints and useful indexes for canonical schema objects.

### Suggested migration additions

Constraints:

- `TIMEX(tid, doc_id)` unique
- `PhaseRun(id)` unique
- `RefinementRun(id)` unique
- optionally `Keyword(id)` unique if retained as supported legacy functionality

Indexes:

- `FrameArgument(headTokenIndex)`
- `NamedEntity(headTokenIndex)`
- `TEvent(doc_id)`
- `TIMEX(doc_id)`

### Acceptance criteria

1. A fresh environment created only from migrations gets the same core schema guarantees as a bootstrap-created environment.
2. Constraint coverage for canonical labels is explicit and documented.
3. Migration failures surface duplicate or malformed historical data clearly.

### Migration steps

1. Add migration files for new constraints and indexes.
2. Add a preflight report step before applying stricter uniqueness constraints.
3. Keep bootstrap code temporarily compatible, but mark it as secondary.
4. After a transition period, reduce bootstrap schema creation to connectivity checks or optional setup only.

### Negative consequences

- Developers with older dirty local databases may hit migration errors.

### Fixability

- high with preflight cleanup support

## Milestone 4: Separate Canonical Semantics from Overloaded Predicates

### Objective

Reduce relationship-type overloading without breaking existing consumers abruptly.

This milestone also addresses event-node fragmentation, but uses an alignment-first strategy rather than immediate node merge.

### Candidate changes

1. Split `DESCRIBES` into:
   - canonical `FRAME_DESCRIBES_EVENT`
   - legacy or optional `KEYWORD_DESCRIBES_DOCUMENT`
2. Split `PARTICIPANT` into:
   - canonical `FRAME_ARGUMENT_OF` or `HAS_FRAME_ARGUMENT` for `FrameArgument -> Frame`
   - canonical `EVENT_PARTICIPANT` for `Entity|NUMERIC|FrameArgument -> TEvent`
3. Introduce explicit Frame-to-TEvent alignment semantics for fragmentation control:
   - example edge: `EVENT_ALIGNED_WITH`
   - alignment metadata: `confidence`, `source`, and optional `alignment_rule`
4. Delay hard `Frame` + `TEvent` consolidation until alignment quality thresholds are met.

Note: the exact naming can change, but the semantic split is more important than the literal string.

### Preferred rollout model

1. Introduce new edge types.
2. Update readers to accept both old and new.
3. Backfill canonical edges into existing data.
4. Update writers to emit canonical edges.
5. Deprecate old edge types only after all tests and queries are migrated.
6. Build an event-alignment projection and evaluate whether one-to-one consolidation is semantically safe.

### Acceptance criteria

1. Canonical readers can operate solely on semantically precise predicates.
2. Legacy readers continue to work during the transition window.
3. Documentation clearly marks old edge types as deprecated once canonical replacements exist.
4. Event alignment quality is measured and reported with explicit thresholds before any physical merge strategy is approved.
5. No provenance-critical information from either `Frame` or `TEvent` is lost in the alignment pathway.

### Migration steps

1. Add backfill queries from old edge names to new edge names.
2. Update query packs, tests, and documentation.
3. Run compatibility validation against both old and new graphs during transition.
4. Add backfill for `EVENT_ALIGNED_WITH` where alignment rules match.
5. Keep `Frame` and `TEvent` physically separate in this milestone; treat unified event nodes as an optional later projection.

### Negative consequences

- This is the most disruptive schema change in the plan.
- Every consumer query touching these edges must be reviewed.
- Event alignment errors can introduce false equivalence if thresholds or rules are weak.

### Fixability

- high, but only with staged compatibility

## Milestone 5: Govern Fine-Grained Semantic Categories

### Objective

Treat semantic subtyping as controlled vocabulary rather than ad hoc runtime label growth.

### Deliverables

1. Make `FrameArgument.argumentType` the canonical non-core semantic category field.
2. Define the allowed vocabulary in docs.
3. Keep APOC-added labels optional and derived.
4. Decide whether dynamic labels remain supported for UI and exploration only.
5. Add explicit governance for `NamedEntity` dynamic labels `NUMERIC` and `VALUE`.
6. Define whether `NUMERIC` and `VALUE` remain canonical labels, derived labels, or are mapped to an evaluation projection that mirrors MEANTIME value structures.

### Acceptance criteria

1. The system can answer non-core role queries without relying on dynamic labels.
2. The allowed values for `argumentType` are documented and stable.
3. Tests cover expected mappings from `ARGM-*` to semantic role categories.
4. Policy for `NUMERIC` and `VALUE` is explicitly documented and enforced by tests.
5. If MEANTIME-oriented value projection is enabled, mapping behavior is deterministic and validated.

### Migration steps

1. No destructive graph migration required initially.
2. Update documentation and tests first.
3. If desired later, add a cleanup task to remove stale or unexpected dynamic labels from old graphs.
4. For `NUMERIC` and `VALUE`, introduce policy-specific migrations only after compatibility-readers are in place.

### Negative consequences

- Label-based exploratory queries may need to be rewritten to property-based filters.
- MEANTIME-focused consumers may require explicit projection layers if canonical graph keeps labels as derived convenience.

### Fixability

- high

## Milestone 6: Rationalize the Legacy Relation-Abstraction Layer

### Objective

Decide whether relation reification via `Evidence` and `Relationship` is strategically important.

### Decision point

Choose one of two paths.

#### Option A: keep and formalize it

Do this if relation-level provenance and explainable extracted relations are a real product or research need.

Required changes:

1. Replace `id(r)`-based identities with deterministic ids.
2. Define a canonical reified relation model.
3. Add constraints and tests.
4. Document provenance semantics clearly.

#### Option B: deprecate it

Do this if relation extraction is not a first-class maintained output.

Required changes:

1. Mark the layer as legacy in docs.
2. Remove it from the canonical ontology.
3. Stop implying that it is a stable maintained contract.

### Acceptance criteria

1. The project no longer treats this layer ambiguously.
2. Maintainers know whether to invest in or ignore this subgraph.

### Migration steps

1. If formalizing, introduce deterministic ids and backfill/rebuild.
2. If deprecating, documentation-only first, removal later only after usage review.

### Negative consequences

- Rebuilding relation ids may invalidate historical references.
- Deprecating the layer may disappoint users who rely on it.

### Fixability

- medium to high, depending on how much existing usage exists

## Milestone 7: Add Schema-Level Validation and Regression Coverage

### Objective

Make the schema contract executable and testable.

### Deliverables

1. Schema invariant tests for core labels and relationships.
2. Migration verification tests.
3. Compatibility tests for transition periods.
4. Negative tests proving schema drift is caught early.

### Acceptance criteria

1. CI fails when canonical edge names or key properties drift unintentionally.
2. CI fails when required constraints are missing.
3. CI can validate a migrated graph and a freshly initialized graph.

### Migration steps

1. Add tests before risky schema changes wherever possible.
2. Run compatibility tests during dual-write phases.

### Negative consequences

- More tests means more maintenance work.

### Fixability

- high and worthwhile

## 7. Acceptance Criteria by Workstream

### Identity and temporal consistency

1. All maintained temporal writers use one `doc_id` representation.
2. No duplicate `TIMEX` or `TEvent` identities exist for the same logical key.
3. Migration diagnostics report zero mixed-type `doc_id` violations after repair.

### Semantic clarity

1. Canonical schema documentation clearly separates maintained and legacy graph elements.
2. Overloaded predicates are either documented as transitional or replaced by canonical alternatives.
3. Fine semantic categories are queryable by property, not only by dynamic labels.

### Operational consistency

1. A fresh environment from migrations is semantically equivalent to a bootstrap-created environment for canonical schema.
2. Core schema invariants are covered by integration tests.
3. Validation tooling can report schema drift deterministically.

## 8. Migration Strategy

Use a four-phase migration discipline for any nontrivial schema change.

### Phase A: document and diagnose

1. Define the target schema change.
2. Add diagnostics to report current violations.
3. Add tests that describe target behavior.

### Phase B: additive introduction

1. Add new properties, constraints, or edge types without removing old ones.
2. Update readers to tolerate both old and new representations.

### Phase C: backfill and validate

1. Run migration/backfill scripts.
2. Validate counts, uniqueness, and join behavior.
3. Re-run integration tests.

### Phase D: deprecate and remove

1. Stop writing old representations.
2. Mark old schema constructs as deprecated in docs.
3. Remove old constructs only after compatibility windows and validation are complete.

This discipline should be followed for:

- key normalization
- predicate renaming
- relation-layer redesign
- any removal of dynamic-label dependence

## 9. Test Strategy

### 9.0 TDD execution rules for this plan

Every milestone implementation must use test-first sequencing.

Required order:

1. Write failing tests and diagnostics first.
2. Implement minimal code or migration changes.
3. Re-run full relevant suites.
4. Refactor and update docs only after green tests.

Mandatory test categories per schema change:

1. One unit-level contract test.
2. One regression test preventing reintroduction.
3. One integration or migration test when persisted graph shape changes.

The schema work needs more than unit tests. It needs layered validation.

### 9.1 Unit tests

Purpose:

- verify deterministic id builders
- verify mapping logic
- verify constraint-generation utilities or migration helpers

Examples:

1. `ARGM-*` to `argumentType` mapping tests.
2. deterministic `TIMEX` and `TEvent` identity construction tests.
3. compatibility-reader tests for old and new predicate names.

### 9.2 Regression tests

Purpose:

- lock known schema bugs so they do not return

Examples:

1. fusion must use canonical document containment edge.
2. non-core event enrichment must not contain unreachable mappings.
3. TLINK heuristics must not depend on nonexistent properties unless explicitly introduced.

### 9.3 Integration tests

Purpose:

- verify graph materialization and cross-phase invariants in Neo4j

Examples:

1. a review run materializes `AnnotatedText`, `Sentence`, `TagOccurrence`, `TIMEX`, `TEvent`, `DESCRIBES`, and `TLINK`.
2. canonical entity and event links remain joinable after migrations.
3. migrated graph and fresh graph both satisfy the same schema invariants.

### 9.4 Migration tests

Purpose:

- verify upgrade safety on representative legacy data shapes

Examples:

1. mixed string/int `doc_id` fixtures are normalized correctly.
2. duplicate key fixtures are detected before constraints are applied.
3. backfill from old predicates to new predicates produces expected canonical edges.

### 9.5 Diagnostics and query-pack validation

Purpose:

- give maintainers short operational checks outside pytest

Recommended additions:

1. duplicate natural-key scans for `TIMEX` and `TEvent`
2. legacy-edge usage scans
3. overloaded-predicate reporting
4. dynamic-label vocabulary audit for `FrameArgument`

## 10. Recommended Delivery Sequence

This is the recommended order of execution.

### Phase 1: low-risk, high-value stabilization

1. Milestone 0: canonical contract classification.
2. Milestone 1: identity and temporal normalization.
3. Milestone 2: immediate contradictions and stale assumptions.
4. Milestone 7: schema-level tests and diagnostics in parallel.

### Phase 2: enforcement and governance

1. Milestone 3: unify constraints and indexes under migrations.
2. Milestone 5: govern semantic categories.

### Phase 3: semantic cleanup and optional redesign

1. Milestone 4: predicate separation with compatibility mode.
2. Milestone 6: formalize or deprecate legacy relation abstraction.

## 11. Suggested Milestone Exit Checklist

Before closing any milestone, verify:

1. Documentation updated.
2. Migration strategy documented.
3. Tests added or updated.
4. Integration coverage executed where relevant.
5. Backward-compatibility impact documented.
6. Known negative consequences listed and accepted.

## 12. Final Recommendation

The schema should not be rewritten wholesale. The current design is already well aligned with event-centric knowledge representation in a property graph.

The correct strategy is:

1. preserve the current semantic core
2. normalize identity
3. reduce ambiguity
4. move enforcement into migrations
5. add schema-level validation
6. only then tackle more disruptive semantic renames or legacy-layer rationalization

That path best matches the project’s goals of explainability, temporal reasoning, entity resolution, and graph-based downstream analytics while minimizing avoidable breakage.
---

## Appendix A: MEANTIME NAF Alignment and Gap Analysis

### Overview

TextGraphX implements a document-grounded, token-anchored semantic model aligned with MEANTIME NAF (Multi-lingual Event-centric Annotation, Temporal Information, Multi-document and Evaluation). See [MEANTIME_GAP_ANALYSIS.md](./MEANTIME_GAP_ANALYSIS.md) for a comprehensive structured analysis.

### Critical Gaps Identified (5 Total)

The following structural gaps prevent full MEANTIME compliance and block advanced temporal/causal reasoning:

1. **No explicit ENTITY_MENTION or EVENT_MENTION node types** — TextGraphX conflates mentions with their canonical entities/events, preventing fine-grained mention-to-entity and mention-to-event reification
2. **Missing CLINK (causal links)** — no causal event relation type; blocks causal reasoning
3. **Missing SLINK (subordinating links)** — no speech event subordination; blocks quotation and reported-speech annotation
4. **Missing SIGNAL and C-SIGNAL nodes** — temporal/causal trigger words not explicitly annotated
5. **Incomplete event properties** — missing `class`, `aspect`, `certainty`, `polarity`, `time`, `special_cases`, `modality` needed for modal and epistemic reasoning

### Additional Minor Gaps

- TIMEX missing `functionInDocument`, `anchorTimeID`, `beginPoint`, `endPoint`
- Entity mentions lack `syntactic_type` classification (NAM, NOM, PRO, etc.)
- Semantic role relations lack `sem_role_framework` governance (PROPBANK, FRAMENET, KYOTO)
- VALUE type not distinguished (PERCENT, MONEY, QUANTITY)
- TLINK missing `signalID` references

### Recommended Milestone M8: MEANTIME-Aligned Mention Typing and Causal Reasoning

**Objective:** Extend schema to support MEANTIME-style mention reification, causal reasoning, and multi-framework semantic roles.

**Phase A: Introduce Mention Types**
- New labels: `ENTITY_MENTION`, `EVENT_MENTION`
- New relations: `ENTITY -[:REFERS_TO]- ENTITY_MENTION`, `TEVENT -[:REFERS_TO]- EVENT_MENTION`
- Migrate mention-specific properties from Entity/TEvent to their mention labels

**Phase B: Extend Temporal and Causal Relations**
- New labels: `SIGNAL`, `C-SIGNAL`
- New relations: `CLINK` (causal), `SLINK` (subordinating), `GLINK` (grammatical)
- Add signal anchoring to TLINK and new causal/subordinating edges

**Phase C: Enrich Event Properties**
- Add to TEvent: `class` {SPEECH_COGNITIVE, GRAMMATICAL, OTHER, MIX}, `external_ref`
- Add to EventMention: `pos`, `aspect`, `certainty`, `polarity`, `time`, `special_cases`, `modality`
- Add to TIMEX: `functionInDocument`, `anchorTimeID`, `beginPoint`, `endPoint`

**Phase D: Formalize Semantic Roles**
- Introduce `HAS_PARTICIPANT` relation with `sem_role_framework` governance
- Support PROPBANK, FRAMENET, KYOTO frameworks
- Properly structure VALUE nodes with type classification

**Timeline:** Post-M7; recommended for Phase 2+ after core schema hardening is complete and tests stabilize at 120+ passing.

**Impact:**
- ✅ Enables joint evaluation against MEANTIME-annotated datasets
- ✅ Supports causal and discourse reasoning
- ✅ Provides full multi-framework semantic role mapping
- ✅ Maintains backward compatibility via schema tiers
