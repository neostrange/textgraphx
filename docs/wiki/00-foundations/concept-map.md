<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Concept Map

**Gateway** · **Wiki Home** · **Foundations** · Concept Map

## Abstract

A high-level picture of how the moving parts fit together. This is the single diagram to reach for when orienting a new reader.

## Pipeline and layers

```mermaid
flowchart LR
  subgraph Source
    TXT[Raw text / NAF / MEANTIME XML]
  end
  subgraph Pipeline
    ING[Ingestion<br/>GraphBasedNLP]
    REF[Refinement<br/>RefinementPhase]
    TMP[Temporal<br/>TemporalPhase]
    EVT[Event Enrichment<br/>EventEnrichmentPhase]
    TLK[TLINK<br/>TlinksRecognizer]
  end
  subgraph Graph
    TOK[TagOccurrence / Sentence]
    NER[NamedEntity / EntityMention]
    ENT[Entity canonical]
    FR[Frame / FrameArgument]
    TMX[TIMEX / TimexMention]
    TEV[TEvent / EventMention]
    SIG[Signal]
    TL[TLINK edges]
  end
  TXT --> ING --> TOK --> REF --> NER --> ENT
  REF --> FR
  REF --> TMP --> TMX
  TMP --> SIG
  ENT --> EVT --> TEV
  FR --> EVT
  TEV --> TLK --> TL
  TMX --> TLK
```

## Mention / canonical duality

```mermaid
flowchart LR
  EM[EntityMention] -- REFERS_TO --> EN[Entity]
  VM[EventMention] -- REFERS_TO --> TE[TEvent]
  TM[TimexMention] -- REFERS_TO --> TX[TIMEX]
  NE[NamedEntity] -- REFERS_TO --> EN
  FR[Frame] -- INSTANTIATES --> VM
  FA[FrameArgument] -- HAS_FRAME_ARGUMENT --> FR
  PT[Entity / NUMERIC / VALUE] -- EVENT_PARTICIPANT --> VM
```

## Governance stack

```mermaid
flowchart TB
  CODE[Runtime write paths] --> MIG[Applied migrations]
  MIG --> SDOC[docs/schema.md contract]
  SDOC --> ONT[ontology.json metadata]
  ONT --> DIAG[Diagnostics + phase assertions]
  DIAG --> QG[Quality gate / CI]
```

See [`../../schema.md`](../../schema.md) for the authoritative text of the precedence order.

## See also

- [`theme-and-rationale.md`](theme-and-rationale.md)
- [`../20-pipeline/pipeline-theory.md`](../20-pipeline/pipeline-theory.md)
- [`../40-ontology-and-schema/schema-autogen.md`](../40-ontology-and-schema/schema-autogen.md)
