<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — SRL (PropBank-style)

**Gateway** · **Wiki Home** · **Algorithms** · SRL (PropBank)

## Purpose

Identify predicate-argument structures for each verbal (and selected nominal) predicate and record them as `Frame` + `FrameArgument` nodes.

## Inputs

- `TagOccurrence` sequence with POS and dependency labels.
- Lemma / roleset identifier when an SRL model supplies one.

## Outputs

- `Frame` per predicate.
- `FrameArgument` per semantic argument, with role label drawn from the controlled argument type vocabulary.
- `HAS_FRAME_ARGUMENT` and `INSTANTIATES` edges.

## Assumptions

- Predicate sense inventory is PropBank-compatible.
- Nominal predicates are a second-class concern; coverage is driven by the upstream model.

## Limits / failure modes

- Argument-span drift is common around conjunctions and coordination.
- Implicit arguments (not expressed in the clause) are not recovered.

## Implementation

- [`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py) (SRL integration point).
- SRL helper components under [`src/textgraphx/text_processing_components/`](../../../src/textgraphx/text_processing_components).

## Evaluation

- Frame-level checks feed into the event-participant evaluator.
- Phase assertions validate that every `Frame` has at least one `HAS_FRAME_ARGUMENT` edge when SRL is enabled.

## References

- [palmer2005propbank]
- [fillmore2006framenet]
- [gildea2002srl]

## See also

- [`../10-linguistics/semantic-role-labeling.md`](../10-linguistics/semantic-role-labeling.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
