<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Origin Paper — From Hur et al. (2024) to TextGraphX

**Gateway** · **Wiki Home** · **Foundations** · Origin Paper

> **Framing.** TextGraphX originated from the paper cited below. The current system treats it as **origin and motivation, not a specification**. Several shortcomings of the original proposal are addressed directly by the current repository. This page makes the provenance explicit and enumerates the extensions.

## Citation

Hur, A.; Janjua, N.; Ahmed, M. (2024). *Unifying context with labeled property graph: A pipeline-based system for comprehensive text representation in NLP.* **Expert Systems with Applications**, 239, 122269. DOI: [10.1016/j.eswa.2023.122269](https://doi.org/10.1016/j.eswa.2023.122269). Open access (CC BY 4.0). Short-key: `hur2024unifying`.

## What the paper contributed

The paper introduced a pipeline-based LPG approach to comprehensive text representation, with specialized patterns for:

1. Nominal mention detection.
2. Named-entity disambiguation (NED).
3. Event enrichment.
4. Event participant detection.
5. Temporal link (TLINK) detection.

It evaluated the approach on the MEANTIME corpus (Cybulska & Vossen).

## Lasting contributions (carried forward into TextGraphX)

- The pipeline-LPG paradigm itself.
- The five task tracks as a useful decomposition for event-centric text representation.
- Use of MEANTIME as a structural benchmark.

## Known limitations of the paper's proposal

These are the specific gaps the current repository addresses. The current system is not a reimplementation of the paper; it is an independent R&D artifact.

| # | Paper limitation | TextGraphX response |
| - | --- | --- |
| 1 | No formal schema tiering. | Machine-readable `canonical`/`optional`/`legacy` tiers in [`ontology.json`](../../../src/textgraphx/schema/ontology.json). See [`schema-autogen.md`](../40-ontology-and-schema/schema-autogen.md). |
| 2 | No reasoning contracts or endpoint typing. | `relation_endpoint_contract` + `temporal_reasoning_profile` + `event_attribute_vocabulary` enforced by phase assertions. See [`reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md). |
| 3 | No phase-level assertions / self-certifying pipeline. | `src/textgraphx/phase_assertions.py` + diagnostics query packs. |
| 4 | No regression gating or reproducibility metadata. | `src/textgraphx/tools/check_quality_gate.py`, baseline snapshots under `src/textgraphx/datastore/evaluation/baseline/`, deterministic IDs, provenance/authority policy ([`../../PROVENANCE_AUTHORITY_POLICY.md`](../../PROVENANCE_AUTHORITY_POLICY.md)). |
| 5 | No MEANTIME structural bridge validator. | Milestone 8 bridge validator ([`../../MILESTONE8_BRIDGE_VALIDATOR.md`](../../MILESTONE8_BRIDGE_VALIDATOR.md)). |
| 6 | Weak / implicit referential-chain handling. | Hard contracts: `EntityMention --REFERS_TO--> Entity`, `EventMention --REFERS_TO--> TEvent`, `TimexMention --REFERS_TO--> TIMEX`, `Frame --INSTANTIATES--> EventMention`. |
| 7 | No TLINK anchor consistency rules, no contradiction handling, no closure semantics. | `temporal_reasoning_profile`: canonical relation types, contradiction pairs, closure rules, DCT anchor policy. |
| 8 | No span coordinate contract. | [`span-coordinate-contract.md`](../40-ontology-and-schema/span-coordinate-contract.md): `start_tok`/`end_tok`/`start_char`/`end_char` invariants. |
| 9 | No event-mention layer distinct from canonical events. | `EventMention` node as first-class evidence layer for `TEvent`. |
| 10 | No value-node canonicalization. | `NUMERIC` / `VALUE` canonicalization for participant typing. |
| 11 | Single-corpus, not reproducible-by-CI. | Phase evaluators M1–M7, bridge M8, regression gates M9–M10; reports under `src/textgraphx/datastore/evaluation/`. |
| 12 | No docs/structural guardrails. | `.github/scripts/verify_structure_hygiene.sh` + upcoming `verify_docs_hygiene.sh`. |

## Tone rules when citing the paper elsewhere

- Use phrases like *"origin paper"*, *"initial proposal"*, *"motivated by"*. Avoid *"as defined by"* or *"per the paper"* — behavior is specified by the current codebase.
- Any reference to the paper should be paired with a pointer to the current-system counterpart to avoid conflating the two.

## References

- [hur2024unifying]
- [cybulska2014meantime]
- [hogan2021kg]

## See also

- [`theme-and-rationale.md`](theme-and-rationale.md)
- [`../60-research/README.md`](../60-research/README.md) — `paper-vs-current.md` (PR-6) will expand the per-contribution comparison.
- [`../40-ontology-and-schema/reasoning-contracts.md`](../40-ontology-and-schema/reasoning-contracts.md)
