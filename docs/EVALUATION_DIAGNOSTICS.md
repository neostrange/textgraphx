# MEANTIME Evaluation Diagnostics & Boundary Analysis

## Boundary Philosophy: KG vs. NLP Benchmarks
During our evaluation cycle (April 2026), we observed a significant delta between **Strict F1** and **Relaxed F1** scores for Entity and Event extraction.
*   **Entity Strict F1:** ~0.139
*   **Event Strict F1:** ~0.232

### The Cause of Strict F1 Penalties
A script-based diagnostic pulling literal mismatch strings from the graph revealed that the NLP benchmark (MEANTIME) expects exceptionally wide contextual spans. 

**Examples of Mismatches:**
*   *System Prediction:* `Airbus Industrie`
*   *MEANTIME Gold Bound:* `Airbus Industrie , the European aerospace consortium`

*   *System Prediction:* `a stock market`
*   *MEANTIME Gold Bound:* `. The Dow Jones Industrial Average , a stock market index used to gauge the performance of American stock`

### Architectural Decision
**We will NOT configure Cypher rules to "game" the Strict F1 metric.** 
Inflating string boundaries to capture trailing appositives, full relative clauses, and leading punctuation fundamentally degrades the utility of a Knowledge Graph. A KG relies on tight, atomic nodes (like `Airbus Industrie`) connected by explicit edges (like `IS_A` -> `European aerospace consortium`). Storing paragraph-length tokens as uniform nodes destroys our ability to perform localized graph traversals and temporal reasoning.

### Forward Strategy
1.  **Benchmarking:** We will prioritize **Relaxed F1** to measure whether our system is targeting the correct general span containing the information.
2.  **Graph Construction:** We will maintain tight dependency-based noun chunks.
3.  **Future Enhancements:** We must focus on **Relation Extraction (e.g., co-reference and appositive linking)** rather than artificially widening node boundaries.
