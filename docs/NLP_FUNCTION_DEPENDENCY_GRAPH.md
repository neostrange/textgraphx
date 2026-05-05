# textgraphx — NLP Function Dependency Graph & Parallelism Map

**Generated:** May 2026  
**Scope:** Inter-function data dependencies, execution ordering, and parallelism opportunities across all pipeline stages.  
**Related documents:** [NLP_FUNCTION_CATALOG.md](NLP_FUNCTION_CATALOG.md), [MASTER_ARCHITECTURE_PLAN.md](MASTER_ARCHITECTURE_PLAN.md), [architecture-overview.md](architecture-overview.md)

---

## Table of Contents

1. [How to Read This Document](#how-to-read-this-document)
2. [Global Pipeline DAG](#global-pipeline-dag)
3. [Stage 1 Ingestion — Internal DAG](#stage-1-ingestion--internal-dag)
4. [Stage 2 Refinement — Internal DAG](#stage-2-refinement--internal-dag)
5. [Stage 3 Temporal — Internal DAG](#stage-3-temporal--internal-dag)
6. [Stage 4 Event Enrichment — Internal DAG](#stage-4-event-enrichment--internal-dag)
7. [Stage 5 TLINK Recognition — Internal DAG](#stage-5-tlink-recognition--internal-dag)
8. [Cross-Stage Reasoning — Internal DAG](#cross-stage-reasoning--internal-dag)
9. [Parallelism Opportunities Summary](#parallelism-opportunities-summary)
10. [Function I/O Contract Table](#function-io-contract-table)
11. [Critical Path Analysis](#critical-path-analysis)

---

## How to Read This Document

- **→** means "must complete before"
- **‖** means "can run in parallel"
- **Graph node** = Neo4j node type written or read
- **Input** = what Neo4j state the function requires to exist before it can run
- **Output** = what Neo4j state the function produces

A function group listed under **‖ PARALLEL GROUP** means all members of that group can be submitted concurrently. They share no data dependencies with each other (though all depend on the same upstream prerequisite).

---

## Global Pipeline DAG

```
RAW TEXT
    │
    ▼
[Stage 1: Ingestion]
    │ writes: AnnotatedText, Sentence, TagOccurrence, NamedEntity,
    │         Frame, FrameArgument, CorefMention, Antecedent,
    │         NounChunk, IS_DEPENDENT, IN_FRAME, PARTICIPANT
    ▼
[Stage 2: Refinement]
    │ reads:  all Stage 1 output
    │ writes: head properties, Entity, REFERS_TO, EntityMention,
    │         EventMention, EVENT_PARTICIPANT, synset enrichment
    ▼
[Stage 3: Temporal]      [Stage 4: Event Enrichment]
    │                           │
    │  (currently sequential,   │  (currently after Temporal;
    │   but 3→4 dependency      │   ideal ordering = 4→3→4 feedback)
    │   runs one-way)           │
    ▼                           ▼
[Stage 3+4 merged outputs]
    │ writes: TIMEX, TEvent, EventMention, DESCRIBES, INSTANTIATES
    ▼
[Stage 5: TLINK Recognition]
    │ reads:  TEvent, TIMEX, Signal, CSignal, TagOccurrence
    │ writes: TLINK edges
    ▼
[Cross-Stage Reasoning: Fusion]
    │ reads:  Entity (kb_id), Antecedent (head_text)
    │ writes: SAME_AS, CO_OCCURS_WITH
    ▼
COMPLETE KNOWLEDGE GRAPH
```

**Known ordering problem:** Stage 3 (Temporal) runs before Stage 4 (Event Enrichment) in the current hardcoded orchestrator. The linguistically correct order is: Event Enrichment should run first to establish event class/aspect, then Temporal normalization can use that information, then Event Enrichment runs a second pass to pick up new TEvents. This feedback loop is not implemented. See [MASTER_ARCHITECTURE_PLAN.md §8](MASTER_ARCHITECTURE_PLAN.md).

---

## Stage 1 Ingestion — Internal DAG

### Execution order within Ingestion

```
Step 1 (serial — document scaffolding)
    create_sentence_node
        → AnnotatedText and Sentence nodes must exist before all token writes

Step 2 (serial — token extraction)
    create_tag_occurrences  (or create_tag_occurrences2)
        → TagOccurrence nodes must exist before dep parse, NER span links, SRL token links

Step 3 (serial — dep parse)
    create_tag_occurrence_dependencies
        → extract raw dep tuples from spaCy Doc
    process_dependencies  (or process_dependencies2)
        → IS_DEPENDENT edges written; required by Refinement head assignment

Step 4 ‖ PARALLEL GROUP — all fire after Step 2 completes, independent of each other
┌─────────────────────────────────────────────────────────────────────────────┐
│  GROUP A: NER                                                               │
│    process_entities                                                         │
│      → _normalize_syntactic_type                                            │
│      → _syntactic_type_from_tag                                             │
│      → _map_to_meantime_class                                               │
│    store_entities         (writes NamedEntity nodes)                        │
│    store_value_mentions   (writes VALUE NamedEntity nodes)                  │
│    store_spacy_timex_candidates  (writes TimexMention candidates)           │
├─────────────────────────────────────────────────────────────────────────────┤
│  GROUP B: PropBank SRL (verbal) — transformer-srl port 8010                │
│    SemanticRoleLabel.__call__                                               │
│      → replace_hyphens_to_underscores                                      │
│      → get_sent_wise_res_srl → callAllenNlpApi  (network: port 8010)       │
│      → extract_srl                                                         │
│      → post_process_verbframe                                               │
│    process_srl  (writes Frame{PROPBANK}, FrameArgument, PARTICIPANT)       │
│      → _merge_frame                                                         │
│      → _merge_frame_argument                                                │
│      → _link_argument_to_frame                                              │
│      → _link_indices_to_node                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  GROUP C: NomBank SRL (nominal) — CogComp port 8011                        │
│    callNominalSrlApi  (network: port 8011)                                  │
│    process_nominal_srl  (writes Frame{NOMBANK}, FrameArgument)             │
│      → _bio_to_spans                                                        │
│      → _merge_frame                                                         │
│      → _merge_frame_argument                                                │
│      → _link_argument_to_frame                                              │
│      → _link_indices_to_node                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  GROUP D: Word Sense Disambiguation — AMuSE-WSD port 81                    │
│    perform_wsd                                                              │
│      → replace_hyphens_to_underscores                                      │
│      → _call_amuse_wsd_api  (network: port 81)                             │
│      → _update_tokens_in_neo4j  (writes synset_id to TagOccurrence)       │
├─────────────────────────────────────────────────────────────────────────────┤
│  GROUP E: Entity Linking — Entity-Fishing (Wikidata)                       │
│    EntityFishing.__call__                                                   │
│      → main_disambiguation_process                                          │
│        → prepare_data                                                       │
│        → disambiguate_text  (network: Entity-Fishing service)              │
│        → process_response                                                   │
│      → updated_entities                                                     │
│        → look_extra_informations_on_entity                                 │
│        → concept_look_up  (network: Entity-Fishing service)               │
├─────────────────────────────────────────────────────────────────────────────┤
│  GROUP F: Coreference — spacy-experimental-coref (in-process)              │
│    resolve_coreference                                                      │
│      → _extract_spacy_coref_clusters  (reads doc.spans from spaCy)        │
│      → _service_span_to_inclusive_bounds                                   │
│      → _find_named_entity_by_span  (reads Neo4j: depends on GROUP A)      │
│      → create_node  (writes Antecedent/CorefMention)                       │
│      → connect_node_to_tag_occurrences  (writes IN_MENTION)               │
└─────────────────────────────────────────────────────────────────────────────┘
    NOTE: GROUP F has a soft dependency on GROUP A completing first
    (it queries NamedEntity to avoid duplicates). All others are independent.

Step 5 (serial — entity fusion, requires Groups A completed)
    fuse_entities
      → assign_head_info_to_multitoken_entities
      → assign_head_info_to_singletoken_entities
      → prioritize_spacy_entities
      → prioritize_dbpedia_entities

Step 6 (serial — external NER API, if used in addition to spaCy)
    extract_entities  (network: external NER API)
    integrate_entities_into_db
      → _reconcile_stale_named_entities
      → _resolve_uid_anchor_token_index

Step 7 (serial — syntactic chunking, independent of Steps 4–6)
    process_noun_chunks
    store_noun_chunks
```

### Ingestion parallelism summary

| Task Group | Can Start After | Duration Estimate | Parallelisable |
|-----------|-----------------|-------------------|----------------|
| A: NER | TagOccurrence nodes written | Fast (local spaCy) | Yes — parallel with B, C, D, E |
| B: PropBank SRL | TagOccurrence nodes written | Medium (network port 8010) | **Yes — parallel with A, C, D, E** |
| C: NomBank SRL | TagOccurrence nodes written | Medium (network port 8011) | **Yes — parallel with A, B, D, E** |
| D: WSD | TagOccurrence nodes written | Medium (network port 81) | Yes — parallel with A, B, C, E |
| E: Entity-Fishing | TagOccurrence nodes written | Slow (network, per-entity) | Yes — parallel with A, B, C, D |
| F: Coreference | TagOccurrence + NamedEntity written | Fast (in-process) | Soft dep on A |
| Entity Fusion | Groups A, F done | Fast (Cypher only) | No — serial |
| Noun Chunks | TagOccurrence nodes written | Fast (local spaCy) | Yes — parallel with A–F |

**Key optimization:** Groups B (PropBank) and C (NomBank) are the two most expensive operations in ingestion. They call different services on different ports with no shared state. Running them in parallel halves the SRL latency.

---

## Stage 2 Refinement — Internal DAG

```
Step 1 ‖ PARALLEL GROUP — Head Assignment
    (all require IS_DEPENDENT edges from Ingestion Step 3)
    (all are independent of each other — write to different node types)
┌────────────────────────────────────────────────────────────────────────┐
│  get_and_assign_head_info_to_entity_multitoken                        │
│  get_and_assign_head_info_to_entity_singletoken                       │
│  get_and_assign_head_info_to_antecedent_multitoken                    │
│  get_and_assign_head_info_to_antecedent_singletoken                   │
│  get_and_assign_head_info_to_corefmention_multitoken                  │
│  get_and_assign_head_info_to_corefmention_singletoken                 │
│  get_and_assign_head_info_to_all_frameArgument_multitoken             │
│  get_and_assign_head_info_to_all_frameArgument_singletoken            │
│  get_and_assign_head_info_to_temporal_frameArgument_multitoken        │
│  get_and_assign_head_info_to_temporal_frameArgument_singletoken       │
│  get_and_assign_head_info_to_eventive_frameArgument_multitoken        │
│  get_and_assign_head_info_to_eventive_frameArgument_singletoken       │
└────────────────────────────────────────────────────────────────────────┘
    ↓ all must complete before Step 2

Step 2 ‖ PARALLEL GROUP — Frame–Entity Linking
    (requires head properties to exist on all mention nodes from Step 1)
┌────────────────────────────────────────────────────────────────────────┐
│  link_frameArgument_to_namedEntity_for_nam_nom                        │
│  link_frameArgument_to_namedEntity_for_pobj                           │
│  link_frameArgument_to_namedEntity_for_pro                            │
│  link_frameArgument_to_numeric_entities                               │
│  link_antecedent_to_namedEntity                                       │
│  link_frameArgument_to_entity_via_named_entity                        │
└────────────────────────────────────────────────────────────────────────┘
    ↓ link_frameArgument_to_new_entity must run AFTER all others
      (creates fallback Entity only for still-unlinked args)

Step 3 (serial — entity disambiguation, requires Step 2)
    disambiguate_entities
        → creates canonical Entity nodes from NamedEntity
        → writes REFERS_TO bridge edges

Step 4 ‖ PARALLEL GROUP — Mention Materialization
    (all require Step 2 linking to be complete; all write distinct node types)
┌────────────────────────────────────────────────────────────────────────┐
│  materialize_nominal_mentions_from_frame_arguments                    │
│  materialize_nominal_mentions_from_noun_chunks                        │
│  materialize_predicate_nominal_mentions                               │
│  materialize_appositive_mentions                                      │
└────────────────────────────────────────────────────────────────────────┘

Step 5 (serial — event promotion, requires Step 4)
    promote_nominal_events
    assign_meantime_syntactic_types
    detect_quantified_entities_from_frameArgument

Step 6 ‖ PARALLEL GROUP — Semantic Enrichment
    (both independent, read only, enrich token/mention properties)
┌────────────────────────────────────────────────────────────────────────┐
│  assign_synset_info_to_tokens  (requires synset_id from WSD in Stage 1)│
│    → get_all_hypernyms                                                  │
│    → get_synonyms                                                       │
│    → get_domain_labels                                                  │
│    → get_derivational_features → _lemma_similarity                     │
│    → get_verb_relation_features                                         │
│    → get_depth_features                                                 │
│                                                                         │
│  normalize_srl_annotation  (normalizes SRL roles in-place)             │
│    → normalize_propbank_role                                            │
│    → normalize_framenet_role                                            │
│    → suggest_framenet_frame                                             │
│    → validate_frame_role_structure                                      │
│    → validate_role_structure                                            │
└────────────────────────────────────────────────────────────────────────┘
```

### Refinement parallelism summary

| Step | Parallel? | Prerequisite |
|------|-----------|-------------|
| Head Assignment (12 methods) | **All parallel** | `IS_DEPENDENT` edges exist |
| Frame–Entity Linking (6 methods) | **All parallel** (except `link_*_new_entity` last) | Head assignment done |
| `link_frameArgument_to_new_entity` | Serial (last) | All other linking done |
| Mention materialization (4 methods) | **All parallel** | Frame–entity linking done |
| Event promotion / type assignment | Serial | Materialization done |
| WordNet enrichment + SRL normalization | **Both parallel** | WSD synset IDs exist |

---

## Stage 3 Temporal — Internal DAG

```
Step 1 (serial — document retrieval)
    get_annotated_text  →  get_doc_text_and_dct

Step 2 ‖ PARALLEL GROUP — External temporal taggers (independent services)
┌────────────────────────────────────────────────────────────────────────┐
│  callHeidelTimeService  (port 5000 — TIMEX3 detection)                 │
│  callTtkService         (port 5050 — TimeML event/signal extraction)   │
└────────────────────────────────────────────────────────────────────────┘
    ↓ both outputs merged before Step 3

Step 3 (serial — TIMEX + Signal persistence)
    materialize_signals
        → creates Signal, CSignal, TIMEX, TimexMention nodes
        → writes TIMEX token-span grounding
```

**HeidelTime** and **TTK** are fully independent services targeting the same text. They can be called concurrently. The merged output is deduplicated by span before writing.

---

## Stage 4 Event Enrichment — Internal DAG

```
Step 1 (serial — frame→event binding)
    _describe_frame_and_role
        → writes FRAME_DESCRIBES_EVENT edges
        → reads: Frame nodes (from Stage 1), TEvent nodes (from Stage 3)

Step 2 (serial — event mention creation)
    materialize_event_mentions
        → writes EventMention nodes
        → writes REFERS_TO → TEvent edges

Step 3 (serial — frame instantiation)
    attach_frames_to_event_mentions
        → writes INSTANTIATES edges from Frame → EventMention

Step 4 (query generation — no writes)
    _participant_source_subquery
        → generates Cypher subquery for participant resolution (used inside Step 1 query)
```

Event Enrichment is largely serial within itself. The main opportunity is between Stage 3 and Stage 4 (currently sequential, should be feedback-loop per [MASTER_ARCHITECTURE_PLAN.md §3.2.1]).

---

## Stage 5 TLINK Recognition — Internal DAG

```
Step 1 (serial — document list)
    get_annotated_text

Step 2 ‖ PARALLEL GROUP — TLINK pattern cases (per document)
    (all 6 cases read from the same Neo4j state but write to distinct TLINK edges)
    (no case reads another case's output — pure write-only, no conflicts)
┌────────────────────────────────────────────────────────────────────────┐
│  create_tlinks_case1   AFTER via "after" signal                        │
│  create_tlinks_case2   TLINK via gerund complement + signal            │
│  create_tlinks_case3   TLINK via gerund head temporal arg              │
│  create_tlinks_case4   Event → TIMEX via temporal noun head            │
│  create_tlinks_case5   Event → TIMEX via preposition + signal type     │
│  create_tlinks_case6   Event → DCT anchor                              │
└────────────────────────────────────────────────────────────────────────┘
    all delegate to: _run_query  (shared Neo4j executor)
```

**All 6 TLINK cases are independent.** They produce non-overlapping edge sets (different pattern matches). They can be submitted as 6 concurrent Cypher queries against Neo4j per document.

---

## Cross-Stage Reasoning — Internal DAG

```
Step 1 ‖ PARALLEL GROUP — Entity fusion (all independent)
┌────────────────────────────────────────────────────────────────────────┐
│  fuse_entities_cross_sentence        (writes CO_OCCURS_WITH)           │
│  fuse_entities_cross_document        (writes SAME_AS via kb_id)        │
│  propagate_coreference_identity_cross_document  (writes SAME_AS)       │
└────────────────────────────────────────────────────────────────────────┘
```

**Prerequisite:** All 5 pipeline stages complete. Entity `kb_id` must be populated (from Entity-Fishing in Stage 1). Antecedent `head_text` must be set (from head assignment in Stage 2).

---

## Parallelism Opportunities Summary

The table below consolidates all identified parallelism opportunities ranked by latency impact.

| # | Opportunity | Currently | Potential Gain | Risk |
|---|------------|-----------|----------------|------|
| **P1** | PropBank SRL (port 8010) ‖ NomBank SRL (port 8011) | Sequential | Halves SRL wall time (dominant cost) | Neo4j write conflicts on shared `FrameArgument` keys — requires MERGE idempotency (already implemented) |
| **P2** | SRL ‖ WSD ‖ Entity-Fishing ‖ NER (all Stage 1 service calls) | Sequential | 3–4× speedup on ingestion network I/O | Soft dep: Entity-Fishing best after NER; WSD reads tokens not entities |
| **P3** | All 12 head-assignment methods (Refinement Step 1) | Sequential loop | 12× speedup on small Cypher ops | None — each targets distinct node type |
| **P4** | HeidelTime ‖ TTK (Stage 3 service calls) | Sequential | Halves temporal service latency | Merge/dedup required on TIMEX output |
| **P5** | All 6 TLINK case queries (Stage 5) | Sequential loop | 6× speedup on rule evaluation | None — write to distinct edge sets |
| **P6** | 6 Frame–entity linking methods (Refinement Step 2) | Sequential loop | 6× speedup | `link_*_new_entity` must be last |
| **P7** | 3 cross-document fusion methods | Sequential | 3× speedup | None — write to distinct edges |
| **P8** | WordNet enrichment ‖ SRL normalization (Refinement Step 6) | Sequential | 2× speedup | None — independent read paths |

### Which parallelism to implement first

```
Priority order for DAG orchestrator implementation:
1. P1  (PropBank ‖ NomBank) — highest latency, lowest risk
2. P2  (Stage 1 service calls in parallel) — significant latency, needs coordination
3. P5  (TLINK cases in parallel) — easy to implement, measurable improvement
4. P3  (head assignment in parallel) — easy but small absolute gain
5. P4  (HeidelTime ‖ TTK) — medium gain
```

---

## Function I/O Contract Table

The table below documents the graph-state preconditions (reads) and postconditions (writes) for every major function. This is the formal contract that a DAG orchestrator must enforce.

| Function | Reads from Graph | Writes to Graph | Can Start When |
|----------|-----------------|-----------------|----------------|
| `create_sentence_node` | `AnnotatedText` (must exist) | `:Sentence`, `HAS_SENTENCE` | AnnotatedText created |
| `create_tag_occurrences` | `Sentence` nodes | `:TagOccurrence`, `HAS_TOKEN` | Sentences created |
| `process_dependencies` | `TagOccurrence` nodes | `:IS_DEPENDENT` edges | TagOccurrence written |
| `process_entities` | spaCy Doc (in-memory) | `:NamedEntity` nodes | Sentences created |
| `store_entities` | entity dicts (in-memory) | `:NamedEntity` nodes | process_entities done |
| `fuse_entities` | `NamedEntity` nodes | head properties on NE | store_entities done |
| `SemanticRoleLabel.__call__` | spaCy Doc | `token._.srl_frames` extension | spaCy pipeline loaded |
| `process_srl` | `token._.srl_frames`, `TagOccurrence` | `:Frame{PROPBANK}`, `:FrameArgument`, `:PARTICIPANT` | TagOccurrence + SRL extensions |
| `callNominalSrlApi` | sentence text (string) | NomBank JSON (in-memory) | — (external service) |
| `process_nominal_srl` | NomBank JSON, `TagOccurrence` | `:Frame{NOMBANK}`, `:FrameArgument` | TagOccurrence + NomBank response |
| `resolve_coreference` | spaCy Doc, `NamedEntity` | `:Antecedent`, `:CorefMention`, `:IN_MENTION` | NamedEntity nodes exist |
| `perform_wsd` | `TagOccurrence` text tokens | `synset_id`, `babelnet_id` on TagOccurrence | TagOccurrence written |
| `EntityFishing.__call__` | spaCy Doc (spans) | `kb_id`, `url`, `description` on span extensions | spaCy NER done |
| `get_and_assign_head_info_*` | `NamedEntity`/`CorefMention`/`FrameArgument` + `IS_DEPENDENT` | `head_text`, `head_index` properties | IS_DEPENDENT edges exist |
| `link_frameArgument_to_namedEntity_*` | `FrameArgument` head props, `NamedEntity` head props | `:REFERS_TO` edges | Head assignment done |
| `link_frameArgument_to_new_entity` | FrameArgument nodes (all unlinked) | new `:Entity` + `:REFERS_TO` | All other linking done |
| `disambiguate_entities` | `NamedEntity` + REFERS_TO edges | `:Entity` canonical nodes | Frame–entity linking done |
| `materialize_nominal_mentions_*` | `FrameArgument`/`NounChunk` nodes | `:EntityMention` nodes | Linking done |
| `promote_nominal_events` | `EntityMention` candidates | `:EventMention` nodes | Materialization done |
| `assign_synset_info_to_tokens` | `TagOccurrence` with `synset_id` | hypernym/synonym/depth properties | WSD (perform_wsd) done |
| `get_doc_text_and_dct` | `AnnotatedText` node | `(text, dct)` tuple in-memory | AnnotatedText exists |
| `callHeidelTimeService` | document text (string) | TimeML XML (in-memory) | — (external service) |
| `callTtkService` | document text (string) | TTK XML (in-memory) | — (external service) |
| `materialize_signals` | parsed TimeML data | `:Signal`, `:CSignal`, `:TIMEX`, `:TimexMention` | HeidelTime + TTK responses parsed |
| `_describe_frame_and_role` | `Frame` + `TEvent` nodes | `:FRAME_DESCRIBES_EVENT` edge | Temporal phase done |
| `materialize_event_mentions` | `Frame` + `TEvent` | `:EventMention` + `:REFERS_TO` | _describe_frame_and_role done |
| `attach_frames_to_event_mentions` | `Frame` + `EventMention` | `:INSTANTIATES` edges | materialize_event_mentions done |
| `create_tlinks_case1..6` | `TEvent`, `TIMEX`, `Signal`, `TagOccurrence` | `:TLINK` edges | Event enrichment done |
| `fuse_entities_cross_sentence` | `Entity` nodes, sentence indices | `:CO_OCCURS_WITH` | All stages done |
| `fuse_entities_cross_document` | `Entity.kb_id` across documents | `:SAME_AS` | All stages done |
| `propagate_coreference_identity_cross_document` | `Antecedent.head_text` | `:SAME_AS` | All stages done |

---

## Critical Path Analysis

The critical path is the longest chain of sequential dependencies. Optimizing off-critical-path items gives no wall-time benefit until the critical path is addressed.

```
CRITICAL PATH (current architecture, sequential):

create_sentence_node                    ~5ms
→ create_tag_occurrences                ~10ms  (spaCy transformer)
→ process_dependencies                  ~10ms
→ SemanticRoleLabel.__call__            ~800ms (transformer-srl network call)
→ callNominalSrlApi                     ~600ms (CogComp network call) ← BOTTLENECK
→ process_srl + process_nominal_srl     ~50ms
→ resolve_coreference                   ~200ms (in-process spaCy-coref)
→ fuse_entities                         ~30ms
→ [Stage 1 complete]
→ head assignment (12 methods serial)   ~120ms
→ linking (7 methods serial)            ~70ms
→ materialization                       ~40ms
→ disambiguate_entities                 ~30ms
→ assign_synset_info_to_tokens          ~80ms
→ [Stage 2 complete]
→ callHeidelTimeService                 ~300ms (network)
→ callTtkService                        ~400ms (network)  ← SEQUENTIAL TODAY
→ materialize_signals                   ~30ms
→ [Stage 3 complete]
→ _describe_frame_and_role              ~40ms
→ materialize_event_mentions            ~30ms
→ [Stage 4 complete]
→ create_tlinks_case1..6 (serial)       ~120ms
→ [Stage 5 complete]
→ fusion (3 methods serial)             ~60ms

TOTAL (estimated, per document): ~3.0 seconds
```

```
CRITICAL PATH (after P1+P2+P4+P5 parallelism applied):

create_sentence_node + create_tag_occurrences + process_dependencies  ~25ms
→ [Stage 1 parallel: PropBank ‖ NomBank ‖ WSD ‖ Entity-Fishing ‖ NER]
   longest: max(PropBank ~800ms, NomBank ~600ms) = ~800ms
→ resolve_coreference + fuse_entities  ~230ms
→ [Stage 2: head assignment (12 parallel) ~15ms → linking (6 parallel) ~15ms → ...]
   ~200ms total
→ [Stage 3: HeidelTime ‖ TTK in parallel = max(300, 400) = ~400ms]
→ [Stage 4: serial ~100ms]
→ [Stage 5: 6 TLINK cases parallel = ~25ms]
→ [Fusion: 3 methods parallel = ~20ms]

TOTAL (estimated, per document): ~1.8 seconds  (~40% reduction)
```

The dominant remaining bottleneck after all parallelism is applied is **PropBank SRL latency (~800ms network call)**. This is the single function worth optimizing if wall-time is the primary concern (batching, caching, or upgrading to `callAllenNlpApiBatch` with concurrent httpx).

---

## Notes on Current Architecture Deviations

1. **Stages 3 and 4 are in the wrong order.** The correct dependency is `Event Enrichment (partial) → Temporal → Event Enrichment (second pass)`. The current sequence `Temporal → Event Enrichment` means temporal normalization cannot use event class/aspect information.

2. **Head assignment is run 12 times sequentially** in `run_all_rule_families()`. These 12 Cypher queries are independent and could be submitted concurrently within a single transaction batch.

3. **TLINK cases 1–6 are run in a loop.** They are pattern-matched Cypher queries that write to non-overlapping edge sets. They could be submitted as 6 concurrent Neo4j transactions per document.

4. **PropBank and NomBank SRL are called sequentially** inside `GraphBasedNLP.process()`. There is no architectural reason for this — they hit different services. The fix is a single `asyncio.gather()` or thread pool call.

5. **WordNet enrichment (`assign_synset_info_to_tokens`) depends on WSD completing** in Stage 1. WSD is currently run inside Refinement, not Ingestion, meaning the WordNet enrichment step cannot be parallelized with Stage 1 operations. Relocating WSD to Stage 1 (where AMuSE-WSD is called) would unblock this.
