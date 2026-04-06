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
- Referential integrity for canonical chains (`EntityMention -> REFERS_TO -> Entity`, `EventMention -> REFERS_TO -> TEvent`, `Frame -> INSTANTIATES -> EventMention`).
- Required core fields for canonical labels (`AnnotatedText`, `TagOccurrence`, `NamedEntity`, `Entity`, `TIMEX`, `TEvent`, `EventMention`, `Frame`, `FrameArgument`).
- Span integrity (`start_tok <= end_tok`, token/char fields consistent when both exist).

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

`schema/ontology.json.relation_endpoint_contract` defines allowed source/target type pairs for high-impact relationships (`EVENT_PARTICIPANT`, `REFERS_TO`, `INSTANTIATES`, `TLINK`).

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
3. Temporal and event layer: `TIMEX`, `TEvent`, `EventMention`, `Signal`.
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
- `EventMention`
- `Signal`
- `Antecedent`
- `CorefMention`
- `TIMEX`
- `TEvent`
- `VALUE`

Relationship types:

- `CONTAINS_SENTENCE`
- `HAS_TOKEN`
- `HAS_NEXT`
- `IS_DEPENDENT`
- `PARTICIPATES_IN`
- `HAS_FRAME_ARGUMENT`
- `REFERS_TO`
- `PARTICIPANT`
- `EVENT_PARTICIPANT`
- `TRIGGERS`
- `DESCRIBES`
- `FRAME_DESCRIBES_EVENT`
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
| `EntityMention` | Surface mention layer for entity-like spans | `id`: stable mention id. `doc_id`: owning document id. `value`: surface text. `head`: surface head token text. `headTokenIndex`: surface head token index. `syntacticType` / `syntactic_type`: coarse mention class. `start_tok`, `end_tok`, `start_char`, `end_char`: canonical span coordinates. Additive nominal-semantic fields may also be present, including `nominalSemanticHead*`, `nominalHeadWnLexname`, `nominalEvalProfile`, and `nominalSemanticSignals`. | Explicitly introduced by migrations and actively written by refinement for nominal mentions. During transition/backfill flows, some `NamedEntity` nodes may also carry the `EntityMention` label. |
| `NamedEntity` | Surface entity mention | `id`: deterministic mention id. `type`: NER label. `value`: mention text. `index`: token start index. `end_index`: token end index. `kb_id`: external KB id when disambiguated. `url_wikidata`: copied KB URI. `score`: linker similarity score. `normal_term`: normalized label text. `description`: linker-provided description or surface form. `token_id`: token-based stable id for migration-safe joins. `token_start`: token start index. `token_end`: token end index. `head`: resolved head token text. `headTokenIndex`: head token index in document. `syntacticType`: coarse syntactic category such as `NAM`, `NOMINAL`, `PRO`. `spacyType`: previous NER type retained during NEL correction. | Base node created by `EntityProcessor` and `EntityExtractor`. Several properties are added later by refinement and correction passes. |
| `Entity` | Canonical or synthesized entity abstraction | `id`: canonical id or synthetic id from mention text. `type`: semantic or syntactic class. `kb_id`: stable identity used for disambiguated entities. `syntacticType`: syntactic category for synthetic entities. `head`: head text. `headTokenIndex`: head token index. Nominal backing entities may additionally carry `nominalSemanticHead*`, `nominalHeadWnLexname`, and other additive nominal profile fields inherited from mention-level refinement. | Created by `EntityDisambiguator`, refinement fallback rules, quantified-entity detection, and prepositional complement entity creation. |
| `NounChunk` | Noun phrase span | `id`: deterministic noun chunk id. `type`: chunk type, defaulting to `NOUN_CHUNK`. `value`: noun chunk surface text. `index`: start token index. | Created by `NounChunkProcessor`. |
| `Frame` | Predicate frame from SRL | `id`: deterministic frame id, usually `frame_<doc>_<start>_<end>`. `headword`: predicate head text. `headTokenIndex`: predicate head token index. `text`: frame span text. `startIndex`: start token index. `endIndex`: end token index. | Created by `SRLProcessor._merge_frame()`. |
| `FrameArgument` | SRL argument span | `id`: deterministic argument id, usually `fa_<doc>_<start>_<end>_<argtype>`. `head`: resolved argument head text. `headTokenIndex`: head token index. `type`: PropBank role, for example `ARG0` or `ARGM-TMP`. `text`: argument surface text. `startIndex`: start token index. `endIndex`: end token index. `syntacticType`: syntactic class such as `NAM`, `NOMINAL`, `PRO`, `EVENTIVE`, `IN`. `signal`: temporal or prepositional signal text. `complement`: complement head text. `complementIndex`: complement token index. `complementFullText`: full complement span text. `argumentType`: normalized non-core semantic type such as `Locative` or `CauseClauses`. | Base node created by `SRLProcessor._merge_frame_argument()`. Many enrichment properties are added later by refinement and event-enrichment phases. |
| `Signal` | Temporal trigger span from TTK output | `id`: TTK signal id when available, else deterministic fallback. `doc_id`: owning document id. `type`: currently `SIGNAL`. `text`: signal surface text. `start_tok`: first token index. `end_tok`: last token index. `start_char`: character start offset. `end_char`: character end offset. | Created by `TemporalPhase.materialize_signals()`. Tokens are anchored with `TRIGGERS` just like `TIMEX` and `TEvent`. |
| `Antecedent` | Coreference cluster head | `id`: deterministic cluster-head id. `text`: antecedent span text. `startIndex`: start token index. `endIndex`: end token index. `head`: resolved head text. `headTokenIndex`: resolved head token index. `syntacticType`: coarse syntactic category. | Created by `CoreferenceResolver.create_node()`, then enriched in refinement. |
| `CorefMention` | Coreference mention | `id`: deterministic mention id. `text`: mention span text. `startIndex`: start token index. `endIndex`: end token index. `head`: resolved head text. `headTokenIndex`: resolved head token index. `syntacticType`: coarse syntactic category. | Created by `CoreferenceResolver.create_node()`, then enriched in refinement. |

### 2.3 Temporal and event nodes

| Label | Role | Properties | Notes |
| --- | --- | --- | --- |
| `TIMEX` | Temporal expression | `tid`: temporal id within a document. `doc_id`: owning document id. `type`: TIMEX type such as `DATE`, `TIME`, `DURATION`. `value`: normalized temporal value. `text`: surface text when available. `quant`: quantifier from HeidelTime, default `N/A`. `origin`: extraction source, commonly `text2graph` or XML-provided origin. `start_index`: token start index in the current HeidelTime path. `end_index`: token end index in the current HeidelTime path. `begin`: legacy start offset from the older XML path. `end`: legacy end offset from the older XML path. `functionInDocument`: `CREATION_TIME` for DCT or `NONE` otherwise. | Created by `TemporalPhase.create_DCT_node()`, `TemporalPhase.materialize_timexes()`, and `TemporalPhase.materialize_timexes_fallback()`. The document creation time node is also just a `TIMEX`. |
| `TEvent` | Temporalized event node | `eiid`: event instance id. `doc_id`: owning document id. `begin`: event begin token index or offset. `end`: event end token index or offset. `aspect`: temporal aspect. `class`: event class. `epos`: event POS from TTK output. `form`: event surface form. `pos`: event POS. `tense`: event tense. `modality`: modal surface value from TTK when present. `polarity`: event polarity from TTK when present. | Created by `TemporalPhase.materialize_tevents()`. |
| `EventMention` | Mention-level event instantiation | `id`: stable mention id, currently derived from `TEvent.eiid`. `doc_id`: owning document id. `pred`: mention-level predicate text. `tense`, `aspect`, `pos`, `epos`, `form`, `modality`, `polarity`, `class`: copied or normalized temporal/event attributes. `start_tok`, `end_tok`, `start_char`, `end_char`, `begin`, `end`: mention span coordinates. | Created by `EventEnrichmentPhase.create_event_mentions()`. Each `EventMention` links to a canonical `TEvent` through `REFERS_TO`; `TemporalPhase` does not create these nodes. |

### 2.4 Relation, keyword, and audit nodes

| Label | Role | Properties | Notes |
| --- | --- | --- | --- |
| `Evidence` | Mention-level evidence for extracted relations | `id`: derived from the internal Neo4j id of an `IS_RELATED_TO` relationship. `type`: relation type copied from `IS_RELATED_TO.type`. | Created only if `TextProcessor.build_relationships_inferred_graph()` is executed. This is a live but legacy relation-extraction path. |
| `Relationship` | Higher-level relation abstraction between canonical entities | `id`: derived from the internal Neo4j id of an `IS_RELATED_TO` relationship. `type`: relation type copied from `IS_RELATED_TO.type`. | Created only by `TextProcessor.build_relationships_inferred_graph()`. |
| `Keyword` | Keyword node attached to a document | `id`: keyword lemma id. `NE`: optional named-entity type attached to the keyword. `index`: keyword start offset. `endIndex`: keyword end offset. | Created by `TextProcessor.store_keywords()`. This label is not documented in the ontology files but still has an active write path. |
| `PhaseRun` | Generic phase audit marker | `id`: timestamp-based run id. `phase`: canonical phase name. `timestamp`: ISO timestamp. `duration_seconds`: phase duration. `documents_processed`: processed document count. `meta_*`: arbitrary metadata stored as flattened prefixed properties. | Created by `phase_assertions.record_phase_run()` and used by temporal, event-enrichment, and TLINK phases. |
| `RefinementRun` | Refinement-specific audit marker | `id`: timestamp-based run id. `timestamp`: ISO timestamp. `passes`: ordered list of refinement passes that ran. | Created at the end of `RefinementPhase.__main__`. |

## 3. Dynamic and Derived Labels

Some schema elements are not separate base node types. They are additional labels assigned at runtime.

### 3.1 Additional labels on `NamedEntity`

| Label | Applied to | Meaning |
| --- | --- | --- |
| `NUMERIC` | `NamedEntity` nodes whose `type` is in `['MONEY', 'QUANTITY', 'PERCENT']` | Marks mentions treated as numeric values in refinement and event enrichment. |
| `VALUE` | `NamedEntity` nodes whose `type` is in `['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']` | Broader value-like label used for quantity and measure logic. |

Important note: `NUMERIC` is not created as a separate standalone node family. It is an extra label on selected `NamedEntity` nodes.

### 3.2 Additional labels on `FrameArgument`

`EventEnrichmentPhase.add_non_core_participants_to_event()` sets `FrameArgument.argumentType`, then `add_label_to_non_core_fa()` applies that value as an extra label using APOC.

Observed dynamic labels include:

- `Comitative`
- `Locative`
- `Directional`
- `Goal`
- `Manner`
- `Temporal`
- `Extent`
- `Reciprocals`
- `SecondaryPredication`
- `PurposeClauses`
- `CauseClauses`
- `Discourse`
- `Modals`
- `Negation`
- `DirectSpeech`
- `Adverbials`
- `Adjectival`
- `LightVerb`
- `Construction`
- `NonCore`

These are implementation labels added at runtime. They are not fully reflected in the ontology files.

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

### 4.2 Lexical, mention, and entity relationships

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `REFERS_TO` | `TagOccurrence -> Tag` | none | Optional lemma grouping edge for non-stop tokens. |
| `REFERS_TO` | `EntityMention -> Entity` | none | Explicit mention-to-canonical link used by refinement-generated nominal mentions and by the maintained mention layer. |
| `REFERS_TO` | `EventMention -> TEvent` | none | Mention-to-canonical event link created by `EventEnrichmentPhase.create_event_mentions()`. |
| `REFERS_TO` | `NamedEntity -> Entity` | `type`: usually `evoke` | Canonical link from a surface mention to an entity abstraction. |
| `REFERS_TO` | `FrameArgument -> NamedEntity` | none | Refinement link from an argument span to a matched mention. |
| `REFERS_TO` | `FrameArgument -> Entity` | none | Flattened or fallback link from an argument span to a canonical or synthetic entity. Some refinement queries use undirected `MERGE`, so treat this as semantically bidirectional in old data. |
| `REFERS_TO` | `FrameArgument -> NUMERIC` | none | Argument linked directly to a numeric-labeled `NamedEntity`. |
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
| `PARTICIPANT` | `Entity -> TEvent` | `type`: copied from `FrameArgument.type`. `prep`: preposition when the argument is prepositional. | Event participant edge created for core roles in `EventEnrichmentPhase`. |
| `PARTICIPANT` | `Entity -> EventMention` | `type`: copied from `FrameArgument.type`. `prep`: preposition when the argument is prepositional. | Mention-level participant edge retained for compatibility alongside `EVENT_PARTICIPANT`. |
| `PARTICIPANT` | `NUMERIC -> TEvent` | `type`: copied from `FrameArgument.type`. `prep`: optional preposition. | Numeric participant edge in event enrichment. |
| `PARTICIPANT` | `NUMERIC -> EventMention` | `type`: copied from `FrameArgument.type`. `prep`: optional preposition. | Mention-level numeric participant edge retained for compatibility alongside `EVENT_PARTICIPANT`. |
| `PARTICIPANT` | `FrameArgument -> TEvent` | `type`: original non-core argument type. `prep`: optional preposition. | Non-core event participant edge from the argument span itself. |
| `EVENT_PARTICIPANT` | `Entity|NUMERIC|FrameArgument -> TEvent|EventMention` | `type`: copied from frame-argument role. `prep`: optional preposition for prepositional arguments. | Canonical participant edge family written alongside `PARTICIPANT` during the maintained transition period. |
| `TRIGGERS` | `TagOccurrence -> TIMEX` | none | Token or token span triggers a temporal expression node. |
| `TRIGGERS` | `TagOccurrence -> TEvent` | none | Token triggers a temporal event node. |
| `TRIGGERS` | `TagOccurrence -> Signal` | none | Token or token span anchors a temporal signal node. |
| `CREATED_ON` | `AnnotatedText -> TIMEX` | none | Connects a document to its DCT temporal node. |
| `TLINK` | `TEvent -> TEvent` | `id`: TLINK id from TARSQI XML when available. `relType`: temporal relation such as `BEFORE`, `AFTER`, `SIMULTANEOUS`. `signalID`: temporal signal id from TTK when available. `source`: heuristic source such as `t2g` when produced by `TlinksRecognizer`. | Event-to-event temporal relation. |
| `TLINK` | `TEvent -> TIMEX` | `id`, `relType`, `signalID`, `source` | Event-to-time temporal relation. |
| `TLINK` | `TIMEX -> TIMEX` | `id`, `relType`, `signalID`, `source` | Time-to-time temporal relation. |
| `CLINK` | `TEvent -> TEvent` | `source`: currently `srl_argm_cau` | Derived causal relation from `ARGM-CAU` frame arguments during event enrichment. |
| `SLINK` | `TEvent -> TEvent` | `source`: currently `srl_argm_dsp` | Derived subordinating relation from `ARGM-DSP` frame arguments during event enrichment. |

### 4.4 Fusion and keyword relationships

| Relationship | Endpoint pattern | Properties | Meaning |
| --- | --- | --- | --- |
| `CO_OCCURS_WITH` | `Entity -> Entity` | `confidence`: confidence score. `evidence_source`: rule family or phase. `rule_id`: specific rule identifier. `created_at`: creation timestamp. | Cross-sentence fusion edge for nearby entity co-occurrence. |
| `SAME_AS` | `Entity -> Entity` | `confidence`: confidence score. `evidence_source`: rule family or phase. `rule_id`: specific rule identifier. `created_at`: creation timestamp. | Cross-document identity fusion for entities sharing stable KB identity. |
| `DESCRIBES` | `Keyword -> AnnotatedText` | `rank`: keyword rank score | Legacy keyword-to-document descriptive edge. This is separate from `Frame -> TEvent` event description, but reuses the same relationship type. |

### 4.5 Transitional relationship policy

Some relationship families are intentionally dual-written during the current schema-alignment period so that maintained query paths and older graph consumers can coexist.

| Legacy relationship | Canonical/current relationship | Current write policy |
| --- | --- | --- |
| `PARTICIPANT` (`FrameArgument -> Frame`) | `HAS_FRAME_ARGUMENT` | Queries should tolerate both; newer query contracts prefer `HAS_FRAME_ARGUMENT|PARTICIPANT`. |
| `DESCRIBES` (`Frame -> TEvent`) | `FRAME_DESCRIBES_EVENT` | `EventEnrichmentPhase.link_frameArgument_to_event()` writes both edges intentionally. |
| `PARTICIPANT` (event participant edges) | `EVENT_PARTICIPANT` | Core and non-core participant enrichment write both edges for compatibility while newer consumers can prefer `EVENT_PARTICIPANT`. |

This dual-write strategy is intentional. It should be removed only as part of an explicit migration with coordinated query updates; it is not redundant drift.

## 5. Identity Conventions

Stable identifiers are important because most writes are implemented with `MERGE`.

Observed conventions:

- `AnnotatedText.id`: importer-assigned document id.
- `Sentence.id`: `<doc>_<sentence_index>`.
- `TagOccurrence.id`: `<doc>_<sentence_id>_<token_char_offset>` in current token creation code.
- `NamedEntity.id`: `<doc>_<start>_<end>_<type>`.
- `NamedEntity.token_id`: token-index-based deterministic id used for migration-safe matching.
- `NounChunk.id`: `<doc>_<start>`.
- `Frame.id`: `frame_<doc>_<start>_<end>`.
- `FrameArgument.id`: `fa_<doc>_<start>_<end>_<argtype>`.
- `Antecedent.id`: `Antecedent_<doc>_<start>_<end>`.
- `CorefMention.id`: `CorefMention_<doc>_<start>_<end>`.
- `TIMEX`: natural key is effectively `(tid, doc_id)`.
- `TEvent`: natural key is effectively `(eiid, doc_id)`.
- `PhaseRun.id` and `RefinementRun.id`: ISO timestamp strings.

## 6. Constraints and Indexes

### 6.1 Constraints created in application code

`GraphBasedNLP.create_constraints()` declares node-key or uniqueness-style constraints for:

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

Practical implication: the enforced schema depends on whether the app bootstrap path or the migrations path has been used. The migration path is currently more complete for `Frame` and `FrameArgument` uniqueness.

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
- `relType`: semantic value of a `TLINK`.
- `prep`: stored on `PARTICIPANT` edges when a preposition or prepositional head should be preserved.

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
2. `Keyword` nodes and `Keyword -[:DESCRIBES {rank}]-> AnnotatedText` edges exist in code but are missing from the ontology files.
3. `DESCRIBES` is overloaded for two unrelated subgraphs: `Frame -> TEvent` and `Keyword -> AnnotatedText`.
4. `PARTICIPANT` is also overloaded: it is used for `FrameArgument -> Frame`, `Entity/NUMERIC -> TEvent`, and `FrameArgument -> TEvent`.
5. `CONTAINS_SENTENCE` is the canonical document-to-sentence edge, but `fusion.py` still queries `:CONTAINS`, which does not match the primary ingestion schema and looks like legacy drift.
6. `PhaseRun` is a real persisted audit label but is not represented in the ontology files.
7. `RefinementRun` is also persisted and omitted from the ontology files.
8. `TlinksRecognizer` reads `e.modal` on `TEvent`, but the current write paths do not populate that property.
9. `TIMEX` has two property shapes because the codebase contains both the newer HeidelTime path (`start_index`, `end_index`, `text`, `quant`) and an older XML path (`begin`, `end`).
10. `Signal` is currently implemented only for temporal `SIGNAL` spans from TTK. `CSignal` is still a planned schema element, not a persisted label yet.
11. `FrameArgument.argumentType` includes a mapping for `ARGM-TMP`, but the current non-core enrichment query excludes `ARGM-TMP` from that branch, so the `Temporal` mapping is effectively unreachable there.
12. Some refinement `REFERS_TO` merges use undirected patterns, so very old data may not be perfectly uniform in relationship direction even when the intended semantics are clear.
13. The nominal semantic-head profile is intentionally additive. `head` remains the original surface or parser-root head, while `nominalSemanticHead*` stores the noun-preferred head used for lexical reasoning and nominal-event analysis.

## 9. Recommended Canonical View

If you need one simplified schema view for downstream consumers, use this canonical interpretation:

- Structural backbone: `AnnotatedText -> Sentence -> TagOccurrence`.
- Mentions and semantic spans: `TagOccurrence -> NamedEntity|Frame|FrameArgument|Antecedent|CorefMention|NounChunk` via `PARTICIPATES_IN`.
- Entity normalization: `NamedEntity -> Entity` via `REFERS_TO`.
- Event normalization: `TagOccurrence -> TEvent|TIMEX` via `TRIGGERS`, then `Frame -> TEvent` via `DESCRIBES`.
- Event participants: `Entity|NUMERIC|FrameArgument -> TEvent` via `PARTICIPANT`.
- Temporal relations: `TLINK` among `TEvent` and `TIMEX`.
- Fusion and provenance: `CO_OCCURS_WITH`, `SAME_AS`, and relation-evidence nodes where the legacy relation extraction path is enabled.

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
- Warn if advisory provenance/profile fields are missing.