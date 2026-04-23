<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# For LLM / Generative AI

**Gateway** · **Wiki Home** · **Applications** · For LLM / Generative AI

## Abstract

TextGraphX is a natural substrate for grounding large language models: an event-centric, temporally-anchored KG gives GraphRAG-style retrieval, contract-backed factuality, and reasoning paths an LLM can cite.

## Why this matters for LLMs

- **Grounding.** Retrieval against a typed graph returns more than similar-text; it returns entities, events, their participants, and their temporal relations.
- **Factuality.** The schema's hard contracts (span integrity, canonical chains, TLINK consistency) let a downstream validator decide whether an LLM answer is supported by graph evidence.
- **Explanation.** Every answer can be traced to (a) spans in source text, (b) canonical nodes, and (c) reasoning rules — the opposite of opaque prompt completion.
- **Temporal reasoning.** Allen-algebra canonical relation types make "what happened before/after/during X?" questions answerable structurally.

## Integration patterns

- **GraphRAG.** Retrieve a subgraph (entity + event + temporal neighbors), then prompt the LLM with the subgraph and spans. See [edge2024graphrag].
- **Tool-augmented reasoning.** Expose the diagnostics query pack and `temporal_reasoning_profile` to the LLM as tools; let it verify its own claims against the graph.
- **Refusal / hedging.** Let the LLM defer answers for which the graph lacks evidence rather than hallucinate.

## Limits / risks

- KG construction is lossy; an LLM grounded only in the graph loses nuance present in the source text. Both should be available.
- LLM outputs that modify the graph must be fed back through the same contract pipeline; bypassing contracts defeats the point.

## References

- [lewis2020rag]
- [edge2024graphrag]
- [hogan2021kg]
- [hur2024unifying]

## See also

- [`for-context-engineering.md`](for-context-engineering.md)
- [`for-symbolic-ai.md`](for-symbolic-ai.md)
- [`use-cases.md`](use-cases.md)
- [`integration-patterns.md`](integration-patterns.md)
