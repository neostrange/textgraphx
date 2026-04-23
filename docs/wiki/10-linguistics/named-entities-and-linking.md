<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Named Entities and Linking

**Gateway** · **Wiki Home** · **Linguistics** · Named Entities and Linking

## Abstract

Named entities are surfaced as `NamedEntity` mentions, then promoted/linked to canonical `Entity` nodes during the refinement phase. The mention/canonical split is the defining discipline of this layer.

## What is represented

- **`NamedEntity`** — surface mention with span, NE type, and `doc_id`.
- **`EntityMention`** — the broader mention class covering nominal mentions beyond strict named-entity categories.
- **`Entity`** — canonical entity; downstream reasoning target.
- **`REFERS_TO`** — `NamedEntity` / `EntityMention` → `Entity`.

## Where it is produced

- NER: ingestion ([`src/textgraphx/GraphBasedNLP.py`](../../../src/textgraphx/GraphBasedNLP.py)).
- NED / canonicalization: refinement ([`src/textgraphx/RefinementPhase.py`](../../../src/textgraphx/RefinementPhase.py)).

## Why this matters

- Participant resolution joins against `Entity`, never against `NamedEntity` alone.
- Cross-sentence / cross-document identity lives only at the canonical layer.
- Dynamic labels (`NUMERIC`, `VALUE`) are applied at the canonical layer when participants are not proper named entities.

## Limits and pitfalls

- Off-the-shelf NER taxonomies (PERSON/LOC/ORG/DATE/...) do not align one-to-one with MEANTIME's event-participant roles; evaluator code normalizes across them.
- Entity linking to external KBs (e.g., DBpedia/Wikidata) is not globally performed; it is opt-in per pipeline configuration.

## References

- [tjong2003conll]
- [fillmore2006framenet]
- [hogan2021kg]

## See also

- [`../30-algorithms/ner-and-linking.md`](../30-algorithms/ner-and-linking.md)
- [`../30-algorithms/entity-fusion-and-canonicalization.md`](../30-algorithms/entity-fusion-and-canonicalization.md)
- [`coreference-and-discourse.md`](coreference-and-discourse.md)
