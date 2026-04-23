<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# MEANTIME Corpus

**Gateway** · **Wiki Home** · **Datasets** · MEANTIME

## Abstract

MEANTIME (Multilingual Event and Time Corpus) is the primary structural benchmark for TextGraphX. It provides gold annotations for entities, events, participants, and TLINKs in a multi-document news setting.

## What it contains

- ~120 news documents (the English subset is used by TextGraphX).
- Annotations: entity mentions and chains, event mentions and chains, participants with roles, TIMEX, and TLINK.
- NAF-based annotation format.

## How TextGraphX uses it

- **Structural bridge.** MEANTIME is the gold anchor for the M8 bridge validator ([`../50-evaluation-science/meantime-bridge.md`](../50-evaluation-science/meantime-bridge.md)).
- **Per-phase evaluation.** Entity/event/participant/TLINK evaluators score against MEANTIME gold.
- **Regression baseline.** MEANTIME summary metrics are committed under `src/textgraphx/datastore/evaluation/baseline/`.

## Limits

- English subset only in the current evaluation pipeline.
- News-domain bias; out-of-domain generalization is not measured.
- Annotation disagreements exist, especially at the TLINK layer.

## References

- [cybulska2014meantime]
- [pustejovsky2003timeml]

## See also

- [`newsreader-naf.md`](newsreader-naf.md)
- [`gold-vs-system-alignment.md`](gold-vs-system-alignment.md)
- [`../50-evaluation-science/meantime-bridge.md`](../50-evaluation-science/meantime-bridge.md)
