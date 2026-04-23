<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Use Cases

**Gateway** · **Wiki Home** · **Applications** · Use Cases

## Abstract

Concrete downstream applications enabled by an event-centric temporal KG over text.

## Exemplar use cases

- **Timeline construction.** Assemble per-entity or per-topic timelines from a corpus; answer "who did what when".
- **Regulatory / compliance auditing.** Extract event chains (approvals, filings, decisions) with temporal anchoring and citations for review.
- **Narrative summarization.** Produce event-skeleton summaries rather than flat extractive ones.
- **Temporal QA.** Answer before/after/during questions with graph-path explanations.
- **Corpus-level analysis.** Study the distribution of event types, participant roles, or temporal-connective usage across a corpus subset.
- **Grounded RAG.** Serve LLM-facing grounding with entity, event, and temporal context rather than flat passages.
- **Consistency-checked extraction.** Use the system's contract layer to audit a third-party extraction pipeline's output.

## What makes each work in TextGraphX

- Typed canonical nodes give each use case a stable anchor.
- Temporal reasoning profile lets "before/after/during" be a structural query, not a language task.
- Diagnostics and contracts mean every use case can be audited for soundness before downstream consumption.

## References

- [hur2024unifying]
- [edge2024graphrag]
- [hogan2021kg]

## See also

- [`integration-patterns.md`](integration-patterns.md)
- [`for-llm-genai.md`](for-llm-genai.md)
- [`for-context-engineering.md`](for-context-engineering.md)
