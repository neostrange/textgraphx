<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Metrics Catalog (Science)

**Gateway** · **Wiki Home** · **Evaluation Science** · Metrics Catalog

## Abstract

The scientific side of the metrics catalog: the definitions, math, and caveats for each metric the system reports. For the operational view (which tier, where artifacts land) see [`../55-evaluation-strategy/metrics-catalog.md`](../55-evaluation-strategy/metrics-catalog.md).

## Span-level metrics

- **Precision / Recall / F1.**
  $$P = \frac{|S \cap G|}{|S|}, \quad R = \frac{|S \cap G|}{|G|}, \quad F_1 = \frac{2PR}{P+R}$$
  Where $S$ is the system's set of spans and $G$ is the gold set. Exact match vs relaxed (head-inclusive) match are both reported.

## Coreference metrics

- **MUC** — link-based.
- **B³** — mention-based.
- **CEAFφ4** — entity-based with similarity function $\phi_4$.
- Report the three alongside their macro average (CoNLL score).

## Temporal metrics

- **TLINK relation-type F1** over the canonical relation-type inventory.
- **Consistency score** — fraction of documents free of `contradiction_pair` occurrences.
- **Closure inflation** — ratio of inferred to asserted TLINKs under the declared closure rules.

## Contract metrics

- **Hard-contract violation count.** Must be zero.
- **Advisory-contract violation count.** Informational.

## Caveats

- Span-level metrics are sensitive to tokenizer choice; the MEANTIME bridge abstracts this away.
- Coreference metrics do not agree when chain topologies differ; always report all three.
- TLINK metrics depend heavily on whether closure is applied before scoring; the system scores pre-closure by default.

## References

- [tjong2003conll]
- [verhagen2007tempeval]
- [verhagen2010tempeval2]
- [uzzaman2013tempeval3]
- [allen1983intervals]

## See also

- [`what-quality-means.md`](what-quality-means.md)
- [`../55-evaluation-strategy/metrics-catalog.md`](../55-evaluation-strategy/metrics-catalog.md)
