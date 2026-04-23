<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Algorithm Card — TLINK Rule Engine

**Gateway** · **Wiki Home** · **Algorithms** · TLINK Rule Engine

## Purpose

Produce typed temporal links between `TEvent` and `TIMEX` endpoints consistent with Allen's interval algebra and the declared `temporal_reasoning_profile`.

## Inputs

- Canonical `TEvent` and `TIMEX` nodes (post-event-enrichment).
- `Signal` nodes and their syntactic attachments.
- `temporal_reasoning_profile` from [`ontology.json`](../../../src/textgraphx/schema/ontology.json).

## Outputs

- `TLINK` edges with `type` drawn from `temporal_reasoning_profile.canonical_reltypes`.
- Provenance fields on each edge (`source_rule`, `confidence` where available).

## Assumptions

- Endpoints are well-typed (enforced by `relation_endpoint_contract`).
- Document scope is the default unit of reasoning.
- Contradictory pairs (declared in `contradiction_pairs`) must not co-occur on the same endpoint pair.

## Limits / failure modes

- Rule-based TLINK extraction has limited recall on implicit relations.
- Cross-sentence TLINKs without a surface signal are under-generated.
- Closure inflates density; it is therefore applied conservatively (rules listed in `closure_rules`).

## Implementation

- [`src/textgraphx/TlinksRecognizer.py`](../../../src/textgraphx/TlinksRecognizer.py).

## Evaluation

- TLINK evaluator under `src/textgraphx/evaluators/`.
- Consistency diagnostics flag any `contradiction_pair` occurrence.
- Closure diagnostics report the number of inferred vs asserted edges.

## References

- [allen1983intervals]
- [pustejovsky2003timeml]
- [verhagen2007tempeval]
- [verhagen2010tempeval2]
- [uzzaman2013tempeval3]

## See also

- [`../10-linguistics/temporal-semantics.md`](../10-linguistics/temporal-semantics.md)
- [`temporal-extraction-ttk.md`](temporal-extraction-ttk.md)
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
