<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# For Context Engineering

**Gateway** · **Wiki Home** · **Applications** · For Context Engineering

## Abstract

"Context engineering" — the discipline of assembling the right evidence for a prompt — benefits from a graph whose units already match the things an LLM needs to reason about: entities, events, participants, and times.

## Useful properties

- **Structural slicing.** Retrieve a subgraph around a query entity/event rather than a flat passage.
- **Temporal window retrieval.** Use TLINK neighborhoods to materialize "what happened just before this" contexts.
- **Canonical deduplication.** Multiple surface mentions collapse to one canonical node — context stays compact.
- **Typed filters.** Filter by `wnLexname`, event attributes, argument roles.

## Patterns

- **Event-centric retrieval.** Start from the `TEvent` most likely relevant to the query, expand by participant and temporal neighbors.
- **Time-window materialization.** Given a `TIMEX` or DCT, pull all events whose TLINK chain anchors inside the window.
- **Path-based explanation.** Surface the graph path that supports a retrieved context; include it as citation in the prompt.

## Limits

- Subgraph size must be bounded; LLM context windows are finite.
- Subgraph quality depends on schema completeness — gaps in participant detection produce gaps in context.

## References

- [lewis2020rag]
- [edge2024graphrag]

## See also

- [`for-llm-genai.md`](for-llm-genai.md)
- [`integration-patterns.md`](integration-patterns.md)
- [`use-cases.md`](use-cases.md)
