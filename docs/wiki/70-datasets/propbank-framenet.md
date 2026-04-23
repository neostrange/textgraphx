<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# PropBank and FrameNet

**Gateway** · **Wiki Home** · **Datasets** · PropBank / FrameNet

## Abstract

PropBank and FrameNet are the two lexical resources behind SRL in TextGraphX. PropBank is the primary roleset reference; FrameNet provides a richer semantic-frame view used for analysis and enrichment.

## What they provide

- **PropBank.** Predicate rolesets (e.g., `run.02` with `ARG0`, `ARG1`, ...). Training anchor for most SRL models.
- **FrameNet.** Frame definitions with frame elements (FEs). Broader semantic typing of predicates.

## How TextGraphX uses them

- SRL model outputs are mapped onto a `Frame`/`FrameArgument` graph structure.
- The `argument_type_vocabulary` in `ontology.json` captures the controlled set of argument role labels accepted.

## Limits

- Lexical coverage is English-centric.
- Nominal predicates are under-represented compared to verbal predicates.

## References

- [palmer2005propbank]
- [fillmore2006framenet]
- [gildea2002srl]

## See also

- [`../10-linguistics/semantic-role-labeling.md`](../10-linguistics/semantic-role-labeling.md)
- [`../30-algorithms/srl-propbank.md`](../30-algorithms/srl-propbank.md)
