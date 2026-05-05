# spaCy Gap Analysis, Critical Function Review, and Graph-Computable Enhancements

**Created:** 2025  
**Status:** Living document — update whenever pipeline phases or schema change  
**Audience:** Pipeline engineers, schema maintainers, evaluation leads

---

## Table of Contents

1. [Evaluation Baseline — Where We Stand](#1-evaluation-baseline)
2. [Critical Function Analysis — Ordering, Inputs/Outputs, Effectiveness](#2-critical-function-analysis)
3. [spaCy Attribute Gap Audit](#3-spacy-attribute-gap-audit)
4. [Graph-Computable Enhancement Algorithms](#4-graph-computable-enhancement-algorithms)
5. [Priority Action Matrix](#5-priority-action-matrix)

---

## 1. Evaluation Baseline — Where We Stand

Current MEANTIME evaluation (strict mode, 6 documents):

| Layer | Precision | Recall | F1 | Threshold | Status |
|---|---|---|---|---|---|
| entity | 0.267 | 0.340 | **0.299** | 0.75 | 🔴 Critical |
| event | 0.123 | 0.414 | **0.190** | 0.75 | 🔴 Critical |
| timex | 0.281 | 0.581 | **0.379** | 0.75 | 🔴 Critical |
| relation | 0.067 | 0.084 | **0.075** | 0.75 | 🔴 Critical |
| has_participant | 0.000 | 0.000 | **0.000** | — | 🔴 Broken |
| tlink | 0.070 | 0.145 | **0.094** | — | 🔴 Critical |

**Universal pattern:** precision << recall across every layer. The system over-generates on all axes. This is a filtering problem, not a coverage problem.

**Key type mismatches observed:**
- Events: predicted nodes are missing `aspect` and `tense` attributes that gold standard requires
- TIMEX: value format inconsistency (`PY5` vs `P5Y`)
- Entities: boundary offsets misaligned (predicted span is subset or superset of gold)

---

## 2. Critical Function Analysis — Ordering, Inputs/Outputs, Effectiveness

### 2.1 Stage Execution Order vs. Data Dependency

The pipeline executes stages in this hard-coded sequence in `orchestrator.py`:

```
Stage 1: ingestion → Stage 2: refinement → Stage 3: temporal → Stage 4: event_enrichment → Stage 5: tlinks
```

This ordering contains **two critical violations** where Stage 2 methods depend on data that doesn't exist until Stage 3/4:

#### Violation A — `morphological_projection` runs before TEvents exist

`RULE_FAMILIES["morphological_projection"]` includes:
- `project_event_polarity` — sets `polarity` on `TEvent` nodes
- `project_event_tense_aspect` — sets `tense`, `aspect` on `TEvent` nodes

**Problem:** `TEvent` nodes are created in Stage 3 (temporal) and Stage 4 (event enrichment), *after* Stage 2 completes. At the time `project_event_tense_aspect` runs, there are zero `TEvent` nodes in the graph. The methods execute without errors (zero rows matched) but produce no results.

**Direct link to evaluation failures:** The evaluation reports `type_mismatch` failures where gold has `aspect='NONE'` and `tense='PRESENT'` but predictions are missing these fields entirely. This is the direct cause. The morphological projection that should populate them runs too early.

**Fix:** Move `morphological_projection` and `syntactic_semantic_coercion` to run as the first step of Stage 4 (event_enrichment), not Stage 2. Alternatively, split Stage 2 into Stage 2a (token-level refinement) and Stage 2b (event-level refinement, run after Stage 3).

#### Violation B — `nominal_mentions` materialization partially blind to events

Several `nominal_mentions` methods create `EventMention` links to event anchors:
- `materialize_event_argument_mentions`
- `materialize_nominal_mentions_from_frame_arguments`

These try to link to `TEvent` nodes, but when Stage 2 runs, Stage 3 hasn't created `TEvent` nodes yet. The methods create `NamedEntity` fallback nodes instead, inflating entity counts (contributing to FP entity noise) and leaving event-argument links unresolved.

**Fix:** These two methods must move to Stage 4.

### 2.2 Function-Level Effectiveness Assessment

#### Head Assignment Family (16 methods — `head_assignment`)

| Method | Input | Output | Issue |
|---|---|---|---|
| `get_and_assign_head_info_to_entity_multitoken` | `NamedEntity` (multi-token spans) | `head`, `headTokenIndex` properties | Runs 16 separate Cypher round-trips sequentially |
| `get_and_assign_head_info_to_antecedent_*` | `Antecedent` nodes | head properties | Redundant with entity version for resolved mentions |
| `get_and_assign_head_info_to_corefmention_*` | `CorefMention` nodes | head properties | Same dependency-traversal logic repeated 6×  |
| `get_and_assign_head_info_to_frameArgument_*` | `FrameArgument` | head, preposition | 8 variants for different dep-parse patterns |

**Effectiveness:** All 16 methods implement the same query pattern (traverse `IS_DEPENDENT` from mention tokens, find the root). They run sequentially and each hits the DB independently. **All 16 are safe to run in parallel via `asyncio.gather()` or a thread pool.** No data dependency between them — each operates on a disjoint node label subset.

**Root cause of redundancy:** Head info (`dep_`, `head.i`) is not stored on `TagOccurrence` nodes. If `dep_` and `head_tok_index` were stored on the node at ingestion time (Stage 1), all 16 methods could be replaced by 2 Cypher `SET` statements that simply copy the property from the token node to the mention node. See §3 for the storage gap.

#### Linking Family (8 methods — `linking`)

| Method | Input | Output | Effectiveness |
|---|---|---|---|
| `link_antecedent_to_namedEntity` | `Antecedent` + coref clusters | `REFERS_TO` edges | Works, but has_participant still 0 |
| `link_frameArgument_to_namedEntity_for_nam_nom` | `FrameArgument` + `NamedEntity` | `EVENT_PARTICIPANT` edges | Creates participant links, but missing TEvent anchor |
| `link_frameArgument_to_namedEntity_for_pobj` | `FrameArgument` (pobj-type) | `EVENT_PARTICIPANT` | Overlapping coverage with `for_nam_nom` |
| `link_frameArgument_to_namedEntity_for_pro` | `FrameArgument` (PRO-type) | `EVENT_PARTICIPANT` | Handles pronouns — depends on coref |
| `link_frameArgument_to_new_entity` | Unlinked `FrameArgument` | Creates new `Entity` nodes | ⚠️ Creates entities without KB linkage → inflates FP |
| `link_frameArgument_to_numeric_entities` | Numeric `FrameArgument` | Numeric `Entity` | Fine |
| `link_frameArgument_to_entity_via_named_entity` | `FrameArgument` | `EVENT_PARTICIPANT` | Relies on NER resolution being complete |

**Critical issue — `has_participant F1=0.000`:** The linking methods connect `FrameArgument → Event_PARTICIPANT → Entity`. The evaluation measures `has_participant` as a relation between `TEvent` and `Entity`. Since `TEvent` nodes don't exist when Stage 2 runs, `EVENT_PARTICIPANT` edges are created with `Frame` nodes as the event anchor, not `TEvent` nodes. Stage 4 is supposed to bridge `Frame → TEvent`, but this bridge is not reliably created. The entire has_participant scoring pipeline is broken at this structural junction.

**`link_frameArgument_to_new_entity` is dangerous:** When no existing `NamedEntity` matches a `FrameArgument`, this method creates a new `Entity` node from the frame argument's text. These synthetic entities are not NER-validated and inflate false positives directly. The 17 spurious entities in doc 112579 are likely a product of this method.

#### Nominal Mentions Family (11 methods — `nominal_mentions`)

`promote_nominal_events` in `syntactic_semantic_coercion` (and the `nominal_mentions` family) aggressively creates event candidates from noun phrases. The evaluation shows 43 FP events vs 8 TP events in doc 112579. The `promote_nominal_events` method converts noun tokens with PropBank frame support into `TEvent` candidates, but the precision filter is too loose. Events like "exchange", "accord" are being promoted when they should not be.

**Missing precision signal:** The method currently uses frame existence as the sole criterion. It should also require:
1. The noun appears in a deverbal pattern (derivational form of a verb — available via WordNet `derivational_forms` already stored on tokens)
2. The noun is in a temporal argument position (parent or child with `ARGM-TMP`, `nsubj`, `dobj`)
3. PropBank frame confidence above threshold

#### TLINK Cases 4 and 5 — Overlap and Redundancy

Cases 4 and 5 both match the pattern:
```
(token:TagOccurrence)-[:IN_FRAME]->(fa:FrameArgument {type:'ARGM-TMP'})-...→(e:TEvent)
(token)-[:TRIGGERS]->(tm:TimexMention|TIMEX)
```
The difference is:
- Case 4: `fa.headTokenIndex = h.tok_index_doc`
- Case 5: `fa.end_tok = pobj.tok_index_doc` + preposition list check

These patterns match overlapping token sets when the ARGM-TMP argument ends at the TIMEX head. Both will fire on the same `(e, t)` pairs, creating duplicate TLINK attempts (mitigated by MERGE but wasteful). Case 5's richer preposition-to-relType mapping is the correct logic; Case 4 can be deprecated or absorbed into Case 5.

#### case6 (DCT anchoring) — Depends on tense attribute that may not exist

`create_tlinks_case6` filters on `e.tense IN ['PAST', 'PRESENT', 'FUTURE']`. Since `project_event_tense_aspect` runs in Stage 2 (before TEvents exist), most TEvent nodes arrive at Stage 5 with `tense=NULL`. Case 6 then matches zero rows. This is a direct consequence of Violation A above.

### 2.3 Input/Output Summary by Stage

| Stage | Key Inputs from Graph | Key Outputs to Graph | Current Bottleneck |
|---|---|---|---|
| 1 — ingestion | Raw text | `TagOccurrence`, `NamedEntity`, `Frame`, `FrameArgument`, `CorefMention` | SRL services called sequentially |
| 2 — refinement | Stage 1 nodes | `head`/`headTokenIndex` on mentions, `EVENT_PARTICIPANT`, `REFERS_TO` edges | 16 head-assign queries sequential; runs before TEvents exist |
| 3 — temporal | Stage 1+2 nodes | `TIMEX`, `TEvent` (from HeidelTime + TTK) | HeidelTime and TTK called sequentially |
| 4 — event enrichment | Stage 1+2+3 nodes | `EventMention`, `INSTANTIATES`, `ALIGNS_WITH` | morphological projection never applied (runs in Stage 2) |
| 5 — tlinks | Stage 1-4 nodes | `TLINK` edges | Case 6 fires on ~0 events (tense=NULL) |

---

## 3. spaCy Attribute Gap Audit

### 3.1 What `en_core_web_trf` Provides vs. What Is Stored

#### TagOccurrence node — currently stored

| Property | spaCy source | Notes |
|---|---|---|
| `text` | `token.text` | ✅ |
| `lemma` | `token.lemma_` | ✅ |
| `pos` | `token.tag_` | ✅ Penn Treebank fine-grained |
| `upos` | `token.pos_` | ✅ Universal POS |
| `index` | `token.idx` | ✅ char start offset |
| `end_index` | `token.idx + len(token.text)` | ✅ char end offset |
| `tok_index_doc` | `token.i` | ✅ |
| `tok_index_sent` | `token.i - sent.start` | ✅ |
| `is_stop` | `lexeme.is_stop \| is_punct \| is_space` | ✅ |
| morph features | `token.morph` — flattened as separate properties | ⚠️ Only in `TagOccurrenceCreator.create_tag_occurrences()`. The inline `store_sentence2()` in `text_processor.py` uses its own loop without morph. Code-path inconsistency. |

#### IS_DEPENDENT edge — currently stored

| Property | spaCy source | Notes |
|---|---|---|
| `type` (edge property) | `token.dep_` | ✅ dep label on the edge — but NOT on the TagOccurrence node itself |

#### TagOccurrence node — NOT stored (gaps)

| spaCy attribute | Type | Downstream value | Priority |
|---|---|---|---|
| `token.dep_` | str | Store directly on node. Eliminates need to traverse IS_DEPENDENT edge for dep-based Cypher filters. Head assignment (16 methods) could be replaced. | 🔴 High |
| `token.head.i` (`head_tok_index`) | int | Direct property lookup instead of graph traversal. Would reduce head-assignment Cypher complexity from 16 methods to 2. | 🔴 High |
| `token.ent_iob_` | str: B/I/O | BIO tag enables boundary detection. Currently, entity span boundaries are computed from `tok_index_doc` ranges on `NamedEntity`. Storing BIO on tokens enables set-union span reconstruction and fixes boundary mismatch issues. | 🔴 High |
| `token.ent_type_` | str | NER type on the token (redundant with NamedEntity.type, but available for non-linked tokens). | 🟡 Medium |
| `token.is_alpha` | bool | Separates alphabetic from numeric/punctuation tokens. Used in entity filtering. | 🟡 Medium |
| `token.is_digit` | bool | Numeric token flag. `link_frameArgument_to_numeric_entities` currently uses a heuristic. | 🟡 Medium |
| `token.like_num` | bool | Detects number-like tokens (e.g., "five", "3rd"). Better than `is_digit` for NLP purposes. | 🟡 Medium |
| `token.shape_` | str | Shape code e.g. `Xxxx`, `ddd`. Useful for pattern-based entity type heuristics (dates, codes, etc.). | 🟡 Medium |
| `token.norm_` | str | Lowercase normalized form. More stable than `text` for matching. | 🟡 Medium |
| `token.is_oov` | bool | Out-of-vocabulary flag. Low-confidence signal for rare tokens. | 🟢 Low |
| `token.whitespace_` | str | Whitespace after the token. Needed for accurate detokenization and text span reconstruction. | 🟢 Low |
| `token.is_sent_start` | bool | Sentence boundary marker. Useful for discourse-level features. | 🟢 Low |
| `token.vector_norm` | float | L2 norm of transformer embedding. Proxy for semantic specificity. Storing the full vector is expensive (768-dim), but the norm is cheap. | 🟢 Low |
| `token.cluster` | int | Brown cluster ID (when available). Coarse semantic grouping. | 🟢 Low |

#### Sentence node — gaps

| spaCy attribute | Notes |
|---|---|
| `sent.root.text` | The syntactic root of the sentence (main predicate). Useful for predicate identification. |
| `sent.root.dep_` | Root's dependency label (usually `ROOT`). |
| `sent.root.i` / `sent.root.tok_index_doc` | Index of the root token. Enables sentence-predicate lookups without traversal. |

Currently only `id` and `text` are stored on `Sentence` nodes. Adding root info would enable "what is the main event of this sentence?" as a direct property lookup.

#### AnnotatedText (document) node — gaps

| spaCy attribute | Notes |
|---|---|
| `doc._.coref_chains` | Coreference cluster count (already handled via `CorefMention` nodes) |
| Sentence count | Number of sentences in the document. Not stored. Useful for document-level normalization. |
| Token count | Total tokens. Useful for density metrics. |

### 3.2 Most Impactful Fixes (Top 3)

**Fix 1 — Store `dep_` and `head_tok_index` on TagOccurrence at ingestion**

Add two properties to the dict in `TagOccurrenceCreator.create_tag_occurrences()`:

```python
tag_occurrence = {
    ...existing fields...,
    "dep": token.dep_,
    "head_tok_index": token.head.i,
}
```

Impact: The 16 head-assignment methods in Stage 2 can be reduced to a single MATCH+SET:

```cypher
MATCH (m:NamedEntity|FrameArgument)
MATCH (m)<-[:PARTICIPATES_IN]-(tok:TagOccurrence)
WHERE tok.dep NOT IN ['punct','space']
WITH m, tok ORDER BY tok.tok_index_doc
// Find the token whose dep label indicates it is the syntactic head of the span
MATCH (head_tok:TagOccurrence {tok_index_doc: tok.head_tok_index})
  WHERE head_tok.tok_index_doc >= m.start_tok AND head_tok.tok_index_doc <= m.end_tok
    AND head_tok.dep IN ['nsubj','dobj','pobj','nsubjpass','attr','ROOT']
WITH m, head_tok LIMIT 1
SET m.head = head_tok.text,
    m.headTokenIndex = head_tok.tok_index_doc,
    m.headLemma = head_tok.lemma
```

**Fix 2 — Store `ent_iob_` on TagOccurrence**

Add `"ent_iob": token.ent_iob_` to the token dict. This enables a Cypher-based span reconstruction:

```cypher
// Find entity spans by IOB sequence — enables boundary correction
MATCH (s:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
WHERE tok.ent_iob IN ['B','I']
WITH s, tok ORDER BY tok.tok_index_doc
// Group consecutive B/I tokens into spans
```

This would replace the current approach of reading NER output spans from spaCy and trusting them as-is, allowing post-hoc span correction against the dependency tree.

**Fix 3 — Unify `store_sentence2()` to call `TagOccurrenceCreator.create_tag_occurrences()`**

The `store_sentence2()` method in `text_processor.py` duplicates token creation logic inline (without morph features). This creates inconsistency: some documents in the graph have morphological features, others don't. The fix is to remove the inline loop and delegate to `TagOccurrenceCreator.create_tag_occurrences()`.

---

## 4. Graph-Computable Enhancement Algorithms

These enhancements require no new external service calls. They operate purely on existing graph data via Cypher queries.

### 4.1 Tense/Aspect Projection from Stored Morphological Features

**Impact:** Directly fixes the `type_mismatch` failures in event evaluation.

The morphological features `Tense`, `Aspect`, and `VerbForm` are stored on `TagOccurrence` nodes as flat properties (when `create_tag_occurrences()` is used). These can be projected to `TEvent` nodes via the `TRIGGERS` relationship.

```cypher
// Stage 4 backfill — run AFTER TEvent nodes are created
MATCH (e:TEvent)<-[:TRIGGERS]-(tok:TagOccurrence)
WHERE e.tense IS NULL OR e.aspect IS NULL
WITH e, tok,
  CASE tok.Tense
    WHEN 'Past'   THEN 'PAST'
    WHEN 'Pres'   THEN 'PRESENT'
    ELSE
      CASE tok.VerbForm
        WHEN 'Inf'  THEN 'INFINITIVE'
        WHEN 'Part' THEN CASE tok.Tense WHEN 'Past' THEN 'PASTPART' ELSE 'PRESPART' END
        ELSE 'NONE'
      END
  END AS inferred_tense,
  CASE tok.Aspect
    WHEN 'Prog' THEN 'PROGRESSIVE'
    WHEN 'Perf' THEN 'PERFECTIVE'
    ELSE 'NONE'
  END AS inferred_aspect
SET e.tense  = coalesce(e.tense,  inferred_tense),
    e.aspect = coalesce(e.aspect, inferred_aspect),
    e.tense_source  = coalesce(e.tense_source,  'morphological_projection_stage4'),
    e.aspect_source = coalesce(e.aspect_source, 'morphological_projection_stage4')
```

**Note:** Requires Fix 3 from §3.2 (morph features must actually be in the graph). Also requires moving this rule to run after Stage 3.

### 4.2 Transitive TLINK Closure

**Impact:** Increases TLINK recall (currently 0.145) with high precision.

If `A BEFORE B` and `B BEFORE C`, then `A BEFORE C`. This is a valid Allen interval algebra inference. The current TLINK rules do not implement transitivity.

```cypher
// Transitive BEFORE closure
MATCH (a:TEvent)-[:TLINK {relType:'BEFORE'}]->(b)-[:TLINK {relType:'BEFORE'}]->(c)
WHERE elementId(a) <> elementId(c)
  AND NOT (a)-[:TLINK]->(c)
MERGE (a)-[tl:TLINK]->(c)
ON CREATE SET tl.relType = 'BEFORE',
              tl.source = 'transitivity',
              tl.confidence = 0.72,
              tl.rule_id = 'transitive_before',
              tl.evidence_source = 'graph_inference'
RETURN count(tl) AS created
```

```cypher
// Transitive AFTER closure
MATCH (a:TEvent)-[:TLINK {relType:'AFTER'}]->(b)-[:TLINK {relType:'AFTER'}]->(c)
WHERE elementId(a) <> elementId(c)
  AND NOT (a)-[:TLINK]->(c)
MERGE (a)-[tl:TLINK]->(c)
ON CREATE SET tl.relType = 'AFTER',
              tl.source = 'transitivity',
              tl.confidence = 0.72,
              tl.rule_id = 'transitive_after',
              tl.evidence_source = 'graph_inference'
RETURN count(tl) AS created
```

```cypher
// BEFORE + IS_INCLUDED → BEFORE (if A IS_INCLUDED B and B BEFORE C, then A BEFORE C)
MATCH (a:TEvent)-[:TLINK {relType:'IS_INCLUDED'}]->(b)-[:TLINK {relType:'BEFORE'}]->(c)
WHERE elementId(a) <> elementId(c)
  AND NOT (a)-[:TLINK]->(c)
MERGE (a)-[tl:TLINK]->(c)
ON CREATE SET tl.relType = 'BEFORE',
              tl.source = 'transitivity',
              tl.confidence = 0.65,
              tl.rule_id = 'transitive_included_before',
              tl.evidence_source = 'graph_inference'
RETURN count(tl) AS created
```

**Caution:** Run transitivity closure iteratively (fixed-point iteration, max 5 rounds) to avoid creating contradictory TLINKs. Apply only when no conflicting TLINK already exists between the pair.

### 4.3 Event Class Inference from PropBank Frame Names

**Impact:** Improves event `class` attribute completeness.

PropBank frame names encode semantic class. A lookup table from frame lemma pattern → TimeML event class:

```cypher
MATCH (f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
WHERE e.class IS NULL
WITH e, f.frame AS frame_name,
  CASE
    WHEN f.frame IN ['say.01','announce.01','report.01','tell.01','claim.01','declare.01'] THEN 'REPORTING'
    WHEN f.frame IN ['know.01','believe.01','think.01','feel.01','understand.01','assume.01'] THEN 'I_STATE'
    WHEN f.frame IN ['want.01','hope.01','plan.01','intend.01','try.01','attempt.01'] THEN 'I_ACTION'
    WHEN f.frame IN ['begin.01','start.01','continue.01','end.01','finish.01','stop.01'] THEN 'ASPECTUAL'
    WHEN f.frame IN ['be.01','have.01','remain.01','become.01','exist.01'] THEN 'STATE'
    ELSE 'OCCURRENCE'
  END AS inferred_class
SET e.class = inferred_class,
    e.class_source = 'propbank_frame_inference'
RETURN count(e) AS updated
```

This can be extended with a larger lookup table over PropBank 3.4 frame groupings.

### 4.4 Event Confidence Filtering — Reduce Over-Generation

**Impact:** Directly addresses precision 0.123 on events. The system generates ~5× too many events.

```cypher
// Mark events with only one weak evidence source as low_confidence
MATCH (e:TEvent)
WHERE coalesce(e.low_confidence, false) = false
// Count supporting evidence
OPTIONAL MATCH (e)<-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f:Frame)
  WHERE f.framework IN ['PROPBANK','NOMBANK']
OPTIONAL MATCH (e)<-[:TRIGGERS]-(tok:TagOccurrence)
WITH e,
  count(DISTINCT f) AS frame_count,
  count(DISTINCT tok) AS trigger_count,
  coalesce(e.confidence, 1.0) AS base_conf
// Events created solely by the TTK/HeidelTime service with no frame support
// and low base confidence → mark as provisional
WHERE frame_count = 0 AND base_conf < 0.6
SET e.low_confidence = true,
    e.confidence = base_conf * 0.5,
    e.low_confidence_reason = 'no_frame_support'
RETURN count(e) AS marked
```

```cypher
// Mark nominal events with no deverbal WordNet link as low_confidence
MATCH (e:TEvent)<-[:TRIGGERS]-(tok:TagOccurrence)
WHERE tok.upos = 'NOUN'
  AND coalesce(e.low_confidence, false) = false
  AND e.pos = 'NOUN'
// Check if token has derivational event support
OPTIONAL MATCH (tok)-[:HAS_LEMMA]->(tag:Tag)
  WHERE tag.derivational_eventive_verbs IS NOT NULL
    AND size(tag.derivational_eventive_verbs) > 0
WITH e, tok, tag
WHERE tag IS NULL  // no deverbal support
SET e.low_confidence = true,
    e.confidence = coalesce(e.confidence, 0.5) * 0.6,
    e.low_confidence_reason = 'nominal_no_deverbal_support'
RETURN count(e) AS marked
```

### 4.5 Entity Salience Scoring

**Impact:** Enables downstream filtering and ranking of entities by discourse centrality.

```cypher
// Compute entity salience from participation and mention counts
MATCH (e:Entity)
OPTIONAL MATCH (e)<-[:EVENT_PARTICIPANT]-(ev:TEvent)
WITH e, count(DISTINCT ev) AS event_degree
OPTIONAL MATCH (e)<-[:REFERS_TO]-(m)
  WHERE m:NamedEntity OR m:CorefMention
WITH e, event_degree, count(DISTINCT m) AS mention_count
SET e.salience = round(
    (0.6 * toFloat(mention_count) + 0.4 * toFloat(event_degree))
    / (toFloat(mention_count) + toFloat(event_degree) + 1.0),
    4
  ),
  e.salience_computed_at = timestamp()
RETURN count(e) AS updated
```

Salience can then gate which entities appear in has_participant relations and filter low-salience FPs.

### 4.6 Frame ALIGNS_WITH Completeness — PropBank/NomBank Cross-Linking

**Impact:** Improves NomBank frame coverage for events that have both verbal and nominal predicates.

The specification requires `(:Frame)-[:ALIGNS_WITH]->(:Frame)` between PropBank and NomBank frames describing the same event. Currently this is created only during ingestion when both SRL services fire on the same token window. But many pairs are missed when the window check fails.

```cypher
// Link PropBank and NomBank frames for the same TEvent by shared head lemma
MATCH (fv:Frame {framework:'PROPBANK'})
MATCH (fn:Frame {framework:'NOMBANK'})
WHERE fv.headLemma = fn.headLemma
  AND NOT (fv)-[:ALIGNS_WITH]->(fn)
  AND fv.headLemma IS NOT NULL
OPTIONAL MATCH (fv)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
OPTIONAL MATCH (fn)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e)
// Only align frames describing the same event
WITH fv, fn, e WHERE e IS NOT NULL
MERGE (fv)-[aw:ALIGNS_WITH]->(fn)
ON CREATE SET aw.source = 'headlemma_colocated',
              aw.confidence = 0.70,
              aw.evidence_source = 'graph_inference'
RETURN count(aw) AS created
```

### 4.7 Hypernym-Based Entity Type Normalization via WordNet

**Impact:** Reduces entity type mismatches in evaluation. Uses already-stored `wn_hypernym_tree` or `wnLexname` properties.

```cypher
// Coerce entity type from WordNet hypernym chain
MATCH (e:Entity)<-[:REFERS_TO]-(m:NamedEntity)
WHERE e.type IS NULL OR e.type = 'MISC'
MATCH (m)<-[:PARTICIPATES_IN]-(tok:TagOccurrence)
WHERE tok.wnLexname IS NOT NULL
WITH e, m, tok,
  CASE
    WHEN tok.wnLexname IN ['noun.person','noun.group'] THEN 'PERSON'
    WHEN tok.wnLexname IN ['noun.location','noun.object'] THEN 'LOCATION'
    WHEN tok.wnLexname IN ['noun.act','noun.event','noun.process'] THEN 'ORGANIZATION'
    ELSE NULL
  END AS inferred_type
WHERE inferred_type IS NOT NULL
  AND coalesce(e.kb_linked, false) = false  // don't override KB-linked type
WITH e, inferred_type, count(*) AS vote_count ORDER BY vote_count DESC
WITH e, collect(inferred_type)[0] AS top_type  // majority vote
SET e.type = top_type,
    e.type_source = 'wordnet_hypernym'
RETURN count(e) AS updated
```

### 4.8 TIMEX Value Format Normalization

**Impact:** Fixes the `PY5` vs `P5Y` type mismatch observed in evaluation. ISO 8601 duration format is `P[n]Y[n]M[n]DT...`, not `PY5`.

```cypher
// Fix malformed ISO 8601 duration values (e.g., PY5 → P5Y, PM3 → P3M)
MATCH (t:TIMEX)
WHERE t.type = 'DURATION'
  AND t.value IS NOT NULL
  // Detect transposed unit-number order: P[unit][n] instead of P[n][unit]
  AND t.value =~ 'P[YMDWH][0-9]+'
WITH t,
  // Reorder to P[n][unit]
  'P' + substring(t.value, 2) + substring(t.value, 1, 1) AS corrected_value
WHERE corrected_value <> t.value
SET t.value_raw = t.value,
    t.value = corrected_value,
    t.value_normalized = true
RETURN count(t) AS fixed
```

### 4.9 Dependency-Path-Based Entity Relation Extraction

**Impact:** Adds semantic relations between entities that are syntactically linked but lack explicit SRL frames. Works on the existing `IS_DEPENDENT` edge graph.

```cypher
// Extract subject-verb-object triples as implicit relations
MATCH (s:Sentence)-[:HAS_TOKEN]->(subj_tok:TagOccurrence)-[:IS_DEPENDENT {type:'nsubj'}]->
      (pred_tok:TagOccurrence)-[:IS_DEPENDENT {type:'dobj'}]->(obj_tok:TagOccurrence)
MATCH (subj_tok)<-[:PARTICIPATES_IN]-(subj_ne:NamedEntity)-[:REFERS_TO]->(subj_e:Entity)
MATCH (obj_tok)<-[:PARTICIPATES_IN]-(obj_ne:NamedEntity)-[:REFERS_TO]->(obj_e:Entity)
WHERE subj_e <> obj_e
// Create an implicit relation edge
MERGE (subj_e)-[r:IMPLICIT_RELATION {verb_lemma: pred_tok.lemma}]->(obj_e)
ON CREATE SET r.source = 'dep_path_svo',
              r.confidence = 0.65,
              r.predicate_tok_id = pred_tok.id,
              r.sentence_id = s.id
RETURN count(r) AS created
```

This extracts subject-verb-object triples as typed edges. These can later feed has_participant relation scoring.

### 4.10 Coreference Chain Quality Signal

**Impact:** Enables confidence-gated entity merging and cross-document fusion.

```cypher
// Compute per-chain quality signals
MATCH (chain:CorefChain)
OPTIONAL MATCH (chain)-[:HAS_MENTION]->(m:CorefMention)
WITH chain, count(m) AS mention_count
OPTIONAL MATCH (chain)-[:HAS_MENTION]->(m2:CorefMention)-[:REFERS_TO]->(ne:NamedEntity)
WITH chain, mention_count, count(ne) AS named_entity_anchors
SET chain.mention_count = mention_count,
    chain.named_entity_anchors = named_entity_anchors,
    chain.confidence = CASE
      WHEN mention_count >= 5 AND named_entity_anchors >= 1 THEN 0.92
      WHEN mention_count >= 3 AND named_entity_anchors >= 1 THEN 0.82
      WHEN mention_count >= 2 THEN 0.70
      ELSE 0.50
    END
RETURN count(chain) AS updated
```

### 4.11 Sentence Root Backfill

**Impact:** Enables fast predicate identification without IS_DEPENDENT traversal.

```cypher
// Backfill sentence root token reference onto Sentence nodes
MATCH (s:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
WHERE tok.dep = 'ROOT'
  AND s.root_tok_id IS NULL
SET s.root_tok_id = tok.id,
    s.root_lemma = tok.lemma,
    s.root_upos = tok.upos
RETURN count(s) AS updated
```

**Prerequisite:** Requires Fix 1 from §3.2 (`dep` property on TagOccurrence).

---

## 5. Priority Action Matrix

| Priority | Action | Type | Expected F1 Impact | Effort | Blocker? |
|---|---|---|---|---|---|
| P0 | Move `morphological_projection` to Stage 4 | Code ordering | event F1 +0.05–0.15 (fixes type mismatches) | Low | No |
| P0 | Move `materialize_event_argument_mentions` to Stage 4 | Code ordering | has_participant F1 > 0 | Low | No |
| P1 | Store `dep_` and `head_tok_index` on TagOccurrence | Schema + code | Reduces 16 head queries → 1 | Medium | No |
| P1 | Store `ent_iob_` on TagOccurrence | Schema + code | entity boundary mismatch ↓ | Medium | No |
| P1 | Run §4.1 tense/aspect projection query in Stage 4 | Cypher | event tense/aspect in all predictions | Low | Needs P0 |
| P1 | Run §4.4 event confidence filter | Cypher | event precision ↑ significantly | Low | No |
| P2 | Run §4.2 transitive TLINK closure | Cypher | tlink recall ↑ | Low | No |
| P2 | Run §4.3 event class inference | Cypher | event class attribute completeness ↑ | Low | No |
| P2 | Deprecate/merge TLINK Case 4 into Case 5 | Code | Reduces redundancy | Low | No |
| P2 | Run §4.8 TIMEX normalization | Cypher | timex value mismatch ↓ | Low | No |
| P3 | Fix `link_frameArgument_to_new_entity` — add KB gate | Code | entity FP ↓ | Medium | No |
| P3 | Store `like_num`, `is_alpha`, `shape_` on TagOccurrence | Schema + code | Better numeric entity detection | Low | No |
| P3 | Run §4.5 entity salience scoring | Cypher | Enables downstream filtering | Low | No |
| P3 | Run §4.6 Frame ALIGNS_WITH completeness | Cypher | NomBank coverage ↑ | Low | No |
| P3 | Unify `store_sentence2()` to use `TagOccurrenceCreator` | Code | Morph consistency across all docs | Low | No |
| P4 | Run §4.7 hypernym entity type normalization | Cypher | entity type mismatch ↓ | Low | No |
| P4 | Run §4.9 SVO triple extraction | Cypher | Implicit relations added | Medium | No |
| P4 | Backfill sentence root (§4.11) | Cypher | Faster predicate lookup | Low | Needs P1 |

### Quick Wins (zero schema changes, pure Cypher, run immediately)

The following can be run against the existing graph without any code changes or schema migrations:

1. **§4.4** — mark low-confidence events (precision fix)
2. **§4.2** — transitive TLINK closure (recall fix)
3. **§4.8** — TIMEX value normalization (format fix)
4. **§4.3** — event class from PropBank frames (completeness)
5. **§4.5** — entity salience (enables gating)
6. **§4.6** — Frame ALIGNS_WITH gap fill (coverage)
7. **§4.10** — coref chain quality signal (confidence)

None of these touch the ingestion pipeline or schema constraints. They are additive Cypher passes that set properties on existing nodes and can be run in any order. Adding them as a post-Stage-5 "graph enhancement" phase (Stage 6) would be low-risk and directly measurable against the MEANTIME evaluation.

---

*Document end. See also [NLP_FUNCTION_CATALOG.md](NLP_FUNCTION_CATALOG.md), [NLP_FUNCTION_DEPENDENCY_GRAPH.md](NLP_FUNCTION_DEPENDENCY_GRAPH.md), [MASTER_ARCHITECTURE_PLAN.md](MASTER_ARCHITECTURE_PLAN.md).*
