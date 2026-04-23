<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Paper vs Current — A Per-Contribution Comparison

**Gateway** · **Wiki Home** · **Research** · Paper vs Current

> **Tone.** The origin paper (Hur, Janjua & Ahmed, 2024 — [hur2024unifying]) established the pipeline-LPG paradigm and the five task tracks. It is the motivation for this repository and is **not** a specification. The current codebase has extended, replaced, or formalized most of the paper's initial proposals. Use phrases like *"origin paper"*, *"initial proposal"*, *"motivated by"* — not *"as defined by"*. Authoritative shorter version: [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md).

## Per-contribution comparison

| # | Paper contribution | TextGraphX current state |
| - | --- | --- |
| 1 | Pipeline-based LPG paradigm | Retained and extended with contract governance ([`../40-ontology-and-schema/ontology-overview.md`](../40-ontology-and-schema/ontology-overview.md)). |
| 2 | Nominal mention detection | Retained; enriched with WordNet supersenses ([`../30-algorithms/wsd-wordnet.md`](../30-algorithms/wsd-wordnet.md)) and a canonical `EntityMention` layer. |
| 3 | Named entity disambiguation (NED) | Retained; canonical `Entity` fusion is now contract-enforced ([`../30-algorithms/entity-fusion-and-canonicalization.md`](../30-algorithms/entity-fusion-and-canonicalization.md)). |
| 4 | Event enrichment | Retained and split into `TEvent` (canonical) + `EventMention` (evidence) with `INSTANTIATES` bridging to SRL frames. |
| 5 | Event participant detection | Retained; participants travel through `EVENT_PARTICIPANT` with typed endpoints enforced by `relation_endpoint_contract`. Dynamic `NUMERIC`/`VALUE` labels added. |
| 6 | TLINK extraction | Retained; normalized onto Allen-aligned `canonical_reltypes` with `contradiction_pairs`, `closure_rules`, and a DCT anchor policy ([`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)). |
| 7 | MEANTIME evaluation | Retained as a benchmark; formalized into the M8 structural bridge validator ([`../50-evaluation-science/meantime-bridge.md`](../50-evaluation-science/meantime-bridge.md)). |
| 8 | Schema description | Replaced by a machine-readable schema with canonical/optional/legacy tiers ([`../40-ontology-and-schema/schema-semantics.md`](../40-ontology-and-schema/schema-semantics.md)) and applied migrations. |
| 9 | Reasoning guarantees | Added. Not present in paper. `relation_endpoint_contract`, `event_attribute_vocabulary`, `temporal_reasoning_profile`. |
| 10 | Span contract | Added. Not present in paper. Span fields + invariants in [`../40-ontology-and-schema/span-coordinate-contract.md`](../40-ontology-and-schema/span-coordinate-contract.md). |
| 11 | Mention/canonical duality | Added. Not present in paper. Hard contract on all canonical chains. |
| 12 | Phase assertions / self-certifying pipeline | Added. Not present in paper. See [`../55-evaluation-strategy/self-certifying-reports.md`](../55-evaluation-strategy/self-certifying-reports.md). |
| 13 | Regression gate / CI discipline | Added. Not present in paper. Baseline snapshots + `check_quality_gate.py`. |
| 14 | Docs governance / CI guardrails | Added. Not present in paper. `.github/scripts/verify_structure_hygiene.sh` and `verify_docs_hygiene.sh`. |
| 15 | Deprecated edge policy | Added. Not present in paper. `deprecated_relationships` with documented replacements. |

## How to talk about the paper in current docs

- Use [hur2024unifying] as the citation.
- Prefer *"origin paper"*, *"initial proposal"*, *"motivated by"*. Avoid *"as defined by"*.
- Every reference to the paper should pair with a pointer to the current-system counterpart (see this page and [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md)).

## References

- [hur2024unifying]
- [cybulska2014meantime]
- [hogan2021kg]
- [allen1983intervals]

## See also

- [`../00-foundations/origin-paper.md`](../00-foundations/origin-paper.md)
- [`open-questions.md`](open-questions.md)
- [`related-work.md`](related-work.md)
