# TextGraphX Schema

This document describes the actual Neo4j graph schema implemented by the project as of the current codebase. It is intentionally based on the write paths in the Python code, not only on the conceptual ontology files.

Scope:

- Persisted node labels written by ingestion, refinement, temporal, event-enrichment, relation-extraction, fusion, and audit code.
- Persisted relationship types and their observed endpoint patterns.
- Properties actually set in code.
- Dynamic labels and schema drift that are easy to miss if you read only the ontology.

This is therefore an implementation schema, not a purely conceptual ontology.

See also: [schema-evolution-plan.md](./schema-evolution-plan.md), which turns the schema findings into a staged implementation and migration plan.

## Canonical Source Hierarchy

When schema statements disagree, use this precedence order:

1. Runtime write paths in code (`GraphBasedNLP.py`, `RefinementPhase.py`, `TemporalPhase.py`, `EventEnrichmentPhase.py`, `TlinksRecognizer.py`).
2. Applied migrations in `schema/migrations/`.
3. This document (`docs/schema.md`) as the maintained contract.
4. Ontology metadata (`schema/ontology.json`) as machine-readable policy and vocabulary.
5. Architecture and historical docs as explanatory context.

Practical rule:

- If code writes an edge/label/property and this file does not mention it, the schema is incomplete and this file must be updated.
- If this file mentions an edge/label/property that no code or migration writes, treat it as deprecated or planned until proven active.

## Governance Mode (Balanced)

This repository uses a balanced governance model.

Hard-contract scope (must pass):

- Identity keys and key type consistency (`doc_id`, node identifiers, composite natural keys).
- Referential integrity for canonical chains (`EntityMention -> REFERS_TO -> Entity`, `EventMention -> REFERS_TO -> TEvent`, `TimexMention -> REFERS_TO -> TIMEX`, `Frame -> INSTANTIATES -> EventMention`).
- Required core fields for canonical labels (`AnnotatedText`, `TagOccurrence`, `NamedEntity`, `Entity`, `TimexMention`, `TIMEX`, `TEvent`, `EventMention`, `Frame`, `FrameArgument`).
- Span integrity (`start_tok <= end_tok`, token/char fields consistent when both exist).

Runtime enforcement note:

- Phase assertions and diagnostics now track hard-contract violations for missing canonical mention/event chains and missing identity fields on span-bearing mention nodes.
- CI should treat endpoint drift, referential-chain breaks, and missing token/doc-span identity as hard failures once dataset baselines are locked.

Advisory-contract scope (warn, do not block by default):

- Enrichment profile completeness (`nominalSemantic*`, confidence/source metadata).
- Optional provenance coverage on non-critical inferred edges.
- Transitional dual-edge usage ratios (`PARTICIPANT` vs `EVENT_PARTICIPANT`, `DESCRIBES` vs `FRAME_DESCRIBES_EVENT`).

Legacy policy:

- Preserve legacy labels and relationships while canonical aliases are active.
- Removal must happen only through an explicit migration and coordinated query updates.

## Reasoning Contracts (Canonical)

The ontology includes explicit machine-readable reasoning contracts that should be treated as canonical for advanced temporal/event reasoning.

### Relation endpoint contract

`schema/ontology.json.relation_endpoint_contract` defines allowed source/target type pairs for high-impact relationships (`EVENT_PARTICIPANT`, `REFERS_TO`, `HAS_LEMMA`, `INSTANTIATES`, `TLINK`).

Practical use:

- Writers must not emit endpoints outside the allowed sets.
- Query authors can rely on endpoint typing guarantees instead of broad defensive label checks.
- CI tests should fail on endpoint drift in canonical relationships.

### Event attribute vocabulary

`schema/ontology.json.event_attribute_vocabulary` defines normalized values for event-centric fields (`tense`, `aspect`, `polarity`, `certainty`, modality defaults).

Practical use:

- Normalize extraction outputs to this vocabulary before write when possible.
- Treat out-of-vocabulary values as quality defects (hard for canonical fields, advisory for enrichment-only fields).

### Temporal reasoning profile

`schema/ontology.json.temporal_reasoning_profile` defines canonical TLINK relations, contradiction pairs, closure rules, and conflict-consistency policy.

Practical use:

- TLINK normalization and conflict suppression logic should follow this profile.
- Evaluation and phase assertions should reference this profile for consistency checks.

## 1. Schema Layers

The graph has five practical layers:

1. Document and token layer: `AnnotatedText`, `Sentence`, `TagOccurrence`, `Tag`.
2. Mention and semantic layer: `NamedEntity`, `Entity`, `Frame`, `FrameArgument`, `NounChunk`, `Antecedent`, `CorefMention`.
3. Temporal and event layer: `TimexMention`, `TIMEX`, `TEvent`, `EventMention`, `Signal`.
4. Relation and fusion layer: `Evidence`, `Relationship`, plus inferred edges such as `CO_OCCURS_WITH` and `SAME_AS`.
5. Operational audit layer: `PhaseRun`, `RefinementRun`.

There is also one legacy or optional content label that still has a write path:

- `Keyword`

## Canonical, Optional, and Legacy Tiers

The maintained schema contract is tiered so contributors can distinguish what is stable from what is additive or legacy.

### Canonical tier (maintained semantic core)

Node labels:

- `AnnotatedText`
- `Sentence`
- `TagOccurrence`
- `EntityMention`
- `NamedEntity`
- `Entity`
- `Frame`
- `FrameArgument`
- `TimexMention`
- `EventMention`
- `Signal`
- `Antecedent`
- `CorefMention`
- `TIMEX`
- `TEvent`
- `VALUE` *(canonical VALUE node type from `materialize_canonical_value_nodes()` — distinct from the deprecated `:VALUE` dynamic label on `NamedEntity` nodes)*

Relationship types:

- `CONTAINS_SENTENCE`
- `HAS_TOKEN`
- `HAS_NEXT`
- `IS_DEPENDENT`
- `IN_FRAME`
- `IN_MENTION`
- `HAS_FRAME_ARGUMENT`
- `REFERS_TO`
- `HAS_LEMMA`
- `PARTICIPANT`
- `EVENT_PARTICIPANT`
- `TRIGGERS`
- `DESCRIBES`
- `FRAME_DESCRIBES_EVENT`
- `KEYWORD_DESCRIBES_DOCUMENT`
- `INSTANTIATES`
- `CREATED_ON`
- `TLINK`
- `CLINK`
- `SLINK`
- `COREF`

### Optional tier (supported but not guaranteed every run)

Node labels:

- `PhaseRun`
- `RefinementRun`

Relationship types:

- `CO_OCCURS_WITH`
- `SAME_AS`

### Legacy tier (present for compatibility or targeted use)

Node labels:

- `Keyword`
- `Evidence`
- `Relationship`

Relationship types:

- `PARTICIPATES_IN`
- `IS_RELATED_TO`
- `SOURCE`
- `DESTINATION`
- `HAS_EVIDENCE`
- `FROM`
- `TO`

## Span Coordinate Contract

Milestone 1 introduces a dual-coordinate contract for span-bearing semantic nodes.

Canonical fields:

- token offsets: `start_tok`, `end_tok`
- character offsets: `start_char`, `end_char`

Transition policy:

- legacy fields remain available during migration
- compatibility mapping is documented in ontology metadata (`span_contract.legacy_aliases`)
- new and migrated workflows should query canonical fields first

## 2. Node Labels

### 2.1 Core document and token nodes

| Label | Role | Properties | Notes |
| --- | --- | --- | --- |
| `AnnotatedText` | Root document node | `id`: stable document id. `text`: raw document text. `author`: document author. `creationtime`: source creation timestamp. `filename`: source file name. `filetype`: source file type. `title`: source title. `publicId`: public identifier from NAF/XML header. `uri`: source URI. | Created by `MeantimeXMLImporter` in `text_processing_components/DocumentImporter.py`. |
| `Sentence` | Sentence container under a document | `id`: deterministic sentence id, usually `<doc>_<sentence_index>`. `text`: sentence surface text. | Created by `SentenceCreator.create_sentence_node()`. |
| `TagOccurrence` | Token node used as the main anchor for downstream linking | `id`: deterministic token id. `index`: character start offset. `end_index`: character end offset. `text`: token text. `lemma`: token lemma. `pos`: detailed POS tag. `upos`: universal POS tag. `tok_index_doc`: token index within the document. `tok_index_sent`: token index within the sentence. `is_stop`: stop/punct/space flag. Additional morphology properties: every key from `token.morph` may be written as a separate property when `TagOccurrenceCreator.create_tag_occurrences()` is used. | Stored via `TagOccurrenceQueryExecutor`, populated from `TagOccurrenceCreator`. The morphology properties are dynamic and depend on spaCy output. |
| `Tag` | Lemma grouping node | `id`: lemma string. | Only created when the `store_tag` branch is used in `TagOccurrenceQueryExecutor.get_tag_occurrence_query(True)`. |

### 2.2 Mention, entity, SRL, and coreference nodes

| Label | Role | Properties | Notes |
| --- | --- | --- | --- |
| `EntityMention` | Surface mention layer for entity-like spans | `uid`: source-namespaced stable uid used as the merge key for refinement-materialized nominal mentions. Current write paths derive it from document id + mention source namespace + anchor token index + normalized surface text. `id`: stable mention id. `doc_id`: owning document id. `value`: surface text. `head`: surface head token text. `headTokenIndex`: surface head token index. `syntacticType` / `syntactic_type`: coarse mention class. `start_tok`, `end_tok`, `start_char`, `end_char`: canonical span coordinates. Additive nominal-semantic fields may also be present, including `nominalSemanticHead*`, `nominalHeadWnLexname`, `nominalEvalProfile`, and `nominalSemanticSignals`. | Explicitly introduced by migrations and actively written by refinement for nominal mentions. During transition/backfill flows, some `NamedEntity` nodes may also carry the `EntityMention` label. |
| `NamedEntity` | Surface entity mention | `uid`: head-anchored stable uid used as the merge key (derived from document id + normalized surface text + anchor token index, typically `headTokenIndex`). `id`: legacy span/type id (`<doc>_<start>_<end>_<type>`) retained for compatibility. `legacy_span_id`: compatibility copy of legacy `id`. `type`: NER label. `value`: mention text. `index`: token start index. `end_index`: token end index. `kb_id`: external KB id when disambiguated. `url_wikidata`: copied KB URI. `score`: linker similarity score. `normal_term`: normalized label text. `description`: linker-provided description or surface form. `token_id`: token-based stable id for migration-safe joins. `token_start`: token start index. `token_end`: token end index. `head`: resolved head token text. `headTokenIndex`: head token index in document. `syntacticType`: coarse syntactic category such as `NAM`, `NOMINAL`, `PRO`. `spacyType`: previous NER type retained during NEL correction. | Base node created by `EntityProcessor` and `EntityExtractor`. Several properties are added later by refinement and correction passes. |
| `Entity` | Canonical or synthesized entity abstraction | `id`: canonical id or synthetic id from mention text. `type`: semantic or syntactic class. `kb_id`: stable identity used for disambiguated entities. `syntacticType`: syntactic category for synthetic entities. `head`: head text. `headTokenIndex`: head token index. Nominal backing entities may additionally carry `nominalSemanticHead*`, `nominalHeadWnLexname`, and other additive nominal profile fields inherited from mention-level refinement. | Created by `EntityDisambiguator`, refinement fallback rules, quantified-entity detection, and prepositional complement entity creation. |
| `NounChunk` | Noun phrase span | `id`: deterministic noun chunk id. `type`: chunk type, defaulting to `NOUN_CHUNK`. `value`: noun chunk surface text. `index`: start token index. | Created by `NounChunkProcessor`. |
| `Frame` | Predicate frame from SRL | `id`: deterministic frame id, usually `frame_<doc>_<start>_<end>`. `headword`: predicate head text. `headTokenIndex`: predicate head token index. `text`: frame span text. `startIndex`: start token index. `endIndex`: end token index. `framework`: sense inventory the frame is anchored in -- `PROPBANK` (default, verb SRL) or `NOMBANK` (nominal SRL via the optional CogComp service). `sense` *(optional, advisory)*: PropBank or NomBank roleset id such as `run.02` or `acquisition.01`, set when the upstream SRL service emits a roleset prediction. `sense_conf` *(optional, advisory)*: float confidence in `[0, 1]` for `sense`. | Created by `SRLProcessor._merge_frame()`. The `sense` and `sense_conf` properties are advisory-tier per §5.5; absence is not a contract violation. |
| `FrameArgument` | SRL argument span | `id`: deterministic argument id, usually `fa_<doc>_<start>_<end>_<argtype>`. `head`: resolved argument head text. `headTokenIndex`: head token index. `type`: PropBank role, for example `ARG0` or `ARGM-TMP`. `text`: argument surface text. `startIndex`: start token index. `endIndex`: end token index. `syntacticType`: syntactic class such as `NAM`, `NOMINAL`, `PRO`, `EVENTIVE`, `IN`. `signal`: temporal or prepositional signal text. `complement`: complement head text. `complementIndex`: complement token index. `complementFullText`: full complement span text. `argumentType`: normalized non-core semantic type such as `Locative` or `CauseClauses`. | Base node created by `SRLProcessor._merge_frame_argument()`. Many enrichment properties are added later by refinement and event-enrichment phases. |
| `Signal` | Temporal trigger span from TTK output | `id`: TTK signal id when available, else deterministic fallback. `doc_id`: owning document id. `type`: currently `SIGNAL`. `text`: signal surface text. `start_tok`: first token index. `end_tok`: last token index. `start_char`: character start offset. `end_char`: character end offset. | Created by `TemporalPhase.materialize_signals()`. Tokens are anchored with `TRIGGERS` just like `TimexMention` and `TEvent`. |
| `Antecedent` | Coreference cluster head | `uid`: canonical boundary-tolerant uid derived from document id + node type + normalized surface text + deterministic token anchor. `id`: legacy deterministic cluster-head span id. `text`: antecedent span text. `startIndex`: start token index. `endIndex`: end token index. `head`: resolved head text. `headTokenIndex`: resolved head token index. `syntacticType`: coarse syntactic category. | Created by `CoreferenceResolver.create_node()`, then enriched in refinement. |
| `CorefMention` | Coreference mention | `uid`: canonical boundary-tolerant uid derived from document id + node type + normalized surface text + deterministic token anchor. When an exact-span `NamedEntity` is reused as the mention node, its existing `NamedEntity.uid` is preserved. `id`: legacy deterministic mention span id. `text`: mention span text. `startIndex`: start token index. `endIndex`: end token index. `head`: resolved head text. `headTokenIndex`: resolved head token index. `syntacticType`: coarse syntactic category. | Created by `CoreferenceResolver.create_node()`, then enriched in refinement. |

### 2.3 Temporal and event nodes

| Label | Role | Properties | Notes |
| --- | --- | --- | --- |
| `TimexMention` | Mention-level temporal span | `id`: stable mention id, currently `timexmention_<doc>_<tid-or-span>`. `doc_id`: owning document id. `tid`: source-local temporal id when available. `text`: surface text span. `type`: mention-local timex type copied from the extractor. `start_tok`, `end_tok`, `start_char`, `end_char`: canonical span coordinates. `start_index`, `end_index`, `begin`, `end`: extractor-specific span aliases retained when a specific path provides them. | Created by `TemporalPhase.materialize_timexes()` and fallback materialization paths. Tokens anchor to `TimexMention` through `TRIGGERS`, and each mention projects to canonical `TIMEX` through `REFERS_TO`. |
| `TIMEX` | Canonical temporal abstraction | `tid`: temporal id within a document. `doc_id`: owning document id. `type`: TIMEX type such as `DATE`, `TIME`, `DURATION`. `value`: normalized temporal value. `quant`: quantifier from HeidelTime, default `N/A`. `origin`: extraction source, commonly `text2graph` or XML-provided origin. `functionInDocument`: `CREATION_TIME` for DCT or `NONE` otherwise. `anchorTimeID`, `beginPoint`, `endPoint`: normalized TimeML linkage metadata when present. Legacy span/text properties may remain on older nodes during transition, but new write paths treat span anchoring as mention-layer state on `TimexMention`. | Created by `TemporalPhase.create_DCT_node()`, `TemporalPhase.materialize_timexes()`, and `TemporalPhase.materialize_timexes_fallback()`. The document creation time node is also just a `TIMEX`. |
| `TEvent` | Temporalized event node | `eiid`: event instance id. `doc_id`: owning document id. `begin`: event begin token index or offset. `end`: event end token index or offset. `aspect`: temporal aspect. `class`: event class. `epos`: event POS from TTK output. `form`: event surface form. `pos`: event POS. `tense`: event tense. `modality`: modal surface value from TTK when present. `polarity`: event polarity from TTK when present. | Created by `TemporalPhase.materialize_tevents()`. |
| `EventMention` | Mention-level event instantiation | `id`: stable mention id, currently derived from `TEvent.eiid`. `doc_id`: owning document id. `pred`: mention-level predicate text. `tense`, `aspect`, `pos`, `epos`, `form`, `modality`, `polarity`, `class`: copied or normalized temporal/event attributes. `start_tok`, `end_tok`, `start_char`, `end_char`, `begin`, `end`: mention span coordinates. `token_id`: token-based stable id for migration-safe joins. `token_start`: token start index. `token_end`: token end index. | Created by `EventEnrichmentPhase.create_event_mentions()`. Each `EventMention` links to a canonical `TEvent` through `REFERS_TO`; `TemporalPhase` does not create these nodes. |

### 2.4 Relation, keyword, and audit nodes

| Label | Role | Properties | Notes |
| --- | --- | --- | --- |
| `Evidence` | Mention-level evidence for extracted relations | `id`: derived from the internal Neo4j id of an `IS_RELATED_TO` relationship. `type`: relation type copied from `IS_RELATED_TO.type`. | Created only if `TextProcessor.build_relationships_inferred_graph()` is executed. This is a live but legacy relation-extraction path. |
| `Relationship` | Higher-level relation abstraction between canonical entities | `id`: derived from the internal Neo4j id of an `IS_RELATED_TO` relationship. `type`: relation type copied from `IS_RELATED_TO.type`. | Created only by `TextProcessor.build_relationships_inferred_graph()`. |
| `Keyword` | Keyword node attached to a document | `id`: keyword lemma id. `NE`: optional named-entity type attached to the keyword. `index`: keyword start offset. `endIndex`: keyword end offset. | Created by `TextProcessor.store_keywords()` during TextRank-based keyword extraction. Links to documents via `-[:KEYWORD_DESCRIBES_DOCUMENT {rank}]->` edges. |
| `VALUE` | Canonical value-expression node for numeric, monetary, and quantity mentions | `id`: copied from source `NamedEntity.id`. `doc_id`: owning document id. `type`: value type from a controlled vocabulary — one of `PERCENT`, `MONEY`, `QUANTITY`, `CARDINAL`, `ORDINAL`, `DATE`, `DURATION`, `NUMERIC`, `OTHER`. `value`: surface text copied from `NamedEntity.value` or `NamedEntity.text`. `value_normalized`: lowercased surface form for matching. `start_tok`, `end_tok`, `start_char`, `end_char`: canonical span coordinates. `source`: materialization source tag, currently `named_entity_value`. | Created by `RefinementPhase.materialize_canonical_value_nodes()`. Natural key is `(doc_id, id)`. Source `NamedEntity` mentions link to `VALUE` via `REFERS_TO`; `FrameArgument` nodes that already resolve through such a mention chain receive a shortcut `REFERS_TO -> VALUE` edge. Canonical `EVENT_PARTICIPANT` edges are propagated so `VALUE` nodes appear as first-class participant sources in reasoning queries. Distinct from the deprecated `:VALUE` dynamic label that was applied to selected `NamedEntity` nodes; those are removed by migration 0019. |
| `PhaseRun` | Generic phase audit marker | `id`: timestamp-based run id. `phase`: canonical phase name. `timestamp`: ISO timestamp. `duration_seconds`: phase duration. `documents_processed`: processed document count. `meta_*`: arbitrary metadata stored as flattened prefixed properties. | Created by `phase_assertions.record_phase_run()` and used by ingestion, temporal, event-enrichment, and TLINK phases. |
| `RefinementRun` | Refinement-specific audit marker | `id`: timestamp-based run id. `timestamp`: ISO timestamp. `passes`: ordered list of refinement passes that ran. | Created at the end of `RefinementPhase.__main__`. |

## 3. Dynamic and Derived Labels

Some schema elements are not separate base node types. They are additional labels assigned at runtime.

### 3.1 Additional labels on `NamedEntity`

> **Deprecation notice**: These dynamic labels are **write-suppressed** (controlled by `fill_numeric_labels=False`, the current default in `RefinementPhase`). No new `:NUMERIC` or `:VALUE` labels are written. Migration 0019 (operator-triggered) removes remaining instances from existing graphs. Readers must not add new logic that depends on these labels.

| Label | Applied to | Status | Meaning |
| --- | --- | --- | --- |
| `NUMERIC` | `NamedEntity` nodes whose `type` is in `['MONEY', 'QUANTITY', 'PERCENT']` | **Deprecated** — write-suppressed, removal via migration 0019 | Marks mentions treated as numeric values in refinement and event enrichment. Existing read-side code uses it only as a legacy fallback. Do not write new queries against this label. |
| `VALUE` (dynamic label) | `NamedEntity` nodes whose `type` is in `['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']` | **Transitional** — write-suppressed, removal via migration 0019 | Secondary label applied to `NamedEntity` nodes. **Distinct from** the canonical `VALUE` *node type* created by `RefinementPhase.materialize_canonical_value_nodes()`. Query the canonical `:VALUE` node type, not this label. |

Important note: `NUMERIC` is not created as a separate standalone node family. It is an extra label on selected `NamedEntity` nodes. The canonical `VALUE` *node* (not this dynamic label) is a distinct, maintained node type persisted by `materialize_canonical_value_nodes()`.

Transition note:

- Event-enrichment participant-source resolution now prefers canonical `Entity` and `VALUE` node targets and only falls back to legacy `NamedEntity:NUMERIC|VALUE` label matches for compatibility.
- New query logic must not add new reads against `NamedEntity:NUMERIC|VALUE` dynamic labels.
- Refinement paths that apply direct `:NUMERIC` and temporary `:VALUE` labels now emit deprecation warnings, and runtime diagnostics expose `numeric_value_transition_inventory` so migration progress can be tracked without changing current write behavior.

### 3.2 FrameArgument argumentType property (formerly dynamic labels)

`EventEnrichmentPhase.add_non_core_participants_to_event()` sets `FrameArgument.argumentType` to a normalized semantic category. This property is the canonical representation of non-core semantic roles.

Canonical argumentType values (from ontology.json):

- `Comitative` (ARGM-COM)
- `Locative` (ARGM-LOC)
- `Directional` (ARGM-DIR)
- `Goal` (ARGM-GOL)
- `Manner` (ARGM-MNR)
- `Temporal` (ARGM-TMP) — *note: excluded from event enrichment per section 8 caveat*
- `Extent` (ARGM-EXT)
- `Reciprocals` (ARGM-REC)
- `SecondaryPredication` (ARGM-PRD)
- `PurposeClauses` (ARGM-PRP)
- `CauseClauses` (ARGM-CAU)
- `Discourse` (ARGM-DIS)
- `Modals` (ARGM-MOD)
- `Negation` (ARGM-NEG)
- `DirectSpeech` (ARGM-DSP)
- `Adverbials` (ARGM-ADV)
- `Adjectival` (ARGM-ADJ)
- `LightVerb` (ARGM-LVB)
- `Construction` (ARGM-CXN)
- `NonCore` (fallback for unknown ARGM types)

**Historical note**: Prior to April 2026, these values were also duplicated as extra node labels via APOC (`add_label_to_non_core_fa()`). Since no query logic or evaluation code relied on label filtering, the dynamic label application was deprecated as redundant overhead. All semantic queries should use the `argumentType` property directly.

### 3.3 Additional labels on `EntityMention`

| Label | Applied to | Meaning |
| --- | --- | --- |
| `NominalMention` | `EntityMention` nodes materialized from nominal frame arguments and noun chunks | Marks mention-level nominals that remain distinct from canonical entities and from NER-only mention nodes. |
| `DiscourseEntity` | `EntityMention` or `NamedEntity` nodes selected by refinement salience rules | Provides an additive discourse/evaluation view without deleting graph evidence. |

## 4. Relationship Types

Several relationship types are overloaded across different subgraphs. The tables below list the actual observed endpoint patterns.

### 4.1 Structural relationships

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `CONTAINS_SENTENCE` | `AnnotatedText -> Sentence` | none | Canonical document-to-sentence containment edge. |
| `HAS_TOKEN` | `Sentence -> TagOccurrence` | none | Canonical sentence-to-token edge. |
| `HAS_NEXT` | `TagOccurrence -> TagOccurrence` | `sentence`: sentence id | Orders adjacent tokens inside a sentence. |
| `IS_DEPENDENT` | `TagOccurrence -> TagOccurrence` | `type`: dependency label such as `nsubj`, `dobj`, `pobj`, `prep`, `mark`, `pcomp` | Dependency parse edge used heavily in refinement. |
| `PARTICIPATES_IN` | `TagOccurrence -> NamedEntity` | none | Token belongs to a named entity mention. |
| `PARTICIPATES_IN` | `TagOccurrence -> EntityMention` | none | Token belongs to an explicit mention node, including refinement-generated nominal mentions. |
| `PARTICIPATES_IN` | `TagOccurrence -> Frame` | none | Token belongs to a predicate frame. |
| `PARTICIPATES_IN` | `TagOccurrence -> FrameArgument` | none | Token belongs to an SRL argument span. |
| `PARTICIPATES_IN` | `TagOccurrence -> Antecedent` | none | Token belongs to a coreference antecedent. |
| `PARTICIPATES_IN` | `TagOccurrence -> CorefMention` | none | Token belongs to a coreference mention. |
| `PARTICIPATES_IN` | `TagOccurrence -> NounChunk` | none | Token belongs to a noun chunk. |
| `PARTICIPATES_IN` | `TagOccurrence -> Entity` | none | Used in refinement when a synthetic `Entity` is created from complement or quantified-entity logic. |

`PARTICIPATES_IN` governance status:

- Legacy transitional edge family.
- New read paths must not use `PARTICIPATES_IN` as their primary traversal when `IN_FRAME` or `IN_MENTION` expresses the same intent.
- Writers may continue to dual-write it only while split-edge migration support is required.

Canonical split-participation relationships (written alongside `PARTICIPATES_IN` during transition):

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `IN_FRAME` | `TagOccurrence -> Frame` | none | Token belongs to a predicate frame. Canonical replacement for `PARTICIPATES_IN` targeting `Frame` nodes. |
| `IN_FRAME` | `TagOccurrence -> FrameArgument` | none | Token belongs to an SRL argument span. Canonical replacement for `PARTICIPATES_IN` targeting `FrameArgument` nodes. |
| `IN_MENTION` | `TagOccurrence -> NamedEntity` | none | Token belongs to a named entity mention. Canonical replacement for `PARTICIPATES_IN` targeting `NamedEntity` nodes. |
| `IN_MENTION` | `TagOccurrence -> EntityMention` | none | Token belongs to an explicit mention node. Canonical replacement for `PARTICIPATES_IN` targeting `EntityMention` nodes. |
| `IN_MENTION` | `TagOccurrence -> Antecedent` | none | Token belongs to a coreference antecedent. Canonical replacement for `PARTICIPATES_IN` targeting `Antecedent` nodes. |
| `IN_MENTION` | `TagOccurrence -> CorefMention` | none | Token belongs to a coreference mention. Canonical replacement for `PARTICIPATES_IN` targeting `CorefMention` nodes. |
| `IN_MENTION` | `TagOccurrence -> NounChunk` | none | Token belongs to a noun chunk. Canonical replacement for `PARTICIPATES_IN` targeting `NounChunk` nodes. |

Write coverage for `IN_FRAME`/`IN_MENTION`: see section 5.5 writer status table.

### 4.2 Lexical, mention, and entity relationships

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `HAS_LEMMA` | `TagOccurrence -> Tag` | none | Optional lemma grouping edge for non-stop tokens. |
| `REFERS_TO` | `EntityMention -> Entity` | none | Explicit mention-to-canonical link used by refinement-generated nominal mentions and by the maintained mention layer. |
| `REFERS_TO` | `EventMention -> TEvent` | none | Mention-to-canonical event link created by `EventEnrichmentPhase.create_event_mentions()`. |
| `REFERS_TO` | `TimexMention -> TIMEX` | none | Mention-to-canonical temporal link created by `TemporalPhase` materialization. |
| `REFERS_TO` | `NamedEntity -> Entity` | `type`: usually `evoke` | Canonical link from a surface mention to an entity abstraction. |
| `REFERS_TO` | `FrameArgument -> NamedEntity` | none | Refinement link from an argument span to a matched mention. |
| `REFERS_TO` | `FrameArgument -> Entity` | none | Flattened or fallback link from an argument span to a canonical or synthetic entity. Some refinement queries use undirected `MERGE`, so treat this as semantically bidirectional in old data. |
| `REFERS_TO` | `FrameArgument -> NUMERIC` | none | Argument linked directly to a numeric-labeled `NamedEntity`. |
| `REFERS_TO` | `NamedEntity -> VALUE` | none | Source mention link from a value-typed `NamedEntity` to the canonical `VALUE` node materialized by `RefinementPhase.materialize_canonical_value_nodes()`. |
| `REFERS_TO` | `FrameArgument -> VALUE` | none | Argument-level shortcut to a canonical `VALUE` node created when the argument already resolves through a `NamedEntity -> VALUE` chain. Materialized by the same method during propagation. |
| `REFERS_TO` | `Antecedent -> NamedEntity` | none | Lets antecedents inherit authoritative entity mention identity. |
| `COREF` | `CorefMention -> Antecedent` | none | Coreference link from mention to antecedent. |
| `IS_RELATED_TO` | `NamedEntity -> NamedEntity` | `root`: trigger lemma. `type`: extracted relation type. | Mention-level extracted relation created by legacy rule-based relation extraction. |
| `SOURCE` | `Evidence -> NamedEntity` | none | Evidence source mention in the relation-evidence subgraph. |
| `DESTINATION` | `Evidence -> NamedEntity` | none | Evidence destination mention in the relation-evidence subgraph. |
| `HAS_EVIDENCE` | `Relationship -> Evidence` | none | Attaches relation abstraction to evidence node. |
| `FROM` | `Relationship -> Entity` | none | Source canonical entity in relation abstraction. |
| `TO` | `Relationship -> Entity` | none | Destination canonical entity in relation abstraction. |

### 4.3 SRL, event, and temporal relationships

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `PARTICIPANT` | `FrameArgument -> Frame` | `type`: SRL role such as `ARG0`, `ARGM-TMP` | Canonical SRL membership edge. |
| `HAS_FRAME_ARGUMENT` | `FrameArgument -> Frame` | none | Canonical relationship used by newer write paths and query contracts to represent frame membership alongside legacy `PARTICIPANT`. |
| `DESCRIBES` | `Frame -> TEvent` | none | Links a frame to a temporal event it describes. |
| `FRAME_DESCRIBES_EVENT` | `Frame -> TEvent` | none | Canonical event-description edge written alongside `DESCRIBES` for backward-compatible transition support. |
| `INSTANTIATES` | `Frame -> EventMention` | none | Links a frame to the mention-level event instantiation after `EventMention` creation. |
| `ALIGNS_WITH` | `Frame (PROPBANK) -> Frame (NOMBANK)` | `alignment_key`: deterministic order-independent key derived from the two frame IDs. `confidence`: geometric mean of `sense_conf` values when both are available, otherwise the available value. | Optional-tier cross-framework alignment edge. Created by `srl_frame_aligner.run_cross_framework_alignment()` when a PROPBANK and a NOMBANK Frame share the same headword lemma and their head token indices are within `TOKEN_WINDOW=5`. Downstream phases may consume but must not require this edge. |
| `PARTICIPANT` | `Entity -> TEvent` | `type`: copied from `FrameArgument.type`. `prep`: preposition when the argument is prepositional. | Event participant edge created for core roles in `EventEnrichmentPhase`. |
| `PARTICIPANT` | `Entity -> EventMention` | `type`: copied from `FrameArgument.type`. `prep`: preposition when the argument is prepositional. | Mention-level participant edge retained for compatibility alongside `EVENT_PARTICIPANT`. |
| `PARTICIPANT` | `NUMERIC -> TEvent` | `type`: copied from `FrameArgument.type`. `prep`: optional preposition. | Numeric participant edge in event enrichment. |
| `PARTICIPANT` | `NUMERIC -> EventMention` | `type`: copied from `FrameArgument.type`. `prep`: optional preposition. | Mention-level numeric participant edge retained for compatibility alongside `EVENT_PARTICIPANT`. |
| `PARTICIPANT` | `FrameArgument -> TEvent` | `type`: original non-core argument type. `prep`: optional preposition. | Transitional non-core participant shortcut from an argument span directly to a canonical event. Retained for compatibility only; reasoning-grade reads should prefer mention-mediated or entity/value-mediated participant chains. |
| `EVENT_PARTICIPANT` | `Entity|NUMERIC|FrameArgument -> TEvent|EventMention` | `type`: copied from frame-argument role. `prep`: optional preposition for prepositional arguments. | Canonical participant edge family during the current dual-write period. `FrameArgument -> TEvent|EventMention` remains transitional and should not be treated as a stable reasoning contract. |
| `EVENT_PARTICIPANT` | `VALUE -> TEvent|EventMention` | `type`: copied from the `FrameArgument.type` that sourced the chain. `prep`: preposition head when the argument was prepositional. `roleFrame`: provenance tag, currently `PROPBANK`. `confidence`: propagated or defaulted to `1.0`. | Propagated participant edge from canonical value nodes. Created by `RefinementPhase.materialize_canonical_value_nodes()` when a `FrameArgument` that already holds a `PARTICIPANT|EVENT_PARTICIPANT` edge to an event is also resolved to a `VALUE`. Allows value-bearing participants to appear as first-class event arguments in reasoning queries without requiring `NamedEntity` label checks. |

Participant provenance note:

- Event-enrichment participant writes now stamp provenance fields at creation time on both `PARTICIPANT` and `EVENT_PARTICIPANT` edges (`confidence`, `evidence_source`, `rule_id`, `authority_tier`, `source_kind`, `conflict_policy`, `created_at`).
- Core participant writes use `rule_id=participant_linking_core` with confidence `0.65`; non-core writes use `rule_id=participant_linking_non_core` with confidence `0.60`.
| `TRIGGERS` | `TagOccurrence -> TimexMention` | none | Token or token span anchors a temporal mention node. |
| `TRIGGERS` | `TagOccurrence -> TIMEX` | none | Legacy direct anchor to canonical temporal node. Existing data may still contain it, but new writes should anchor tokens to `TimexMention` instead. |
| `TRIGGERS` | `TagOccurrence -> TEvent` | none | Token triggers a temporal event node. |
| `TRIGGERS` | `TagOccurrence -> Signal` | none | Token or token span anchors a temporal signal node. |
| `CREATED_ON` | `AnnotatedText -> TIMEX` | none | Connects a document to its DCT temporal node. |
| `TLINK` | `TEvent -> TEvent` | `id`: TLINK id from TARSQI XML when available. `relType`: temporal relation such as `BEFORE`, `AFTER`, `SIMULTANEOUS`. `signalID`: temporal signal id from TTK when available. `source`: heuristic source such as `t2g` when produced by `TlinksRecognizer`. | Event-to-event temporal relation. |
| `TLINK` | `TEvent -> TIMEX` | `id`, `relType`, `signalID`, `source` | Event-to-time temporal relation. |
| `TLINK` | `TIMEX -> TIMEX` | `id`, `relType`, `signalID`, `source` | Time-to-time temporal relation. |
| `CLINK` | `TEvent -> TEvent` | `source`: currently `srl_argm_cau` | Derived causal relation from `ARGM-CAU` frame arguments during event enrichment. |
| `SLINK` | `TEvent -> TEvent` | `source`: currently `srl_argm_dsp` | Derived subordinating relation from `ARGM-DSP` frame arguments during event enrichment. |
| `HAS_TIME_ANCHOR` | `TEvent -> TimexMention:SRLTimexCandidate` | `source`: `'srl_argm_tmp_anchor'`. `confidence`: `1.0`. `created_at`: ISO timestamp. | Temporal anchor edge written by `temporal.anchor_srl_timex_candidates_to_events()` (Step 10) when an `ARGM-TMP` SRL argument resolves to a `TimexMention` with `SRLTimexCandidate` label and the target TIMEX has `merged=false` and `is_timeml_core=true`. TLINK case 11 (`create_tlinks_case11`) follows this edge to produce an `IS_INCLUDED` TLINK. Optional-tier for queries; canonical write path in Stage 3 (Temporal). |

TLINK anchor-consistency note:

- TLINK hardening now annotates anchor metadata (`sourceAnchorType`, `targetAnchorType`, `anchorPair`, `anchorConsistency`, `anchorConsistencyReason`) for every TLINK.
- In non-shadow mode, inconsistent TLINKs (self-links or endpoint-contract violations) are retained but marked suppressed by `tlink_anchor_consistency_filter`.
- Runtime diagnostics expose this state via `tlink_anchor_consistency_inventory` so anchor inconsistencies and anchor-filter suppressions can be tracked in CI and evaluation payloads.

Recommended CI gate thresholds (starting point):

- `tlink_anchor_inconsistent_count`: allow no increase versus baseline (`--max-tlink-anchor-inconsistent-increase 0`).
- `tlink_missing_anchor_metadata_count`: require full metadata coverage (`--max-tlink-missing-anchor-metadata 0`).
- `participation_in_frame_missing_count`: allow no increase and target zero missing aliases (`--max-participation-in-frame-missing-increase 0`, `--max-participation-in-frame-missing 0`).
- `participation_in_mention_missing_count`: allow no increase and target zero missing aliases (`--max-participation-in-mention-missing-increase 0`, `--max-participation-in-mention-missing 0`).
- Keep overall quality tolerance explicit (`--tolerance <value>`) so quality drift and temporal-anchor regressions are both enforced.

### 4.4 Fusion and keyword relationships

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `CO_OCCURS_WITH` | `Entity -> Entity` | `confidence`: confidence score. `evidence_source`: rule family or phase. `rule_id`: specific rule identifier. `created_at`: creation timestamp. | Cross-sentence fusion edge for nearby entity co-occurrence. |
| `SAME_AS` | `Entity -> Entity` | `confidence`: confidence score. `evidence_source`: rule family or phase. `rule_id`: specific rule identifier. `created_at`: creation timestamp. | Cross-document identity fusion for entities sharing stable KB identity. |
| `KEYWORD_DESCRIBES_DOCUMENT` | `Keyword -> AnnotatedText` | `rank`: keyword rank score | Keyword-to-document metadata edge. Separated from `Frame -> TEvent` to keep DESCRIBES semantically pure (event description only). |

### 4.5 Transitional relationship policy

Some relationship families are intentionally dual-written during the current schema-alignment period so that maintained query paths and older graph consumers can coexist.

| Legacy relationship | Canonical/current relationship | Current write policy |
| --- | --- | --- |
| `PARTICIPANT` (`FrameArgument -> Frame`) | `HAS_FRAME_ARGUMENT` | Queries should tolerate both; newer query contracts prefer `HAS_FRAME_ARGUMENT|PARTICIPANT`. |
| `DESCRIBES` (`Frame -> TEvent`) | `FRAME_DESCRIBES_EVENT` | `EventEnrichmentPhase.link_frameArgument_to_event()` writes both edges intentionally. |
| `PARTICIPANT` (event participant edges) | `EVENT_PARTICIPANT` | Core and non-core participant enrichment write both edges for compatibility while newer consumers can prefer `EVENT_PARTICIPANT`. |
| `PARTICIPATES_IN` (`TagOccurrence -> heterogeneous mention/frame targets`) | `IN_FRAME` and `IN_MENTION` | Runtime writes still dual-write for compatibility, but read-side governance treats `PARTICIPATES_IN` as legacy. |

This dual-write strategy is intentional. It should be removed only as part of an explicit migration with coordinated query updates; it is not redundant drift.

### 4.6 Hard read policy for split participation and temporal mentions

Reasoning-grade and newly authored query paths must follow these rules:

- Use `IN_FRAME` for `TagOccurrence -> Frame|FrameArgument` traversals.
- Use `IN_MENTION` for `TagOccurrence -> NamedEntity|EntityMention|Antecedent|CorefMention|NounChunk` traversals.
- Treat `PARTICIPATES_IN` as fallback-only for compatibility scans, migrations, and legacy readers.
- Use `TagOccurrence -> TRIGGERS -> TimexMention -> REFERS_TO -> TIMEX` for temporal mention-to-canonical traversal.
- Do not anchor new temporal reads directly on `TagOccurrence -> TRIGGERS -> TIMEX` unless the query is explicitly a legacy-compatibility path.
- Do not treat `FrameArgument -> TEvent|EventMention` participant edges as the primary reasoning topology; prefer entity/value-backed or mention-mediated participant chains.

### 5.5 Participation edge split migration (`IN_FRAME`, `IN_MENTION`)

To reduce `PARTICIPATES_IN` overloading during transition, runtime writes now dual-write:

- `TagOccurrence -> IN_FRAME -> Frame|FrameArgument`
- `TagOccurrence -> IN_MENTION -> NamedEntity|EntityMention|CorefMention|Antecedent`

Compatibility policy:

- Existing readers may continue to include `PARTICIPATES_IN` during transition.
- New or migrated readers should prefer `IN_FRAME` and `IN_MENTION` first.
- Any new production reasoning or evaluation query should justify continued `PARTICIPATES_IN` usage explicitly in code review.

Backfill helper for existing databases:

- `python -m textgraphx.tools.migrate_participation_edges --dry-run`
- `python -m textgraphx.tools.migrate_participation_edges --apply`

The helper creates missing `IN_FRAME`/`IN_MENTION` edges from current
`PARTICIPATES_IN` edges in batches and reports before/after missing counts.

### Writer implementation status

| Writer | `IN_FRAME` | `IN_MENTION` | Notes |
| --- | --- | --- | --- |
| `EntityProcessor.store_entities()` | n/a | ✅ done | Dual-writes `PARTICIPATES_IN` + `IN_MENTION` |
| `EntityExtractor` (create path) | n/a | ✅ done | Dual-writes `PARTICIPATES_IN` + `IN_MENTION` |
| `SRLProcessor._merge_frame()` / `_merge_frame_argument()` | ✅ done | n/a | Dual-writes `PARTICIPATES_IN` + `IN_FRAME` |
| `NounChunkProcessor` | n/a | ✅ done | Dual-writes `PARTICIPATES_IN` + `IN_MENTION` (Phase 2 fix applied) |
| `CoreferenceResolver.connect_node_to_tag_occurrences()` | n/a | ✅ done | Dual-writes `PARTICIPATES_IN` + `IN_MENTION` (Phase 2 fix applied) |

### 5.6 Temporal mention parity (`TimexMention`)

Temporal writes now maintain mention-to-canonical parity analogous to `EntityMention` and `EventMention`:

- `TagOccurrence -> TRIGGERS -> TimexMention`
- `TimexMention -> REFERS_TO -> TIMEX`

Governance implications:

- `TimexMention` is the surface-bearing temporal node.
- `TIMEX` is the canonical normalized temporal abstraction used for reasoning and TLINK endpoints.
- New write paths should not attach fresh `TRIGGERS` edges directly to canonical `TIMEX` nodes.
- DCT remains a metadata `TIMEX` attached via `AnnotatedText -[:CREATED_ON]-> TIMEX`; it is exempt from mention-layer parity because it does not originate from in-text tokens.
- Older `TRIGGERS -> TIMEX` edges remain readable during transition and migration.

### 5.7 VALUE mention-layer roadmap decision

Current canonical design intentionally uses direct value normalization:

- `NamedEntity -[:REFERS_TO]-> VALUE`
- Optional propagated participant links from `VALUE` to `TEvent|EventMention`

Design decision:

- `ValueMention` parity is explicitly deferred by design for the current milestones.
- This avoids introducing an additional mention layer before current VALUE quality gates and migration baselines are stabilized.
- Any future `ValueMention` introduction must be treated as a migration-backed architecture change (not an incremental refactor), with explicit dual-write and read-policy updates.

### Incremental Re-extraction Reconciliation (NamedEntity)

Residual risk addressed:

- Re-extracting a document with updated model boundaries can create new `NamedEntity.id` values (`<doc>_<start>_<end>_<type>`) while leaving older span IDs in the graph.

Current hardening behavior (implemented in both `EntityProcessor` and `EntityExtractor` write paths):

- Use stable uid MERGE behavior (`MERGE (ne:NamedEntity {uid: ...})`) while preserving legacy span-based `id` as compatibility metadata.
- After each document extraction batch, mark not-seen `NamedEntity` nodes as stale:
	- `stale = true`
	- `stale_reason = 'reextract_not_seen'`
	- `stale_run_id`, `stale_at`
- Retire mention participation edges from stale nodes:
	- delete `(:TagOccurrence)-[:PARTICIPATES_IN|IN_MENTION]->(:NamedEntity {stale:true})`
- Retire canonical entity links from stale nodes:
	- delete `(:NamedEntity {stale:true})-[:REFERS_TO]->(:Entity)`

Why this is low-disruption:

- No destructive node delete occurs in the default path.
- Legacy node IDs remain for audit/provenance inspection.
- Stale spans are removed from active mention-layer traversal, preventing duplicate span participation in downstream reads.
- Stale mention nodes no longer keep canonical `REFERS_TO` links, preventing stale alias pollution of canonical entity traversals.

Operational cleanup tool:

- `python -m textgraphx.tools.cleanup_stale_named_entities --dry-run`
	- reports stale node inventory and attached edge counts (`IN_MENTION|PARTICIPATES_IN`, `REFERS_TO`).
- `python -m textgraphx.tools.cleanup_stale_named_entities --apply`
	- retires stale mention and canonical edges in batches.
- Optional scoping flags: `--document-id`, `--stale-run-id`, `--older-than-ms`.
- Optional destructive mode: `--apply --detach-delete`
	- batch `DETACH DELETE` for stale `NamedEntity` nodes after edge retirement.

## 5. Identity Conventions

Stable identifiers are important because most writes are implemented with `MERGE`.

Observed conventions:

- `AnnotatedText.id`: importer-assigned document id.
- `Sentence.id`: `<doc>_<sentence_index>`.
- `TagOccurrence.id`: `<doc>_<sentence_id>_<token_char_offset>` in current token creation code.
- `NamedEntity.uid`: head-anchored stable uid (`ne_<doc>_<hash(doc|normalized_surface|anchor_token_index)>`). For the main writer, `anchor_token_index` is `headTokenIndex`; when an extractor cannot supply a semantic head, it must fall back to another deterministic token anchor rather than a trailing-span boundary.
- `NamedEntity.id`: legacy span/type id retained for compatibility: `<doc>_<start>_<end>_<type>`.
- `NamedEntity.token_id`: token-index-based deterministic id intended for migration-safe matching. Current writer format is type-agnostic: `<doc>_<start>_<end>` (implemented via `make_ne_token_id()`). This stays stable across NER type corrections, unlike `NamedEntity.id` (`<doc>_<start>_<end>_<type>`).
- `EntityMention.uid`: source-namespaced stable uid (`em_<doc>_<hash(doc|source|normalized_surface|anchor_token_index)>`) generated via `make_entity_mention_uid()`. Refinement nominal mention materializers now precompute this helper-derived key in Python before batched `MERGE` writes. Legacy `EntityMention.id` remains persisted for compatibility and traceability.
- `NounChunk.id`: `<doc>_<start>`.
- `Frame.id`: `frame_<doc>_<start>_<end>`.
- `FrameArgument.id`: `fa_<doc>_<start>_<end>_<argtype>`.
- `Antecedent.uid`: boundary-tolerant uid (`antecedent_<doc>_<hash(doc|node_type|normalized_surface|anchor_token_index)>`) generated via `make_coref_uid()`.
- `Antecedent.id`: legacy span id retained for compatibility: `Antecedent_<doc>_<start>_<end>`.
- `CorefMention.uid`: boundary-tolerant uid (`corefmention_<doc>_<hash(doc|node_type|normalized_surface|anchor_token_index)>`) generated via `make_coref_uid()`. If a `NamedEntity` is reused as an exact-span mention node, the existing `NamedEntity.uid` is preserved instead of being overwritten.
- `CorefMention.id`: legacy span id retained for compatibility: `CorefMention_<doc>_<start>_<end>`.
- `TIMEX`: natural key is effectively `(tid, doc_id)`.
- `TimexMention.id`: `timexmention_<doc_id>_<tid>` where `tid` is the temporal expression identifier from the TTK/HeidelTime extractor (e.g. `t1`, `t2`). Generated by `TemporalPhase._timex_mention_id(doc_id, tid)`. All three in-text write paths (`materialize_timexes`, `_materialize_timexes_from_heideltime`, `create_timexes2`) converge on this formula.
- `TEvent`: natural key is effectively `(eiid, doc_id)`.
- `EventMention.id`: `<eiid>_mention` — the owning `TEvent.eiid` suffixed with `_mention`. Generated inline in the Cypher of `EventEnrichmentPhase.create_event_mentions()`.
- `Signal.id`: copied from the TTK signal `sid` attribute when present; otherwise a deterministic fallback derived from `doc_id` and span offsets.
- `VALUE`: natural key is effectively `(doc_id, id)` where `id` is copied from the source `NamedEntity.id` (`<doc>_<start>_<end>_<type>`) at materialization time.
- `PhaseRun.id` and `RefinementRun.id`: ISO timestamp strings.

## 6. Constraints and Indexes

### 6.1 Constraints created in application code

`GraphBasedNLP.create_constraints()` declares node-key or uniqueness-style constraints for:

- `Tag(id)`
- `TagOccurrence(id)`
- `Sentence(id)`
- `AnnotatedText(id)`
- `NamedEntity(id)`
- `NamedEntity(uid)`
- `EntityMention(uid)`
- `Entity(type, id)`
- `Evidence(id)`
- `Relationship(id)`
- `NounChunk(id)`
- `TEvent(eiid, doc_id)`

### 6.2 Constraints and indexes in migrations

`schema/migrations/0001_create_constraints.cypher` adds:

- unique `Frame.id`
- unique `FrameArgument.id`
- unique `NamedEntity.id`
- unique `TagOccurrence.id`
- unique `AnnotatedText.id`
- index on `TagOccurrence.tok_index_doc`
- index on `NamedEntity.kb_id`

`schema/migrations/0002_create_namedentity_tokenid_constraint.cypher` adds:

- unique `NamedEntity.token_id`

`schema/migrations/0018_repair_ne_token_id.cypher` then transitions this contract:

- drops the unique `NamedEntity.token_id` constraint
- creates a non-unique index on `NamedEntity.token_id`
- backfills `NamedEntity.token_id` to type-agnostic format `<doc>_<start>_<end>`

`schema/migrations/0020_add_uid_constraints_for_mentions.cypher` adds:

- unique `NamedEntity.uid`
- unique `EntityMention.uid`
- index on `NamedEntity.uid`
- index on `EntityMention.uid`

`schema/migrations/0021_backfill_coref_uid.cypher` backfills:

- `Antecedent.uid` on all nodes that pre-date the UID-hardened `CoreferenceResolver`
- `CorefMention.uid` on standalone nodes (nodes that reused a `NamedEntity` already have
  uid from their `NamedEntity` creation path and are skipped by `WHERE n.uid IS NULL`)
- Uses `apoc.periodic.iterate` in batches of 500 to reproduce the same
  `make_coref_uid()` formula (doc_id, node_type.lower(), normalised surface, anchor token)
  as the Python write-path

`schema/migrations/0016_formalize_value_nodes_with_type_classification.cypher` adds:

- unique `(VALUE.doc_id, VALUE.id)` composite constraint (natural key)
- index on `VALUE.doc_id`
- index on `VALUE.type`
- index on `(VALUE.start_tok, VALUE.end_tok)`
- index on `VALUE.value`
- index on `()-[:REFERS_TO]->(v:VALUE)` relationship index
- index on `()-[r:EVENT_PARTICIPANT]->(v:VALUE)` relationship index

`schema/migrations/0022_add_coref_uid_constraints.cypher` adds:

- unique `Antecedent.uid`
- unique `CorefMention.uid`
- index on `Antecedent.uid`
- index on `CorefMention.uid`

`schema/migrations/0023_add_timexmention_constraints.cypher` adds:

- unique `TimexMention.id`
- index on `TimexMention.doc_id`
- index on `(TimexMention.doc_id, TimexMention.tid)`

This aligns database-level enforcement with the existing `_TIMEX_MENTION_QUERY` write contract.

**Prerequisite**: migration 0021 must be applied first so that all `Antecedent` and
`CorefMention` nodes have a non-NULL `uid`. Applying 0022 before 0021 on a graph with
NULL-uid nodes will fail the UNIQUE constraint.

Practical implication: the enforced schema depends on whether the app bootstrap path or the migrations path has been used. The migration path is currently more complete for `Frame` and `FrameArgument` uniqueness.

### 6.3 UID contract operator validation

The repository now includes an operator helper for validating the live UID contract around `NamedEntity.uid` and `EntityMention.uid`.

Primary helper:

- `python -m textgraphx.tools.uid_smoke_preflight --preflight-only`
- `python -m textgraphx.tools.uid_smoke_preflight --docs 112579,113219,113227 --run-smoke`
- `python -m textgraphx.tools.uid_smoke_preflight --docs 112579,113219,113227 --run-smoke --cleanup`

Convenience targets:

- `make uid-preflight`
- `make uid-smoke UID_DOCS=112579,113219,113227`

What the helper verifies:

- current UID uniqueness constraints on `NamedEntity` and `EntityMention`
- null or blank UID inventory for both labels
- duplicate UID group counts for both labels
- optional smoke-ingest behavior under live constraints
- optional cleanup of staged smoke documents and their graph writes

UID rollover semantics:

- `NamedEntity.uid` is intentionally stable across many span-boundary adjustments, but it is not immutable.
- The hash input is exactly: document id + normalized surface text + anchor token index.
- A UID is expected to change when normalized text changes or when the chosen anchor token index changes.
- Writers should prefer `headTokenIndex` as the anchor and use another deterministic token anchor only when no semantic head index is available from the extractor.

Operational note:

- In this workspace, ingestion smoke runs should use `.venv310` rather than the default `.venv`, because the default Python 3.13 environment is missing `_ctypes` and is not reliable for spaCy-backed pipeline runs.

## 7. Property Semantics Worth Knowing

These properties drive downstream behavior and are not just descriptive metadata:

- `head` and `headTokenIndex`: anchor mention-like nodes to a token for refinement joins.
- `nominalSemanticHead`, `nominalSemanticHeadLemma`, `nominalSemanticHeadTokenIndex`, `nominalSemanticHeadSource`: noun-preferred semantic-head profile for nominal mentions and their backing entities.
- `wnLexname` on `TagOccurrence`, and `nominalHeadWnLexname` on nominal mentions/entities: lexical-domain bridge used for additive WordNet-based semantic typing.
- `nominalEventiveByWordNet`, `nominalEventiveByTrigger`, `nominalEventiveByArgumentStructure`, `nominalEventiveByMorphology`, `nominalEventiveConfidence`: explicit multi-signal nominal-event profile for downstream KG reasoning and evaluator views.
- `nominalEvalProfile`, `nominalEvalLayerSuggestion`, `nominalEvalCandidateGold`, `nominalSemanticSignals`: additive evaluation and semantic-profile fields used to project narrower scorer views without deleting graph data.
- `syntacticType`: used to distinguish nominal, named, pronominal, eventive, and prepositional cases.
- `signal`, `complement`, `complementIndex`, `complementFullText`: used mainly by temporal and prepositional frame-argument logic.
- `argumentType`: normalized semantic class for non-core frame arguments.
- `tok_index_doc`: the most important token alignment field in the graph.
- `kb_id`: cross-document identity anchor for canonical entities and fusion.
- `confidence`, `evidence_source`, `rule_id`, `created_at`: provenance fields on inferred edges, especially `CO_OCCURS_WITH` and `SAME_AS`.
- `authority_tier`, `source_kind`, `conflict_policy`: normalized provenance-contract fields now stamped on inferred relationship families, including event participant edges.
- `relType`: semantic value of a `TLINK`.
- `sourceAnchorType`, `targetAnchorType`, `anchorPair`, `anchorConsistency`, `anchorConsistencyReason`: TLINK anchor-consistency metadata used for temporal diagnostics and suppression auditability.
- `prep`: stored on `PARTICIPANT` edges when a preposition or prepositional head should be preserved.
- `stale`, `stale_reason`, `stale_run_id`, `stale_at`, `last_seen_at`: incremental re-extraction lifecycle markers on `NamedEntity` nodes used to retire stale span participation without deleting historical nodes.

## 8. Schema Drift and Caveats

### Enhancement track: ENH-NOM-01 to ENH-NOM-03

The current nominal-semantic work follows three additive enhancements:

- `ENH-NOM-01`: semantic-head resolution for nominal mentions. Purpose: separate lexical meaning from surface parse-root behavior. Rationale: WordNet and downstream semantic typing are unreliable when modifiers are treated as heads.
- `ENH-NOM-02`: persistence of lexical-domain metadata (`TagOccurrence.wnLexname` and nominal rollups). Purpose: make nominal semantics queryable without recomputing WordNet interpretation. Rationale: lexnames are a cleaner coarse semantic signal than hypernym string matching alone.
- `ENH-NOM-03`: additive nominal semantic/evaluation profile fields. Purpose: preserve graph richness while allowing evaluation to project narrower views such as eventive or discourse-only nominals. Rationale: evaluation policy should be a view over the graph, not a destructive rewrite of the graph.

Current `ENH-NOM-03` evaluator profile modes:

- `all`: no additional nominal profile filter.
- `eventive`: keep only eventive nominals (profile and signal driven).
- `salient`: keep only discourse-salient nominals.
- `candidate-gold`: keep only nominals flagged as candidate gold-aligned mentions.
- `background`: keep only non-eventive background nominals.

These points are important if you are trying to reconcile the codebase, the ontology docs, and the live database.

1. `NUMERIC` and `VALUE` are dynamic labels on `NamedEntity`, not separate base node families.
	Event-enrichment reads now centralize this compatibility behavior and prefer canonical `Entity`/`VALUE` resolution before falling back to legacy labels.
	The same canonical-first compatibility rule now applies when event enrichment scores low-confidence events from participant support, so VALUE-backed participants count as structural evidence instead of being ignored.
2. `Keyword` nodes and `Keyword -[:KEYWORD_DESCRIBES_DOCUMENT {rank}]-> AnnotatedText` edges are persisted but not fully documented in the ontology files. Keywords are extracted via TextRank summarization and linked to documents for metadata/keyword extraction purposes.
3. **Dynamic label application deprecated**: Prior to April 2026, `EventEnrichmentPhase.add_label_to_non_core_fa()` stamped 20+ semantic category labels (Locative, Directional, etc.) on FrameArgument nodes using APOC. These labels were decorative—no query or evaluation logic filtered by them. The label application is now a no-op; use the `argumentType` property instead. This change reduces APOC overhead without functional impact.
4. `PARTICIPANT` is overloaded: it is used for `FrameArgument -> Frame`, `Entity/NUMERIC -> TEvent`, and `FrameArgument -> TEvent`. This overloading is intentional and controlled via the dual-write policy in section 4.5.
5. Historical drift resolved: `CONTAINS_SENTENCE` is the canonical document-to-sentence edge and `fusion.py` now uses `:CONTAINS_SENTENCE` (the stale `:CONTAINS` variant was removed and guarded by milestone contradiction tests).
6. `PhaseRun` is a real persisted audit label but is not represented in the ontology files.
7. `RefinementRun` is also persisted and omitted from the ontology files.
8. Historical drift resolved: `TlinksRecognizer` no longer reads `e.modal`; temporal/event writes and downstream logic consistently use `modality`.
9. `TIMEX` has two property shapes because the codebase contains both the newer HeidelTime path (`start_index`, `end_index`, `text`, `quant`) and an older XML path (`begin`, `end`).
10. `Signal` is currently implemented only for temporal `SIGNAL` spans from TTK. `CSignal` is still a planned schema element, not a persisted label yet.
11. Historical contradiction resolved: non-core participant enrichment excludes `ARGM-TMP`, and the unreachable `WHEN 'ARGM-TMP'` mapping has been removed from that branch.
12. Some refinement `REFERS_TO` merges use undirected patterns, so very old data may not be perfectly uniform in relationship direction even when the intended semantics are clear.
13. The nominal semantic-head profile is intentionally additive. `head` remains the original surface or parser-root head, while `nominalSemanticHead*` stores the noun-preferred head used for lexical reasoning and nominal-event analysis.
14. **DCT is metadata, not a mention**: `TemporalPhase.create_DCT_node()` creates a canonical `TIMEX` for the document creation time and links it through `AnnotatedText -[:CREATED_ON]-> TIMEX`. This is intentional because DCT originates from document header metadata, not from an in-text span. DCT is therefore exempt from `TagOccurrence -> TRIGGERS -> TimexMention` parity.
15. **`TimexMention.id` is now database-enforced**: Migration 0023 adds a uniqueness constraint on `TimexMention.id` and supporting indexes on `doc_id` and `(doc_id, tid)`.
16. **`VALUE` nodes are not yet tracked by `TimexMention`-style mention parity**: The current canonical schema uses direct `NamedEntity -[:REFERS_TO]-> VALUE` with no intermediate `ValueMention` layer. Migration 0016 notes this as a planned future extension (see its comment block). This is intentional for the current milestone and not a schema bug.

## 9. Recommended Canonical View

If you need one simplified schema view for downstream consumers, use this canonical interpretation:

- **Structural backbone**: `AnnotatedText -[:CONTAINS_SENTENCE]-> Sentence -[:HAS_TOKEN]-> TagOccurrence`.
- **Mention membership (canonical)**: `TagOccurrence -[:IN_MENTION]-> NamedEntity|EntityMention|Antecedent|CorefMention|NounChunk`. Use `PARTICIPATES_IN` only as a legacy fallback for compatibility reads.
- **Frame membership (canonical)**: `TagOccurrence -[:IN_FRAME]-> Frame|FrameArgument`. Use `PARTICIPATES_IN` only as a legacy fallback.
- **Entity normalization**: `NamedEntity|EntityMention -[:REFERS_TO]-> Entity`.
- **Value normalization**: `NamedEntity -[:REFERS_TO]-> VALUE` (canonical value abstraction for numeric, monetary, and quantity expressions).
- **Event normalization**: `TagOccurrence -[:TRIGGERS]-> TEvent`, then `Frame -[:FRAME_DESCRIBES_EVENT|DESCRIBES]-> TEvent`.
- **Temporal mention normalization**: `TagOccurrence -[:TRIGGERS]-> TimexMention -[:REFERS_TO]-> TIMEX`. Do not anchor new temporal reads directly at `TagOccurrence -> TRIGGERS -> TIMEX` unless writing a legacy-compatibility path.
- **Event mention normalization**: `EventMention -[:REFERS_TO]-> TEvent`, `Frame -[:INSTANTIATES]-> EventMention`.
- **Event participants**: `Entity|VALUE|FrameArgument -[:EVENT_PARTICIPANT|PARTICIPANT]-> TEvent|EventMention`. Prefer canonical chains (`Entity`/`VALUE` backed) over bare `FrameArgument -> TEvent` edges for reasoning-grade queries.
- **Coreference**: `CorefMention -[:COREF]-> Antecedent`.
- **Temporal relations**: `TLINK` edges among `TEvent` and `TIMEX` (TLINK endpoints are always canonical-tier nodes, not mention nodes).
- **Causal and subordination relations**: `CLINK` and `SLINK` among `TEvent`.
- **Fusion and provenance**: `CO_OCCURS_WITH`, `SAME_AS` on `Entity` nodes; `Evidence`/`Relationship` nodes where the legacy relation extraction path is used.

**Key policy differences from older descriptions**:
- `IN_FRAME`/`IN_MENTION` are canonical; `PARTICIPATES_IN` is legacy.
- `TimexMention` is the surface-bearing temporal node; `TIMEX` is the canonical reasoning node.
- `VALUE` is the canonical reasoning node for value expressions; `NamedEntity:VALUE` dynamic label is deprecated.
- Coreference chain uses `COREF`; mentions and antecedents are not directly traversed from the document root without going through the token layer.

That view matches the maintained pipeline more closely than the older conceptual ontology alone.

## 10. Function Authoring Playbook (LPG)

Use these rules when adding new text-processing functions that write Neo4j data.

### 10.1 Choose canonical write targets first

- Prefer canonical labels and relationships over legacy aliases.
- Keep dual-write only where transition policy explicitly requires it.
- Do not invent new labels/edge types when an existing canonical type already encodes the same semantics.

### 10.2 MERGE identity discipline

- MERGE only on deterministic identity keys.
- Set mutable properties with `SET` after identity is established.
- Do not include non-identity attributes in MERGE patterns.
- For temporal nodes, scope identities by document (`(tid, doc_id)` and `(eiid, doc_id)`).

### 10.3 Required minimum fields on create

Node creation must include at least:

- `AnnotatedText`: `id`
- `TagOccurrence`: `id`, `tok_index_doc`, `index`, `end_index`
- `NamedEntity`: `id`, `type`, span anchors (`index`/`end_index` or canonical equivalents)
- `Entity`: `id`, `type`
- `TIMEX`: `tid`, `doc_id`, `type`
- `TEvent`: `eiid`, `doc_id`
- `EventMention`: `id`, `doc_id`, `start_tok`, `end_tok`
- `Frame`: `id`
- `FrameArgument`: `id`, `type`

### 10.4 Canonical relationship obligations

When mention/event layers are present, preserve these chains:

- `EntityMention -[:REFERS_TO]-> Entity`
- `EventMention -[:REFERS_TO]-> TEvent`
- `Frame -[:INSTANTIATES]-> EventMention` when frame-event alignment exists

### 10.5 Span policy for new writes

- Write canonical token fields (`start_tok`, `end_tok`) whenever span semantics exist.
- Write character fields (`start_char`, `end_char`) when available from the extractor.
- Legacy span fields may be retained for compatibility, but new logic should query canonical fields first.

### 10.6 Provenance on inferred edges

For new inferred relationships, include provenance fields where possible:

- `confidence`
- `evidence_source`
- `rule_id`
- `created_at`

This is strongly recommended for all new inference logic and required for any rule used in evaluation reports.

## 11. Schema Drift Control

Before merging any schema-affecting change, verify all four checks:

1. The new/changed label or relationship appears in this file.
2. The write path exists in code or migration (not documentation-only).
3. Contract tests cover the new shape (hard-contract if canonical, advisory if optional).
4. Legacy-impact is explicit (preserved alias, migration path, or deprecation note).

Suggested CI gate policy:

- Fail if code introduces undocumented canonical labels/relationships/properties.
- Fail if runtime diagnostics report endpoint contract, referential integrity, or identity contract violations above the configured hard thresholds.
- Warn if advisory provenance/profile fields are missing.