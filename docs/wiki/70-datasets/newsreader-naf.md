<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# NewsReader / NAF

**Gateway** · **Wiki Home** · **Datasets** · NewsReader / NAF

## Abstract

The NLP Annotation Format (NAF), from the NewsReader project, is the ingestion format that MEANTIME ships in. TextGraphX has a NAF reader in the ingestion stage.

## Structure (high level)

- A NAF document is a layered XML file: text, terms (tokens/POS/lemma), dependencies, entities, timex, events, TLINK, and more.
- Each layer references earlier layers by span identifiers, giving a consistent anchor for evaluation.

## How TextGraphX consumes it

- Ingestion reads token, entity, timex, and event layers to seed the graph.
- Dependency and SRL layers are consulted when available; otherwise the pipeline re-derives them with pinned upstream models.

## Limits

- NAF layer coverage varies by dataset generation; evaluators must tolerate missing layers.
- Cross-version NAF differences exist; the reader documents which versions are tested.

## See also

- [`meantime-corpus.md`](meantime-corpus.md)
- [`gold-vs-system-alignment.md`](gold-vs-system-alignment.md)
