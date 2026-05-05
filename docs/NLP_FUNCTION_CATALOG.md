# textgraphx — NLP / IE Function Catalog

**Generated:** May 2026  
**Scope:** All linguistic, NLP, and information-extraction functions across the five pipeline stages and the cross-stage reasoning layer.  
**Related documents:** [architecture-overview.md](architecture-overview.md), [MASTER_ARCHITECTURE_PLAN.md](MASTER_ARCHITECTURE_PLAN.md), [NLP_FUNCTION_DEPENDENCY_GRAPH.md](NLP_FUNCTION_DEPENDENCY_GRAPH.md)

---

## Table of Contents

1. [Stage 1 — Ingestion](#stage-1--ingestion)
   - 1.1 Tokenization & Morphology
   - 1.2 Dependency Parsing (Syntax)
   - 1.3 Named Entity Recognition (NER)
   - 1.4 Syntactic Chunking
   - 1.5 Entity Fusion
   - 1.6 Entity Linking (Entity-Fishing → Wikidata)
   - 1.7 Coreference Resolution
   - 1.8 PropBank SRL — Verbal
   - 1.9 NomBank SRL — Nominal
   - 1.10 SRL Persistence
   - 1.11 Word Sense Disambiguation
2. [Stage 2 — Refinement](#stage-2--refinement)
   - 2.1 Head Assignment
   - 2.2 Frame–Entity Linking
   - 2.3 Mention Materialization
   - 2.4 WordNet Semantic Enrichment
   - 2.5 SRL Role Normalization
   - 2.6 Entity Disambiguation
3. [Stage 3 — Temporal Extraction](#stage-3--temporal-extraction)
4. [Stage 4 — Event Enrichment](#stage-4--event-enrichment)
5. [Stage 5 — TLINK Recognition](#stage-5--tlink-recognition)
6. [Cross-Stage Reasoning](#cross-stage-reasoning)
7. [REST API Adapters](#rest-api-adapters)
8. [Summary Statistics](#summary-statistics)
9. [What Is Missing](#what-is-missing)

---

## Stage 1 — Ingestion

**Module:** `src/textgraphx/pipeline/ingestion/` and `text_processing_components/`  
**Input:** Raw document text (plain string) + `doc_id`  
**Output written to Neo4j:** `AnnotatedText`, `Sentence`, `TagOccurrence`, `NamedEntity`, `Frame`, `FrameArgument`, `NounChunk`, `Antecedent`, `CorefMention`

---

### 1.1 Tokenization & Morphology

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `create_sentence_node` | `SentenceCreator` | `SentenceCreator.py` | Create/merge `Sentence` node; link to `AnnotatedText` | `doc_id`, sentence index, sentence text | `:Sentence` node, `HAS_SENTENCE` edge |
| `create_tag_occurrences` | `TagOccurrenceCreator` | `TagOccurrenceCreator.py` | Extract tokens with POS, lemma, morph features | spaCy `Token` | `:TagOccurrence` nodes with `pos`, `tag`, `lemma`, `morph` |
| `create_tag_occurrences2` | `TagOccurrenceCreator` | `TagOccurrenceCreator.py` | Extract tokens without morphological features | spaCy `Token` | `:TagOccurrence` nodes with `pos`, `tag`, `lemma` |

**Dependencies:** spaCy `en_core_web_trf` pipeline must be loaded. `AnnotatedText` node must pre-exist.

---

### 1.2 Dependency Parsing (Syntax)

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `create_tag_occurrence_dependencies` | `TagOccurrenceDependencyProcessor` | `TagOccurrenceDependencyProcessor.py` | Extract dep-parse tuples from spaCy sentence | spaCy `Token.head`, `Token.dep_` | List of `(child_id, head_id, dep_label)` tuples |
| `process_dependencies` | `TagOccurrenceDependencyProcessor` | `TagOccurrenceDependencyProcessor.py` | Write `IS_DEPENDENT` edges as batch UNWIND query | dep tuples from above | `:IS_DEPENDENT` edges with `dep` property |
| `process_dependencies2` | `TagOccurrenceDependencyProcessor` | `TagOccurrenceDependencyProcessor.py` | Write `IS_DEPENDENT` edges per token pair | dep tuples from above | `:IS_DEPENDENT` edges per pair |

**Ordering constraint:** `TagOccurrence` nodes must exist before dep edges can be written.

---

### 1.3 Named Entity Recognition (NER)

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `process_entities` | `EntityProcessor` | `EntityProcessor.py` | Extract NE spans from spaCy Doc; derive syntactic types | spaCy `Doc.ents`, `filter_spans` | List of entity dicts with `start_tok`, `end_tok`, `label`, `syntactic_type` |
| `_normalize_syntactic_type` | `EntityProcessor` | `EntityProcessor.py` | Normalize syntactic type string | raw type string | `NAM` / `NOM` / `PRO` / `OTHER` |
| `_syntactic_type_from_tag` | `EntityProcessor` | `EntityProcessor.py` | Derive type from POS tag + dependency | `token.tag_`, `token.dep_` | syntactic type string |
| `_map_to_meantime_class` | `EntityProcessor` | `EntityProcessor.py` | Map spaCy entity label → MEANTIME entity class | spaCy entity label | MEANTIME class string |
| `store_entities` | `EntityProcessor` | `EntityProcessor.py` | Persist `NamedEntity` nodes with deterministic IDs | entity dicts | `:NamedEntity` nodes, `HAS_MENTION` edges |
| `store_value_mentions` | `EntityProcessor` | `EntityProcessor.py` | Persist numeric/value entity mentions | spaCy `Doc` | `:NamedEntity` nodes typed as VALUE |
| `store_spacy_timex_candidates` | `EntityProcessor` | `EntityProcessor.py` | Persist spaCy `DATE`/`TIME` spans as TIMEX candidates | spaCy `Doc` | `:TimexMention` candidate nodes |
| `extract_entities` | `EntityExtractor` | `EntityExtractor.py` | Call external NER API | document text | entity JSON list |
| `integrate_entities_into_db` | `EntityExtractor` | `EntityExtractor.py` | Persist API-returned entities; retire stale mentions | entity JSON, `doc_id` | `:NamedEntity` nodes; stale-flag on old mentions |
| `_reconcile_stale_named_entities` | `EntityExtractor` | `EntityExtractor.py` | Mark unseen `NamedEntity` nodes as stale | current `NamedEntity` set | stale flag on Neo4j nodes |
| `_resolve_uid_anchor_token_index` | `EntityExtractor` | `EntityExtractor.py` | Resolve anchor token for deterministic UID | entity dict | anchor token index int |

---

### 1.4 Syntactic Chunking

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `process_noun_chunks` | `NounChunkProcessor` | `NounChunkProcessor.py` | Extract noun chunks from spaCy Doc | spaCy `Doc.noun_chunks` | List of chunk dicts with `start_tok`, `end_tok` |
| `store_noun_chunks` | `NounChunkProcessor` | `NounChunkProcessor.py` | Persist `NounChunk` nodes with syntactic type | chunk dicts | `:NounChunk` nodes |
| `_syntactic_type_from_tag` | `NounChunkProcessor` | `NounChunkProcessor.py` | Derive type from POS tag | `token.tag_` | `NOMINAL` / `NAM` / `PRO` |

---

### 1.5 Entity Fusion

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `fuse_entities` | `EntityFuser` | `EntityFuser.py` | Orchestrate head-assignment + entity prioritization passes | `doc_id` | head properties set on existing NE nodes |
| `assign_head_info_to_multitoken_entities` | `EntityFuser` | `EntityFuser.py` | Assign head token metadata to multi-token spans | `NamedEntity` nodes without head info | `head_text`, `head_index` set |
| `assign_head_info_to_singletoken_entities` | `EntityFuser` | `EntityFuser.py` | Assign head token metadata to single-token spans | `NamedEntity` nodes without head info | `head_text`, `head_index` set |
| `prioritize_spacy_entities` | `EntityFuser` | `EntityFuser.py` | Prefer spaCy NEs for numeric/temporal types | conflicting NE annotations | stale flags on lower-priority nodes |
| `prioritize_dbpedia_entities` | `EntityFuser` | `EntityFuser.py` | Prefer DBpedia-linked NEs; preserve nested spans | conflicting NE annotations | stale flags; nested entities preserved |

**Ordering constraint:** `store_entities` must complete before fusion runs.

---

### 1.6 Entity Linking (Entity-Fishing → Wikidata)

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `__call__` | `EntityFishing` | `entity_fishing.py` | spaCy component: run full disambiguation + nil-clustering | spaCy `Doc` | `kb_id`, `url`, `description` set on span extensions |
| `main_disambiguation_process` | `EntityFishing` | `entity_fishing.py` | Orchestrate full Entity-Fishing workflow | spaCy `Doc` | disambiguated entity data |
| `prepare_data` | `EntityFishing` | `entity_fishing.py` | Serialize request payload for Entity-Fishing API | spaCy `Doc` | JSON request payload |
| `disambiguate_text` | `EntityFishing` | `entity_fishing.py` | POST to Entity-Fishing service | JSON payload | Entity-Fishing response JSON |
| `process_response` | `EntityFishing` | `entity_fishing.py` | Decode Entity-Fishing JSON response | raw JSON | list of entity-fishing results |
| `updated_entities` | `EntityFishing` | `entity_fishing.py` | Attach Wikidata QID, URLs, scores to spaCy spans | entity-fishing results, spaCy `Doc` | span extensions populated |
| `look_extra_informations_on_entity` | `EntityFishing` | `entity_fishing.py` | Attach extra KB metadata to span extension | single entity result | span extensions enriched |
| `concept_look_up` | `EntityFishing` | `entity_fishing.py` | Look up KB metadata for an entity by ID | entity ID string | KB metadata JSON |
| `generic_client` | `EntityFishing` | `entity_fishing.py` | Generic REST client for Entity-Fishing endpoints | URL, params | response JSON |

---

### 1.7 Coreference Resolution

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `_extract_spacy_coref_clusters` | `CoreferenceResolver` | `CoreferenceResolver.py` | Extract clusters from spaCy `doc.spans` (spacy-experimental-coref) | spaCy `Doc.spans` | list of cluster dicts `{head, mentions}` |
| `call_coreference_resolution_api` | `CoreferenceResolver` | `CoreferenceResolver.py` | POST to external coref service | document text | coref cluster JSON |
| `_service_span_to_inclusive_bounds` | `CoreferenceResolver` | `CoreferenceResolver.py` | Normalize `[start, end)` → `[start, end]` inclusive | half-open span tuple | closed span tuple |
| `_find_named_entity_by_span` | `CoreferenceResolver` | `CoreferenceResolver.py` | Find existing `NamedEntity` matching span (avoid duplicate creation) | span bounds, `doc_id` | matching `NamedEntity` node or `None` |
| `create_node` | `CoreferenceResolver` | `CoreferenceResolver.py` | Create/merge `Antecedent`/`CorefMention` node with deterministic ID | cluster head span, `doc_id` | `:Antecedent` or `:CorefMention` node |
| `connect_node_to_tag_occurrences` | `CoreferenceResolver` | `CoreferenceResolver.py` | Link `TagOccurrence` tokens to coref node via `IN_MENTION` | coref node, span bounds | `:IN_MENTION` edges |
| `resolve_coreference` | `CoreferenceResolver` | `CoreferenceResolver.py` | Top-level: extract clusters and persist all nodes/edges | spaCy `Doc` or API result | `Antecedent`, `CorefMention` nodes; `IN_MENTION` edges |

**Ordering constraint:** `TagOccurrence` nodes must exist before `connect_node_to_tag_occurrences`.

---

### 1.8 PropBank SRL — Verbal (transformer-srl, port 8010)

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `__call__` | `SemanticRoleLabel` | `semantic_role_labeler.py` | spaCy component: annotate Doc with SRL | spaCy `Doc` | `token._.srl_frames` extensions populated |
| `get_sent_wise_res_srl` | `SemanticRoleLabel` | `semantic_role_labeler.py` | Get per-sentence SRL from transformer-srl | sentence text | SRL JSON per sentence |
| `extract_srl` | `SemanticRoleLabel` | `semantic_role_labeler.py` | Extract BIO-tagged roles + PropBank frame/confidence | SRL JSON | list of `(predicate, roles, frame, confidence)` |
| `post_process_verbframe` | `SemanticRoleLabel` | `semantic_role_labeler.py` | Convert BIO tags to argument span tuples | BIO tag list | list of `(label, start, end)` spans |
| `srl_doc` | `SemanticRoleLabel` | `semantic_role_labeler.py` | Call SRL on full document text | document text | SRL JSON response |
| `replace_hyphens_to_underscores` | `SemanticRoleLabel` | `semantic_role_labeler.py` | Preprocessing: replace infix hyphens | raw text string | preprocessed string |

---

### 1.9 NomBank SRL — Nominal (CogComp, port 8011)

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `callNominalSrlApi` | `rest_caller` | `rest_caller.py` | POST to CogComp nominal-SRL; circuit breaker + cache | sentence text | NomBank JSON response |
| `callNominalSrlApiBatch` | `rest_caller` | `rest_caller.py` | Concurrent batch POST to CogComp nominal-SRL | list of sentences | list of NomBank JSON responses |
| `_bio_to_spans` | `SRLProcessor` | `SRLProcessor.py` | Convert BIO tag sequence → `(label, start, end)` triples | BIO tag list | list of span tuples |
| `process_nominal_srl` | `SRLProcessor` | `SRLProcessor.py` | Persist CogComp nominal-SRL frames with sense info | NomBank response, `doc_id` | `:Frame{framework:NOMBANK}` nodes, `:FrameArgument` nodes |

---

### 1.10 SRL Persistence (Both Frameworks)

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `_merge_frame` | `SRLProcessor` | `SRLProcessor.py` | Create/merge `Frame` node with `framework`, `sense`, `confidence` | frame data dict | `:Frame` node |
| `_merge_frame_argument` | `SRLProcessor` | `SRLProcessor.py` | Create/merge `FrameArgument` node with canonical role | role data dict | `:FrameArgument` node |
| `_link_argument_to_frame` | `SRLProcessor` | `SRLProcessor.py` | Write `PARTICIPANT` edge with normalized role label | `Frame` id, `FrameArgument` id, role label | `:PARTICIPANT` edge with `raw_role` property |
| `_link_indices_to_node` | `SRLProcessor` | `SRLProcessor.py` | Link `TagOccurrence` tokens to `Frame`/`FrameArgument` | token index range, node id | `:IN_FRAME` / `:IN_ARGUMENT` edges |
| `process_srl` | `SRLProcessor` | `SRLProcessor.py` | Orchestrate PropBank SRL frame persistence | spaCy `Token._.srl_frames`, `doc_id` | full SRL subgraph |

**Ordering constraint:** `TagOccurrence` nodes must exist; spaCy token extensions must be populated by `SemanticRoleLabel.__call__`.

---

### 1.11 Word Sense Disambiguation

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `replace_hyphens_to_underscores` | `WordSenseDisambiguator` | `WordSenseDisambiguator.py` | Preprocessing for WSD service | raw text | preprocessed text |
| `_call_amuse_wsd_api` | `WordSenseDisambiguator` | `WordSenseDisambiguator.py` | POST to AMuSE-WSD service (port 81) | sentence collection | WSD JSON response |
| `_update_tokens_in_neo4j` | `WordSenseDisambiguator` | `WordSenseDisambiguator.py` | Write BabelNet/WordNet/NLTK synset IDs to `TagOccurrence` nodes | WSD result, `doc_id` | `synset_id`, `babelnet_id` properties on `:TagOccurrence` |
| `perform_wsd` | `WordSenseDisambiguator` | `WordSenseDisambiguator.py` | Top-level WSD driver | `doc_id`, text | synset annotations on tokens in Neo4j |

---

## Stage 2 — Refinement

**Module:** `src/textgraphx/pipeline/phases/refinement.py`  
**Input (reads from Neo4j):** `NamedEntity`, `CorefMention`, `Antecedent`, `Frame`, `FrameArgument`, `NounChunk`, `TagOccurrence`  
**Output (writes to Neo4j):** head properties on all mention nodes; `EVENT_PARTICIPANT` / `REFERS_TO` edges; `EntityMention`, `EventMention` nodes; enriched `TagOccurrence` properties

---

### 2.1 Head Assignment (16 methods, `RULE_FAMILIES["head_assignment"]`)

All methods follow the same pattern: read mention spans from Neo4j; look up the `IS_DEPENDENT` head token; write `head_text` and `head_index` properties back.

| Function | Operates On | Notes |
|----------|-------------|-------|
| `get_and_assign_head_info_to_entity_multitoken` | multi-token `NamedEntity` | Uses dep-parse head lookup |
| `get_and_assign_head_info_to_entity_singletoken` | single-token `NamedEntity` | Self-assigns head |
| `get_and_assign_head_info_to_antecedent_multitoken` | multi-token `Antecedent` | |
| `get_and_assign_head_info_to_antecedent_singletoken` | single-token `Antecedent` | |
| `get_and_assign_head_info_to_corefmention_multitoken` | multi-token `CorefMention` | |
| `get_and_assign_head_info_to_corefmention_singletoken` | single-token `CorefMention` | |
| `get_and_assign_head_info_to_all_frameArgument_multitoken` | all multi-token `FrameArgument` | |
| `get_and_assign_head_info_to_all_frameArgument_singletoken` | all single-token `FrameArgument` | |
| `get_and_assign_head_info_to_temporal_frameArgument_multitoken` | temporal-type `FrameArgument` | Temporal ArgM-TMP |
| `get_and_assign_head_info_to_temporal_frameArgument_singletoken` | temporal-type `FrameArgument` | |
| `get_and_assign_head_info_to_eventive_frameArgument_multitoken` | eventive-type `FrameArgument` | Eventive ArgM-PRD |
| `get_and_assign_head_info_to_eventive_frameArgument_singletoken` | eventive-type `FrameArgument` | |

**Ordering constraint:** `IS_DEPENDENT` edges must exist (from Ingestion §1.2). These 12+ methods are **mutually independent** within this family — they can run in parallel.

---

### 2.2 Frame–Entity Linking (12+ methods, `RULE_FAMILIES["linking"]`)

All methods create `REFERS_TO` or `EVENT_PARTICIPANT` edges between `FrameArgument` nodes and canonical `Entity` / `NamedEntity` nodes.

| Function | Linking Strategy | Prerequisite |
|----------|-----------------|-------------|
| `link_frameArgument_to_namedEntity_for_nam_nom` | Head-text match for NAM/NOM types | Head assignment done |
| `link_frameArgument_to_namedEntity_for_pobj` | Prepositional-object dependency | Head assignment done |
| `link_frameArgument_to_namedEntity_for_pro` | Pronominal via coref cluster | Coreference resolution done |
| `link_frameArgument_to_new_entity` | Creates new `Entity` for unresolved args | All other linking done |
| `link_frameArgument_to_numeric_entities` | Numeric VALUE matches | Head assignment done |
| `link_antecedent_to_namedEntity` | Antecedent head-text → `NamedEntity` | Head assignment done |
| `link_frameArgument_to_entity_via_named_entity` | Indirect chain through `NamedEntity → Entity` | `NamedEntity → Entity` REFERS_TO chain exists |

---

### 2.3 Mention Materialization

| Function | Class | Purpose | Key Input | Key Output |
|----------|-------|---------|-----------|------------|
| `materialize_nominal_mentions_from_frame_arguments` | `RefinementPhase` | Create `EntityMention` from nominal frame args | `FrameArgument` nodes | `:EntityMention` nodes |
| `materialize_nominal_mentions_from_noun_chunks` | `RefinementPhase` | Create `EntityMention` from noun chunks | `NounChunk` nodes | `:EntityMention` nodes |
| `materialize_predicate_nominal_mentions` | `RefinementPhase` | Materialize nominalized predicates as `EventMention` candidates | nominal `FrameArgument` | `:EventMention` candidate nodes |
| `materialize_appositive_mentions` | `RefinementPhase` | Create `EntityMention` for appositive constructions | dep-parse appositive edges | `:EntityMention` nodes |
| `promote_nominal_events` | `RefinementPhase` | Promote nominal mentions → `EventMention` when eventive | `EntityMention` candidates | `:EventMention` nodes |
| `assign_meantime_syntactic_types` | `RefinementPhase` | Assign MEANTIME syntactic types to entity mentions | mention nodes | `syntactic_type` property set |
| `detect_quantified_entities_from_frameArgument` | `RefinementPhase` | Detect quantified entity args | `FrameArgument` nodes | `quantified=true` property on args |

---

### 2.4 WordNet Semantic Enrichment

| Function | Class | Purpose | Key Input | Key Output |
|----------|-------|---------|-----------|------------|
| `assign_synset_info_to_tokens` | `WordnetTokenEnricher` | Top-level enrichment driver | `TagOccurrence` nodes with `synset_id` | hypernyms, synonyms, depth, domain written to tokens |
| `get_all_hypernyms` | `WordnetTokenEnricher` | Recursively get all hypernyms | WordNet `Synset` | list of hypernym strings |
| `get_synonyms` | `WordnetTokenEnricher` | Extract synonyms from synset | WordNet `Synset` | list of synonym strings |
| `get_domain_labels` | `WordnetTokenEnricher` | Extract domain from lexname | WordNet `Synset` | domain label string |
| `get_derivational_features` | `WordnetTokenEnricher` | Extract derivational forms + eventive verbs | WordNet `Synset` | derivation feature dict |
| `get_verb_relation_features` | `WordnetTokenEnricher` | Extract entailment + causal verb relations | WordNet `Synset` | verb relation feature dict |
| `get_depth_features` | `WordnetTokenEnricher` | Compute min/max depth + abstraction score | WordNet `Synset` | depth feature dict |
| `_lemma_similarity` | `WordnetTokenEnricher` | Cheap lexical lemma similarity | two lemma strings | similarity float |
| `_normalize_lemma` | `WordnetTokenEnricher` | Lowercase + underscore normalize | lemma string | normalized lemma |

**Ordering constraint:** WSD (`perform_wsd`) must run before `assign_synset_info_to_tokens` because WordNet enrichment requires `synset_id` to be present on `TagOccurrence` nodes.

---

### 2.5 SRL Role Normalization

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `normalize_propbank_role` | `SRLRoleNormalizer` | `srl_normalizer.py` | Convert `ARG0..ARG5` → canonical semantic role names | PropBank role string | canonical role string |
| `normalize_framenet_role` | `SRLRoleNormalizer` | `srl_normalizer.py` | Normalize FrameNet frame element via PropBank mapping | frame name, FE name | canonical role string |
| `is_core_role` | `SRLRoleNormalizer` | `srl_normalizer.py` | Check if role is a core argument | role string | bool |
| `is_modifier_role` | `SRLRoleNormalizer` | `srl_normalizer.py` | Check if role is temporal/locative/manner modifier | role string | bool |
| `get_frame_roles` | `FrameNetAligner` | `srl_normalizer.py` | Retrieve role mapping for a FrameNet frame | frame name | role map dict |
| `validate_frame_role_structure` | `FrameNetAligner` | `srl_normalizer.py` | Validate observed roles match FrameNet expectations | frame name, role list | bool + error list |
| `suggest_framenet_frame` | `FrameNetAligner` | `srl_normalizer.py` | Suggest best FrameNet frame given predicate + roles | predicate lemma, role list | FrameNet frame name |
| `validate_role_structure` | `SRLRoleContract` | `srl_normalizer.py` | Validate role structure against contract requirements | role dict | validation result |
| `normalize_srl_annotation` | `srl_normalizer` module | `srl_normalizer.py` | Normalize full SRL annotation: frame + roles + confidence | raw SRL annotation dict | canonical annotation dict |

---

### 2.6 Entity Disambiguation

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `disambiguate_entities` | `EntityDisambiguator` | `EntityDisambiguator.py` | Build entity graph: KB-linked vs. unresolved entities | `NamedEntity` nodes, `doc_id` | `:Entity` canonical nodes; `:REFERS_TO` edges |

---

## Stage 3 — Temporal Extraction

**Module:** `src/textgraphx/pipeline/phases/temporal.py` + `adapters/rest_caller.py`  
**Input (reads from Neo4j):** `AnnotatedText` (text + DCT)  
**Output (writes to Neo4j):** `TIMEX`, `TimexMention`, `Signal`, `CSignal` nodes; `TEvent` nodes; `TLINK` draft edges

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `get_annotated_text` | `TemporalPhase` | `temporal.py` | Retrieve all `AnnotatedText` document ids | Neo4j | list of `doc_id` strings |
| `get_doc_text_and_dct` | `TemporalPhase` | `temporal.py` | Retrieve document text + document creation time | `doc_id` | `(text, dct)` tuple |
| `callHeidelTimeService` | `rest_caller` | `rest_caller.py` | POST text to HeidelTime tagger (port 5000) | document text, DCT | TimeML-annotated XML string |
| `callTtkService` | `TemporalPhase` | `temporal.py` | POST text to TTK TimeML service (port 5050) | document text | TimeML TTK XML string |
| `materialize_signals` | `TemporalPhase` | `temporal.py` | Create `Signal`/`CSignal` nodes with token-span grounding | parsed TimeML data | `:Signal`, `:CSignal` nodes |

**Note:** `callHeidelTimeService` and `callTtkService` are **independent** — they can fire in parallel. Both write to the same `TIMEX` pool which is merged by the phase.

---

## Stage 4 — Event Enrichment

**Module:** `src/textgraphx/pipeline/phases/event_enrichment.py`  
**Input (reads from Neo4j):** `Frame`, `TEvent`, `NamedEntity`, `Entity`  
**Output (writes to Neo4j):** `EventMention` nodes; `FRAME_DESCRIBES_EVENT` / `DESCRIBES` edges; `INSTANTIATES` edges; `EVENT_PARTICIPANT` edges

| Function | Class | File | Purpose | Key Input | Key Output |
|----------|-------|------|---------|-----------|------------|
| `_describe_frame_and_role` | `EventEnrichmentPhase` | `event_enrichment.py` | Write `FRAME_DESCRIBES_EVENT` edge with event attributes (tense/aspect/polarity) | `Frame` id, `TEvent` id, event attributes | `:FRAME_DESCRIBES_EVENT` edge |
| `_participant_source_subquery` | `EventEnrichmentPhase` | `event_enrichment.py` | Generate Cypher subquery for resolving participant sources | — | Cypher subquery string |
| `materialize_event_mentions` | `EventEnrichmentPhase` | `event_enrichment.py` | Create `EventMention` nodes linked via `REFERS_TO → TEvent` | `Frame` data, `doc_id` | `:EventMention` nodes; `:REFERS_TO` edges |
| `attach_frames_to_event_mentions` | `EventEnrichmentPhase` | `event_enrichment.py` | Write `INSTANTIATES` edges from `Frame` to `EventMention` | matched Frame+EventMention pairs | `:INSTANTIATES` edges |

---

## Stage 5 — TLINK Recognition

**Module:** `src/textgraphx/pipeline/phases/tlinks_recognizer.py`  
**Input (reads from Neo4j):** `TEvent`, `TIMEX`, `Signal`, `CSignal`, `TagOccurrence` (dep-parse)  
**Output (writes to Neo4j):** `:TLINK` edges with `relType` and `confidence` properties

| Function | Class | File | Case Pattern | Key Input | Key Output |
|----------|-------|------|-------------|-----------|------------|
| `create_tlinks_case1` | `TlinksRecognizer` | `tlinks_recognizer.py` | `AFTER` via temporal modifiers with "after" signal | `Signal` node, eventive `FrameArgument` | `:TLINK{relType:"AFTER"}` |
| `create_tlinks_case2` | `TlinksRecognizer` | `tlinks_recognizer.py` | TLINK via gerund temporal complements with signal | gerund `TEvent`, `Signal` | `:TLINK` with signal-specific type |
| `create_tlinks_case3` | `TlinksRecognizer` | `tlinks_recognizer.py` | TLINK via gerund head temporal arguments | gerund `TEvent`, temporal arg | `:TLINK` |
| `create_tlinks_case4` | `TlinksRecognizer` | `tlinks_recognizer.py` | Event → `TIMEX` via temporal noun heads | `TEvent`, `TimexMention`, dep head | `:TLINK` |
| `create_tlinks_case5` | `TlinksRecognizer` | `tlinks_recognizer.py` | Event → `TIMEX` via preposition + signal type | `TEvent`, `TIMEX`, `Signal`, prep token | `:TLINK` with signal-mapped type |
| `create_tlinks_case6` | `TlinksRecognizer` | `tlinks_recognizer.py` | Event → DCT (document creation time) anchor | `TEvent`, `AnnotatedText.dct` | `:TLINK{relType:"IS_INCLUDED"}` |
| `get_annotated_text` | `TlinksRecognizer` | `tlinks_recognizer.py` | Retrieve all `AnnotatedText` document ids | Neo4j | list of `doc_id` strings |
| `_run_query` | `TlinksRecognizer` | `tlinks_recognizer.py` | Execute Cypher query with logging + error handling | Cypher string, params | Neo4j result cursor |

**All six TLINK cases are mutually independent and can run in parallel per document.**

---

## Cross-Stage Reasoning

**Module:** `src/textgraphx/reasoning/fusion.py`, `srl_normalizer.py`  
**Stage:** Runs after Stage 2 (entity fusion) and after Stage 5 (event fusion).

| Function | Module | Purpose | Key Input | Key Output |
|----------|--------|---------|-----------|------------|
| `fuse_entities_cross_sentence` | `fusion.py` | Create `CO_OCCURS_WITH` edges for entities in nearby sentences | `Entity` nodes, sentence proximity | `:CO_OCCURS_WITH` edges |
| `fuse_entities_cross_document` | `fusion.py` | Create `SAME_AS` edges for entities sharing `kb_id` across documents | `Entity` nodes with `kb_id` | `:SAME_AS` edges |
| `propagate_coreference_identity_cross_document` | `fusion.py` | Create `SAME_AS` via normalized coreference mention heads | `Antecedent` head text across documents | `:SAME_AS` edges |

**All three are mutually independent and can run in parallel.**

---

## REST API Adapters

**Module:** `src/textgraphx/adapters/rest_caller.py`

| Function | Service | Port | Protocol | Circuit Breaker | Caching |
|----------|---------|------|----------|----------------|---------|
| `callAllenNlpApi` | transformer-srl | 8010 | POST `/predict` | Yes | Yes (`_srl_cache`) |
| `callAllenNlpApiBatch` | transformer-srl | 8010 | POST `/predict` (concurrent httpx) | Yes | Yes |
| `callNominalSrlApi` | CogComp nominal-SRL | 8011 | POST `/predict_nom` | Yes | Yes |
| `callNominalSrlApiBatch` | CogComp nominal-SRL | 8011 | POST `/predict_nom` (concurrent httpx) | Yes | Yes |
| `callHeidelTimeService` | HeidelTime | 5000 | POST | No | No |
| `amuse_wsd_api_call` | AMuSE-WSD | 81 | POST | Yes | No |
| `amuse_wsd_api_call2` | AMuSE-WSD | 81 | POST | No | No |
| `_detect_legacy_srl_schema` | — | — | Internal | — | — |
| `_async_batch_srl` | transformer-srl or CogComp | 8010/8011 | async httpx | Yes | Yes |
| `_async_post_one` | any | any | async httpx | No | No |

---

## Summary Statistics

| Category | Function Count |
|----------|---------------|
| Tokenization / Morphology | 3 |
| Dependency Parsing | 3 |
| NER | 11 |
| Syntactic Chunking | 3 |
| Entity Fusion | 5 |
| Entity Linking (Entity-Fishing) | 9 |
| Coreference Resolution | 7 |
| PropBank SRL — Verbal | 6 |
| NomBank SRL — Nominal | 4 |
| SRL Persistence | 5 |
| Word Sense Disambiguation | 4 |
| WordNet Semantic Enrichment | 9 |
| SRL Role Normalization | 9 |
| Entity Disambiguation | 1 |
| Temporal Extraction | 5 |
| Event Enrichment | 4 |
| TLINK Recognition | 8 |
| Cross-Stage Entity Fusion | 3 |
| REST Adapters | 10 |
| Head Assignment (Refinement) | 12 |
| Frame–Entity Linking (Refinement) | 7 |
| Mention Materialization (Refinement) | 7 |
| **Total** | **~155** |

---

## What Is Missing

The following NLP capabilities are **absent** from the current codebase. They represent gaps between the current system and the situational-awareness target state defined in [MASTER_ARCHITECTURE_PLAN.md](MASTER_ARCHITECTURE_PLAN.md):

| Missing Capability | Required For | Recommended Approach |
|-------------------|-------------|---------------------|
| PDTB connective extractor | Explicit causal/discourse links | T1: lexical trigger list → T2: PDTB classifier |
| RST parser + EDU segmenter | Rhetorical structure, event salience | T2: DMRST or SciDTB model |
| Within-document event coreference | Unified event timelines | T2: ECB+ or WEC model |
| Cross-document event linker (`fuse_events_cross_document`) | Multi-doc situational awareness | T1: lemma+type match → T2: embedding sim |
| Document-level relation extraction (DocRE) | Cross-sentence relations | T2: DocRED-trained model |
| Script/event-chain induction | Endsley Level 3 projection | T2: SGNN or LLaMA narrative chain model |
| Stance/attribution classifier | Source reliability modeling | T1: "said/reported" lexical verbs + T2 |
| Factuality scorer | Distinguishing asserted vs hedged events | T2: FactBank-trained model |
