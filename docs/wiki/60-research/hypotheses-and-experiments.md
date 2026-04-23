<!-- last_reviewed: 2026-04-23 | owner: core | status: draft | review_interval_days: 90 -->

# Hypotheses and Experiments

**Gateway** · **Wiki Home** · **Research** · Hypotheses and Experiments

## Abstract

A working list of testable hypotheses the system's design permits, along with experimental shapes that could answer them.

## H-1. Contract-first extraction catches more real failures than narrative docs alone.

- **Experiment.** Introduce a synthetic contract-violating mutation in a sample of documents; measure how much is caught by phase assertions vs human review alone.
- **Metric.** Detection rate, time-to-detect.

## H-2. MEANTIME-gold structural alignment is a stronger regression signal than span P/R/F.

- **Experiment.** Track both signals across a quarter of pipeline changes; measure how often each flags a real regression vs noise.
- **Metric.** True-positive rate on identified regressions.

## H-3. Conservative TLINK closure improves downstream QA without introducing contradictions.

- **Experiment.** Compare QA accuracy with vs without closure; measure `contradiction_pair` counts under each policy.
- **Metric.** QA accuracy + contradiction count.

## H-4. GraphRAG grounded in TextGraphX outperforms passage-level RAG on temporal QA.

- **Experiment.** Benchmark on TempEval-3-style questions with both retrieval backbones.
- **Metric.** Answer accuracy + citation precision.

## H-5. Event coreference gains from canonical-mention duality more than from cross-document embeddings.

- **Experiment.** Ablate the `EventMention → TEvent` canonicalization vs a pure embedding clustering baseline.
- **Metric.** Event B³/CEAF/MUC trio.

## See also

- [`open-questions.md`](open-questions.md)
- [`../55-evaluation-strategy/how-to-add-an-evaluator.md`](../55-evaluation-strategy/how-to-add-an-evaluator.md)
