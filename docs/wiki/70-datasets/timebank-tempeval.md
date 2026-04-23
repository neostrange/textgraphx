<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# TimeBank and TempEval

**Gateway** · **Wiki Home** · **Datasets** · TimeBank / TempEval

## Abstract

TimeBank (and the TempEval series) is the reference corpus family for temporal expression recognition and TLINK classification.

## What's relevant

- **TimeBank 1.2** — ISO-TimeML gold annotations for TIMEX, EVENT, SIGNAL, TLINK.
- **TempEval-2 / TempEval-3** — shared tasks with evaluation protocols for TIMEX detection, value normalization, and TLINK classification.

## How TextGraphX uses it

- As a secondary evaluation target for TIMEX detection and TLINK extraction when MEANTIME is insufficient.
- As a source of canonical metric definitions: TempEval-3 defines the reference protocols TextGraphX follows when scoring TIMEX and TLINKs.

## Limits

- News-domain focus; generalization limited.
- TLINK annotation density differs from MEANTIME; numbers are not directly comparable across corpora.

## References

- [pustejovsky2003timeml]
- [verhagen2007tempeval]
- [verhagen2010tempeval2]
- [uzzaman2013tempeval3]
- [uzzaman2010event]

## See also

- [`../10-linguistics/temporal-semantics.md`](../10-linguistics/temporal-semantics.md)
- [`../30-algorithms/tlink-rule-engine.md`](../30-algorithms/tlink-rule-engine.md)
