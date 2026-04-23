<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Semantic Role Labeling (SRL)

**Gateway** · **Wiki Home** · **Linguistics** · Semantic Role Labeling

## Abstract

SRL turns each predicate into a `Frame` with typed `FrameArgument`s. Frames bridge the linguistic layer and the event layer by attaching to their corresponding `EventMention` via `INSTANTIATES`.

## What is represented

- **`Frame`** — predicate frame node. Carries predicate lemma, sense/roleset id, and a link to its triggering `TagOccurrence` via `TRIGGERS`.
- **`FrameArgument`** — one argument of a frame. Carries the argument role label and span coordinates.
- **`HAS_FRAME_ARGUMENT`** — `FrameArgument` → `Frame`.
- **`INSTANTIATES`** — `Frame` → `EventMention` (canonical link between SRL and event layers).
- **`FRAME_DESCRIBES_EVENT`** — `Frame` → `TEvent` (indirect convenience edge preserved for queries).

## Where it is produced

SRL is produced in ingestion / refinement (see [`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py) and the SRL components under [`src/textgraphx/text_processing_components/`](../../../src/textgraphx/text_processing_components)).

## Why this matters

- Event participant detection uses `FrameArgument`s as primary candidate set before canonicalization to `Entity`, `NUMERIC`, or `VALUE`.
- Argument role labels feed the controlled `argument_type_vocabulary` in [`ontology.json`](../../../src/textgraphx/schema/ontology.json).
- The `Frame`-`EventMention` duality keeps SRL evidence separate from canonical event identity.

## Limits and pitfalls

- Frame coverage depends on the upstream SRL model's training data (PropBank-style rolesets are the typical anchor).
- Nominal predicates are under-covered compared to verbal predicates.

## References

- [palmer2005propbank]
- [fillmore2006framenet]
- [gildea2002srl]

## See also

- [`syntax-and-dependencies.md`](syntax-and-dependencies.md)
- [`../30-algorithms/srl-propbank.md`](../30-algorithms/srl-propbank.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
