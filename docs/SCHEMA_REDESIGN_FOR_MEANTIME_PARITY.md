# TextGraphX Schema Redesign for MEANTIME Semantic Parity

**Objective:** Restructure TextGraphX schema to incorporate all MEANTIME semantic information while maintaining backward compatibility and operational stability.

**Principle:** Do not retrofit; redesign with MEANTIME-first thinking, then backfill TextGraphX-specific elements.

---

## 1. Core Architectural Problem

### The Mention Conflation Issue

**Current TextGraphX Architecture:**
```
AnnotatedText
  └── Sentence
        └── TagOccurrence (token)
              ├── PARTICIPATES_IN → NamedEntity (mention + entity conflated)
              ├── PARTICIPATES_IN → Frame (SRL predicate, not event mention)
              └── TRIGGERS → TEvent (canonical event with mention properties)
```

**Root Problems:**

1. **NamedEntity is both mention and entity**
   - Stores NER output directly (mention-level surface form, type from NER model)
   - Expected to be stable canonical entity (but types drift with NER models)
   - Cannot distinguish "Barack Hussein Obama" (mention) from "Barack Obama" (canonical)
   - Missing syntactic classification (NAM vs NOM vs PRO)

2. **TEvent is both canonical event and mention**
   - Contains `tense`, `aspect` (mention properties, verb-specific)
   - Contains `eiid`, `doc_id` (canonical event identity)
   - Cannot separate "the company was founded" (mention tense: PAST) from the actual founding event
   - Places event-mention properties on the canonical node

3. **Frame is SRL predicate, not event mention**
   - Frame = PropBank/FrameNet predicate (linguistic artifact)
   - Should not be conflated with EventMention (the semantic event instantiation)
   - Current design conflates "founded" (Frame) with the founding event itself (EventMention/TEvent)

4. **No distinction between mention and annotation layers**
   - MEANTIME: `<ENTITY_MENTION>` (surface form) → `<ENTITY>` (canonical)
   - TextGraphX: NamedEntity is both
   - This breaks when mentions need independent properties (syntactic_type, confidence, mention context)

---

## 2. MEANTIME Semantic Model (Simplified)

```
DOCUMENT-LEVEL (Document Layer)
  └── TOKEN (anchors all higher annotations)
        
MENTION LAYER (Surface-level, mention-specific properties)
  ├── EntityMention
  │   ├── head, syntactic_type, start_tok, end_tok
  │   └── REFERS_TO → Entity (canonical)
  │
  ├── EventMention
  │   ├── pred, pos, tense, aspect, certainty, polarity, time
  │   ├── special_cases, modality
  │   └── REFERS_TO → Event (canonical)
  │
  ├── TIMEX
  │   ├── type, value, functionInDocument
  │   └── anchorTimeID → TIMEX (temporal anchoring)
  │
  ├── Signal (temporal trigger)
  │   └── TRIGGERS → TLINK
  │
  └── CSignal (causal trigger)
      └── TRIGGERS → CLINK

CANONICAL LAYER (Semantic, cross-document)
  ├── Entity (class, ent_type, external_ref/kb_id)
  ├── Event (class, external_ref)
  └── Value (type: PERCENT, MONEY, QUANTITY)

RELATION LAYER (Semantically-typed edges)
  ├── REFERS_TO (mention ↔ canonical)
  ├── HAS_PARTICIPANT (event ↔ participant with role+framework)
  ├── TLINK (temporal: BEFORE, AFTER, etc.)
  ├── CLINK (causal: cause → effect)
  ├── SLINK (subordinating: speech_cognitive ↔ content)
  └── GLINK (grammatical: grammatical_verb ↔ content_verb)
```

---

## 3. Critical Design Decisions

### Decision 1: Mention Layer Existence

**Option A: Keep Current (No Mention Layer)**
- Pro: Minimal disruption to existing code
- Con: Cannot represent mention-specific properties; fails MEANTIME compliance

**Option B: Introduce Mention Layer (Recommended)**
- Pro: Full MEANTIME compliance; clean separation of concerns
- Con: More nodes in graph; requires migration and backward-compat layer

**Champion: Option B** — The complexity is worth it for semantic correctness and evaluation capability.

---

### Decision 2: How to Represent Mentions

**Option A: Separate Node Labels**
```
Entity (canonical)
  ←[:REFERS_TO]-
EntityMention (surface)

TEvent (canonical)
  ←[:REFERS_TO]-
EventMention (surface)
```
Pro: Clear semantics; MEANTIME-aligned  
Con: More nodes; existing queries must adapt

**Option B: Use a "Mention" Relationship Property**
```
Entity -[:REFERS_TO {is_canonical: false, mention_id: "m123"}]- Entity
```
Pro: Fewer nodes  
Con: Semantically muddy; conflates edges with entities

**Champion: Option A** — Explicit node separation is cleaner and more queryable.

---

### Decision 3: Frame vs EventMention Relationship

**Current Problem:** Frame (SRL predicate) conflated with EventMention

**Option A: Frame becomes a property of EventMention**
```
EventMention.frame_id → Frame.id
EventMention -[:HAS_FRAME]-> Frame
```

**Option B: EventMention and Frame remain separate, connect via explicit relation**
```
EventMention -[:INSTANTIATES_FRAME]-> Frame
```

**Option C: Introduce EventHeading layer**
```
EventMention -[:HAS_PREDICATE]-> Frame
Frame -[:HAS_ARGUMENT]-> FrameArgument
```

**Champion: Option B** — EventMention and Frame represent different linguistic/semantic levels; explicit relation clarifies the connection.

---

### Decision 4: Backward Compatibility

**Option A: Migrate everything (breaking change)**
- Existing queries break
- Cleaner internals
- High user impact

**Option B: Run dual representation during transition**
```
Old-style (for backward compat):
  NamedEntity (legacy, presence of this label means "old style")
  
New-style (canonical):
  Entity ←[:REFERS_TO]- EntityMention
  
Adapter: When querying, transform old ↔ new as needed
```

**Champion: Option B** — Provide transition window; mark old patterns as deprecated.

---

## 4. Proposed Schema Restructure

### 4.1 New Node Labels

#### Mention Layer (New)

| Label | Purpose | Key Properties | Canonical Anchor |
|-------|---------|-----------------|------------------|
| `EntityMention` | Surface entity mention | `head`, `syntactic_type` (NAM/NOM/PRO/etc), `start_tok`, `end_tok`, confidence | Entity |
| `EventMention` | Surface event mention | `pred`, `pos`, `tense`, `aspect`, `certainty`, `polarity`, `time`, `special_cases`, `modality`, `start_tok`, `end_tok` | TEvent |
| `Signal` | Temporal trigger word | `text`, `type` (SIGNAL), `start_tok`, `end_tok` | N/A (triggers TLINK) |
| `CSignal` | Causal trigger word | `text`, `type` (C-SIGNAL), `start_tok`, `end_tok` | N/A (triggers CLINK) |
| `Value` | Numerical expression | `text`, `type` (PERCENT/MONEY/QUANTITY), `start_tok`, `end_tok` | N/A (semantic role source) |

#### Canonical Layer (Modified)

| Label | Current | Changes | Reason |
|-------|---------|---------|--------|
| `Entity` | Has NER-level properties | Move NER properties to EntityMention; keep only KB-level here | Separate layers |
| `TEvent` | Has mention properties | Move mention properties to EventMention; keep only canonical here | Separate layers |
| `TIMEX` | Sparse | Add `functionInDocument`, `anchorTimeID`, `beginPoint`, `endPoint` | MEANTIME alignment |
| `Frame` | SRL predicate frame | No change (but clarify relation to EventMention) | Linguistic structure |

#### Existing Layer (Preserved)

- `AnnotatedText`, `Sentence`, `TagOccurrence`: No change
- `NamedEntity` (deprecated): Mark as legacy; provide migration path
- `Antecedent`, `CorefMention`, `NounChunk`: Preserve

---

### 4.2 New Relationship Types

#### Mention ↔ Canonical (New)

| Relation | Source | Target | Properties | Purpose |
|----------|--------|--------|------------|---------|
| `REFERS_TO` | EntityMention | Entity | `confidence` | Mention points to canonical entity |
| `REFERS_TO` | EventMention | TEvent | `confidence` | Mention points to canonical event |

#### Semantic Roles (Restructured)

| Relation | Source | Target | Properties | Distinction |
|----------|--------|--------|------------|------------|
| `HAS_PARTICIPANT` | EventMention | EntityMention \| Value | `sem_role`, `sem_role_framework` (PROPBANK/FRAMENET/KYOTO) | Core SRL: event ↔ participant |
| `HAS_FRAME_ARGUMENT` | EventMention | FrameArgument | `type` | Secondary: detailed FrameNet mapping |

#### Temporal/Causal Relations (New)

| Relation | Source | Target | Properties | Purpose |
|----------|--------|--------|------------|---------|
| `TLINK` | TEvent \| TIMEX | TEvent \| TIMEX | `relType`, `signalID` (→ Signal) | Temporal links |
| `CLINK` | TEvent | TEvent | `c-signalID` (→ CSignal) | Causal links |
| `SLINK` | TEvent | TEvent | (none) | Subordination (speech ↔ content) |
| `GLINK` | TEvent | TEvent | (none) | Grammatical (aspect/causal verbs) |

#### Signal Anchoring (New)

| Relation | Source | Target | Purpose |
|----------|--------|--------|---------|
| `TRIGGERS` | Signal | TLINK | Temporal trigger word |
| `TRIGGERS` | CSignal | CLINK | Causal trigger word |

---

## 5. Schema Comparison: Current vs. Proposed

### Current Structure Issues

```
NamedEntity
  ├── id (NER output ID, not canonical)
  ├── type (NER type, model-dependent)
  ├── value (surface form)
  ├── kb_id (canonical link, if any)
  └── REFERS_TO Entity (if resolved)
  
Problem: NamedEntity IS both the mention and sometimes the entity
Result: Cannot track "who mentioned what" separately from "what entity exists"
```

### Proposed Structure

```
EntityMention (surface-level, mention-specific)
  ├── id (unique mention ID)
  ├── head (syntactic head)
  ├── syntactic_type (NAM, NOM, PRO, etc.)
  ├── start_tok, end_tok
  ├── confidence
  └── REFERS_TO → Entity (canonical)

Entity (canonical, cross-document)
  ├── id (stable, KB-based)
  ├── ent_type (PER, LOC, ORG, ART, FIN, MIX)
  ├── ent_class (SPC, GEN, USP, NEG) — specificity
  ├── external_ref (DBpedia, Wikidata)
  └── kb_id
  
Benefit: Clean separation; mention properties don't leak into canonical
```

---

## 6. Implementation Strategy: TDD-Based Redesign

### Phase 1: Add New Mention Layer (Non-Breaking)

**Goal:** Introduce new mention types alongside old ones.

**Tests (Write First):**
```python
# Unit: EntityMention structure
def test_entity_mention_has_required_properties():
    mention = EntityMention(head="Obama", syntactic_type="NAM", start_tok=5, end_tok=6)
    assert mention.syntactic_type in {"NAM", "NOM", "PRO", "PTV", "PRE", "HLS", "CONJ", "APP", "ARC"}

# Integration: EntityMention → Entity link
def test_entity_mention_refers_to_entity():
    entity = Entity(id="ent_1", ent_type="PER")
    mention = EntityMention(id="m_1", head="Obama")
    mention.REFERS_TO(entity)
    assert entity in mention.refers_to

# Migration: Backfill from NamedEntity
def test_backfill_entity_mentions_from_namedentity():
    ne = NamedEntity(id="ne_1", head="Obama", type="PERSON")
    # Create EntityMention from NamedEntity
    mention = backfill_entity_mention_from_namedentity(ne)
    assert mention.head == "Obama"
    assert mention.syntactic_type is not None
```

**Implementation:**
1. Add `EntityMention`, `EventMention` labels to ontology
2. Add `REFERS_TO` edges (mention → canonical)
3. Write backfill migration from NamedEntity → EntityMention
4. Run tests; ensure old NamedEntity still works (dual representation)

**Output:** 95+ tests pass; both old and new query patterns work

---

### Phase 2: Introduce Signal/CSignal and Causal Relations

**Goal:** Add temporal and causal infrastructure.

**Tests:**
```python
def test_signal_node_structure():
    signal = Signal(id="sig_1", text="after", start_tok=10, end_tok=11)
    assert signal.text in ["after", "before", "during", ...]

def test_clink_causal_relation():
    cause = TEvent(id="te_1")
    effect = TEvent(id="te_2")
    clink = CLINK(source=cause, target=effect)
    assert clink.c_signalID is None or isinstance(clink.c_signalID, CSignal)

def test_signal_triggers_tlink():
    signal = Signal(text="after")
    tlink = TLINK(relType="AFTER")
    signal.TRIGGERS(tlink)
    assert tlink.signalID == signal.id
```

**Implementation:**
1. Add `Signal`, `CSignal` labels
2. Add `CLINK`, `SLINK`, `GLINK` relation types
3. Add `signalID` property to TLINK
4. Add `c-signalID` property to CLINK
5. Create relations from Signal/CSignal to their triggered relations

**Output:** 105+ tests pass; temporal/causal network intact

---

### Phase 3: Restructure Event Layer

**Goal:** Separate EventMention from TEvent; move mention properties.

**Tests:**
```python
def test_event_mention_has_mention_properties():
    em = EventMention(pred="founded", pos="VERB", tense="PAST", aspect="PERFECTIVE")
    assert em.pred == "founded"
    assert em.tense in ["PRESENT", "PAST", "FUTURE", "NONE", "INFINITIVE", "PRESPART", "PASTPART"]

def test_tevent_has_canonical_only():
    te = TEvent(id="te_1", class="OTHER", external_ref="dbpedia/Founding")
    assert hasattr(te, "class")
    assert hasattr(te, "external_ref")
    assert not hasattr(te, "tense")  # No mention properties!

def test_event_mention_refers_to_tevent():
    em = EventMention(id="em_1")
    te = TEvent(id="te_1")
    em.REFERS_TO(te)
    assert te in em.refers_to

def test_frame_relationship_to_event_mention():
    em = EventMention(id="em_1")
    frame = Frame(id="frame_1")
    em.HAS_FRAME(frame)
    # or: em.INSTANTIATES_FRAME(frame)
```

**Implementation:**
1. Create EventMention label with mention properties
2. Remove mention properties from TEvent
3. Add TEvent.class, TEvent.external_ref
4. Create REFERS_TO edges (EventMention → TEvent)
5. Backfill from existing TEvent (one TEvent can generate one EventMention or multiple)

**Complexity:** Event mention conflation is trickier than entity mention — one TEvent may have multiple mentions, or one mention may map to multiple TEvents.

**Solution:** Create EventMention for each canonical TEvent; optionally cluster multiple EventMentions from same source.

**Output:** 110+ tests pass; event mention/canonical cleanly separated

---

### Phase 4: Enrich Temporal Information

**Goal:** Extend TIMEX with MEANTIME properties.

**Tests:**
```python
def test_timex_function_in_document():
    timex = TIMEX(id="timex_1", functionInDocument="CREATION_TIME")
    assert timex.functionInDocument in ["CREATION_TIME", "NONE"]

def test_timex_anchoring():
    timex1 = TIMEX(id="timex_1", type="DATE", value="2024-04-03")
    timex2 = TIMEX(id="timex_2", type="DATE", anchorTimeID="timex_1")
    assert timex2.anchorTimeID == timex1.id

def test_timex_interval():
    timex = TIMEX(id="timex_1", type="DURATION", beginPoint="2024-01-01", endPoint="2024-12-31")
    assert timex.beginPoint and timex.endPoint
```

**Implementation:**
1. Add properties to TIMEX: `functionInDocument`, `anchorTimeID`, `beginPoint`, `endPoint`
2. Add backfill migration for existing TIMEX
3. Tests ensure all properties are queryable

**Output:** 115+ tests pass; temporal expressivity matches MEANTIME

---

### Phase 5: Formalize Semantic Roles

**Goal:** Align HAS_PARTICIPANT with MEANTIME semantics.

**Tests:**
```python
def test_has_participant_properties():
    # EventMention → EntityMention with SRL
    participation = Participation(
        source=event_mention,
        target=entity_mention,
        sem_role="Arg0",
        sem_role_framework="PROPBANK"
    )
    assert participation.sem_role_framework in ["PROPBANK", "FRAMENET", "KYOTO"]

def test_value_node_type():
    value = Value(text="50%", type="PERCENT")
    assert value.type in ["PERCENT", "MONEY", "QUANTITY"]
    # Value can participate in HAS_PARTICIPANT
    participation = event_mention.HAS_PARTICIPANT(value, sem_role="ArgM-EXTENT")
```

**Implementation:**
1. Formalize `HAS_PARTICIPANT` as primary SRL relation
2. Add `sem_role_framework` governance
3. Upgrade VALUE from label-only to structured node
4. Create tests validating SRL coverage

**Output:** 120+ tests pass; full SRL governance in place

---

## 7. Backward Compatibility Strategy

### Keep Old Structures Alive

**NamedEntity (Deprecated but Functional)**
```
NamedEntity -[:CREATED_FROM]-> EntityMention (provenance link)
NamedEntity.deprecated = true (in property audit)
```

**Adapter Layer (For Queries)**
```python
# Old query:
MATCH (ne:NamedEntity) -[:REFERS_TO]-> (e:Entity) RETURN ne, e

# Can be transparently rewritten to:
MATCH (em:EntityMention) -[:REFERS_TO]-> (e:Entity)
AND (ne:NamedEntity) -[:CREATED_FROM]-> (em)
RETURN ne, e

# Or vice versa: if only new structure exists, materialize NamedEntity view
```

**Migration Window:** 2-3 quarters; allow old code to run while providing deprecation warnings and transformation utilities.

---

## 8. Data Reconciliation: Current ↔ Proposed

### Entity Mention Backfill

**Current:**
```
NamedEntity {id: "ne_123", head: "Obama", type: "PERSON", value: "Barack Hussein Obama"}
  -[:REFERS_TO]-> Entity {id: "kb_456", kb_id: "wikidata/Q44267", external_ref: "..."}
```

**Proposed:**
```
EntityMention {id: "em_123", head: "Obama", syntactic_type: "NAM", confidence: 0.95}
  -[:REFERS_TO]-> Entity {id: "kb_456", ent_type: "PER", ent_class: "SPC", external_ref: "..."}

NamedEntity {id: "ne_123"} -[:CREATED_FROM]-> EntityMention {id: "em_123"}  [backfill link]
```

**Migration SQL-like pseudocode:**
```cypher
MATCH (ne:NamedEntity) -[:REFERS_TO]-> (e:Entity)
CREATE (em:EntityMention {
  id: "em_" + ne.id,
  head: ne.head,
  syntactic_type: infer_syntactic_type(ne), // NOM for most NER types
  start_tok: ne.start_tok,
  end_tok: ne.end_tok,
  confidence: ne.confidence or 0.5
})
CREATE (em)-[:REFERS_TO]->(e)
CREATE (ne)-[:CREATED_FROM]->(em)
```

### Event Mention Backfill

**Current:**
```
TEvent {id: "te_123", eiid: "e123", doc_id: 1, tense: "PAST", begin: 100, end: 110}
  -[:TRIGGERS]-> TagOccurrence {id: "tok_100"}
Frame {id: "frame_456"}
  -[:DESCRIBES]-> TEvent {id: "te_123"}
```

**Proposed:**
```
EventMention {id: "em_123", pred: "founded", pos: "VERB", tense: "PAST", start_tok: 100, end_tok: 110}
  -[:REFERS_TO]-> TEvent {id: "te_123", eiid: "e123", doc_id: 1, class: "OTHER"}
Frame {id: "frame_456"}
  -[:INSTANTIATES_FRAME]-> EventMention {id: "em_123"}

TEvent {id: "te_123"} -[:CREATED_FROM]-> EventMention {id: "em_123"}  [backfill link]
```

---

## 9. Impact Analysis

### Breaking Changes (Managed via Deprecation)

| Change | Impact | Mitigation |
|--------|--------|-----------|
| TEvent loses `tense`, `aspect`, etc. | Queries expecting these fail | Provide accessor that redirects to EventMention |
| NamedEntity no longer primary entity layer | Old entity queries may miss EntityMention layer | Adapter: auto-expand NamedEntity → EntityMention |
| New mention nodes | Graph size increases | Manageable; mentions are sparse relative to tokens |
| New CLINK/SLINK/GLINK edges | Existing TLINK-only queries unaffected | New relations are additive |

### Benefits

- ✅ Full MEANTIME compliance
- ✅ Clean mention/canonical separation
- ✅ Supports causal and subordination reasoning
- ✅ Multi-framework SRL governance
- ✅ Backward compatible during transition

### Query Complexity

**Old:** `MATCH (ne:NamedEntity) -[:REFERS_TO]-> (e:Entity) RETURN ne, e`  
**New:** `MATCH (em:EntityMention) -[:REFERS_TO]-> (e:Entity) RETURN em, e`

- Old queries still work (via deprecated NamedEntity)
- New queries are simpler and more semantically clear
- Adapter layer allows transparent transition

---

## 10. Phasing and Timeline

| Phase | Milestone | Tests Target | Duration |
|-------|-----------|--------------|----------|
| 1 | Entity mention layer | 95+ | 1-2 weeks |
| 2 | Signal/causal infrastructure | 105+ | 1-2 weeks |
| 3 | Event mention layer | 110+ | 2 weeks |
| 4 | Temporal enrichment | 115+ | 1 week |
| 5 | SRL governance | 120+ | 1 week |
| Transition | Backward compat + docs | 120+ | 2-4 weeks |

**Total: 4-8 weeks** for full redesign with high confidence.

---

## 11. Champion Approach Summary

### Design Decision Summary

| Decision | Champion | Rationale |
|----------|----------|-----------|
| Introduce mention layer? | **YES (Option B)** | MEANTIME compliance + semantic correctness |
| Use separate node labels? | **YES (Option A)** | Clear, queryable, MEANTIME-aligned |
| Frame vs EventMention | **Option B: explicit relation** | Linguistic clarity; not conflated |
| Backward compat? | **YES (Option B: dual repr)** | Smooth transition; existing code survives |

### Key Structural Changes

1. **New node types:** `EntityMention`, `EventMention`, `Signal`, `CSignal`, `Value`
2. **New relations:** `CLINK`, `SLINK`, `GLINK`, `HAS_PARTICIPANT` (formalized), `TRIGGERS` (Signal → TLINK)
3. **Restructured:** TEvent (remove mention properties), Entity (add class/external_ref), TIMEX (add temporal properties)
4. **Preserved:** AnnotatedText, Sentence, TagOccurrence, Frame, existing TLINK logic

### Test Coverage Goal

- Unit: 50+ tests (property contracts, node/relation creation)
- Integration: 50+ tests (mention ↔ canonical, signal anchoring, event mention chains)
- Migration: 20+ tests (backfill correctness, data reconciliation)
- **Total: 120+ tests** passing, covering both old and new patterns

---

## 12. Next Steps

1. **Consensus on Design:** Review this proposal; confirm champion approach
2. **M8 Planning:** Formalize detailed requirements per phase
3. **Test-First Execution:** Start with Phase 1 (Entity Mention Layer)
4. **Parallel Documentation:** Update ontology.json and schema.md as we go
5. **Evaluation:** Compare resulting graph against MEANTIME-annotated datasets

---

## Appendix: MEANTIME ↔ TextGraphX Mapping (Proposed)

| MEANTIME | Current TextGraphX | Proposed TextGraphX | Status |
|----------|-------------------|-------------------|--------|
| Document | AnnotatedText | AnnotatedText | ✅ No change |
| token | TagOccurrence | TagOccurrence | ✅ No change |
| Entity (canonical) | Entity | Entity + (ent_class, external_ref) | ✅ Enhanced |
| EntityMention | NamedEntity (conflated) | EntityMention | ✅ New |
| Event (canonical) | TEvent (conflated) | TEvent (cleaned) | ✅ Refactored |
| EventMention | Implicit in TEvent | EventMention | ✅ New |
| Signal | None | Signal | ✅ New |
| C-Signal | None | CSignal | ✅ New |
| Value | NUMERIC (label only) | Value (node) | ✅ New |
| REFERS_TO (entity) | REFERS_TO | REFERS_TO (EntityMention → Entity) | ✅ Clarified |
| REFERS_TO (event) | Implicit | REFERS_TO (EventMention → TEvent) | ✅ New |
| HAS_PARTICIPANT | PARTICIPANT (ambiguous) | HAS_PARTICIPANT (formalized) | ✅ Formalized |
| TLINK | TLINK | TLINK + signalID | ✅ Enhanced |
| CLINK | None | CLINK | ✅ New |
| SLINK | None | SLINK | ✅ New |
| GLINK | None | GLINK | ✅ New |

**Result:** 100% MEANTIME semantic parity + TextGraphX operational excellence
