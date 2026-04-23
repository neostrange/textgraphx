<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Datasets Overview

**Gateway** · **Wiki Home** · **Datasets** · Overview

## Abstract

TextGraphX touches several linguistic datasets/resources across ingestion, evaluation, and research. This page is the map.

## Datasets and resources

| Resource | Role in TextGraphX |
| --- | --- |
| **MEANTIME corpus** | Primary structural benchmark; gold for entities, events, participants, TLINKs ([`meantime-corpus.md`](meantime-corpus.md)). |
| **NewsReader NAF** | Ingestion format for MEANTIME-derived documents ([`newsreader-naf.md`](newsreader-naf.md)). |
| **TimeBank / TempEval** | Reference corpora for TIMEX and TLINK evaluation ([`timebank-tempeval.md`](timebank-tempeval.md)). |
| **TARSQI / TTK** | Temporal extraction tooling used inside the temporal phase ([`tarsqi-ttk-outputs.md`](tarsqi-ttk-outputs.md)). |
| **PropBank / FrameNet** | Reference lexical resources for SRL ([`propbank-framenet.md`](propbank-framenet.md)). |
| **WordNet** | Lexical enrichment (supersenses, synsets) ([`wordnet-synsets.md`](wordnet-synsets.md)). |
| **Coreference formats** | CoNLL-2003 / CoNLL-2012-style inputs ([`coreference-formats.md`](coreference-formats.md)). |

## Governance and policy

- Dataset selection and paths are declared centrally ([`dataset-governance.md`](dataset-governance.md)).
- All evaluation artifacts land under `src/textgraphx/datastore/evaluation/`, never under `datastore/annotated/` (user preference).
- Gold-vs-system alignment rules: [`gold-vs-system-alignment.md`](gold-vs-system-alignment.md).

## References

- [cybulska2014meantime]
- [pustejovsky2003timeml]
- [uzzaman2013tempeval3]
- [palmer2005propbank]
- [fillmore2006framenet]
- [miller1995wordnet]

## See also

- [`../55-evaluation-strategy/strategy-overview.md`](../55-evaluation-strategy/strategy-overview.md)
- [`../50-evaluation-science/meantime-bridge.md`](../50-evaluation-science/meantime-bridge.md)
