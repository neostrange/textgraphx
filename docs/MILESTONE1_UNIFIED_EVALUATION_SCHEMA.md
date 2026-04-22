# Milestone 1: Unified Evaluation Schema with Validity Headers

## Overview

Milestone 1 establishes the foundational evaluation framework that ensures all evaluation artifacts (metrics, reports, datasets) are self-certifying and fully comparable. This addresses the core problem: **without provenance, we cannot trust evaluation comparisons or rule out confounding factors**.

## Problem Statement

Previous evaluation reports lacked:
1. **Parameter documentation**: We don't know which dataset, config, or seed was used
2. **Feature activation evidence**: Is fusion/enrichment actually producing edges?
3. **Comparability guarantees**: Can we safely compare two reports?
4. **Reproducibility proof**: Did this result come from a deterministic process?

These gaps make it impossible to validate improvements or identify performance regressions confidently.

## Solution Components

### 1. **RunMetadata** — Complete Run Parameter Fingerprint

```python
@dataclass
class RunMetadata:
    dataset_hash: str           # SHA256 of dataset file metadata
    config_hash: str            # SHA256 of deployment config
    seed: int                   # Random seed
    strict_gate_enabled: bool   # Transition gate status
    fusion_enabled: bool        # Cross-document fusion status
    cleanup_mode: str           # "full" | "auto" | "none"
    timestamp: str              # ISO 8601 UTC timestamp
    duration_seconds: Optional[float]  # Elapsed time
```

Every evaluation run captures its complete parameter set. These hashes are **stable** and **order-independent**, making metadata comparable.

### 2. **ValidityHeader** — Certification Layer

```python
@dataclass
class ValidityHeader:
    run_metadata: RunMetadata
    determinism_checked: bool
    determinism_pass: Optional[bool]  # None=not checked, True=passed, False=failed
    feature_activation_evidence: Dict[str, Any]  # {"same_as_edges": 42, ...}
    inconclusive_reasons: list[str]   # Why this result is unreliable
```

The validity header certifies:
- ✓ **What parameters were used** (run_metadata)
- ✓ **Whether it's reproducible** (determinism_checked/pass)
- ✓ **Whether features activated** (feature_activation_evidence)
- ✓ **Whether the result is conclusive** (inconclusive_reasons)

### 3. **UnifiedMetricReport** — Self-Certifying Artifact Container

```python
@dataclass
class UnifiedMetricReport:
    metric_type: str
    validity_header: ValidityHeader
    metrics: Dict[str, Any]
    evidence: Dict[str, Any]  # Supporting breakdown
    metadata: Dict[str, Any]  # Additional context
```

All evaluation results (edges, mentions, phases) wrap their metrics in this container, which includes the validity header as a required first-class member.

### 4. **Determinism Verification** — Reproducibility Proof

The `determinism` module compares repeated runs (with identical parameters) to verify:
- Do metrics match exactly?
- Are any features or edge types different?
- Is the randomness controlled?

```python
report = compare_metric_results(results1, results2, tolerance=0.0)
report.conclusive  # True if deterministic within tolerance
report.violations  # List of differing metrics
```

### 5. **Feature Activation Detection** — Ensuring Studies Are Valid

Before claiming fusion/enrichment "didn't help," verify it actually activated:

```python
conclusive, reasons = check_fusion_activation(
    fusion_enabled=True,
    same_as_count=42,  # If 0, fusion didn't produce expected edges
    co_occurs_count=15
)
# Returns (True, []) if conclusive
# Returns (False, ["fusion_enabled=true but SAME_AS edges=0"]) if inconclusive
```

Inconclusive results are marked and excluded from comparisons.

### 6. **Standardized Runner** — Automated Report Generation

`StandardizedEvaluationRunner` encapsulates the evaluation process:
- Automatically computes dataset/config hashes
- Tracks runtime parameters
- Creates unified reports with validity headers

```python
runner = StandardizedEvaluationRunner(
    dataset_paths=[Path("gold.json")],
    config_dict={"model": "gpt4"},
    seed=42,
    strict_gate_enabled=True,
    fusion_enabled=False,
)

meta = runner.create_run_metadata(datetime.now(), elapsed=45.5)
report = runner.create_report(
    metric_type="edge_metrics",
    metrics={"precision": 0.85},
    run_metadata=meta,
    determinism_pass=True,
)

report.to_json_file(Path("metrics.json"))
```

## Module Structure

```
textgraphx/evaluation/
├── __init__.py                    # Public API
├── report_validity.py             # RunMetadata, ValidityHeader, hashing
├── determinism.py                 # Run comparison, reproducibility checking
├── unified_metrics.py             # UnifiedMetricReport, factory
└── integration.py                 # StandardizedEvaluationRunner, loaders
```

## Rendered Output Examples

### YAML Frontmatter (for markdown reports)

```yaml
---
run_metadata:
  dataset_hash: "abc123def456"
  config_hash: "xyz789abc123"
  seed: 42
  strict_gate_enabled: true
  fusion_enabled: false
  cleanup_mode: "auto"
  timestamp: "2026-04-05T12:00:00Z"
  duration_seconds: 45.5
determinism_checked: true
determinism_pass: true
feature_activation_evidence: {}
inconclusive_reasons: []
is_conclusive: true
---
```

### JSON Export (for programmatic access)

```json
{
  "metric_type": "edge_metrics",
  "validity_header": {
    "run_metadata": { ... },
    "determinism_checked": true,
    "determinism_pass": true,
    "feature_activation_evidence": {"same_as_edges": 42},
    "inconclusive_reasons": [],
    "is_conclusive": true
  },
  "metrics": {
    "precision": 0.85,
    "recall": 0.90
  },
  "evidence": {
    "edge_types": {"SAME_AS": 42, "CO_OCCURS": 15}
  }
}
```

## Key Guarantees

### 1. **Identical Parameters = Comparable Reports**
If two reports have the same run_metadata hash, they used the same dataset, config, and seed. Direct metric comparison is valid.

### 2. **Determinism ∈ Report**
Every report states whether its metrics were verified as reproducible. Non-deterministic results are explicitly marked.

### 3. **Feature Activation Tracked**
If fusion is enabled but creates zero edges, the report is marked inconclusive. No false comparisons based on disabled features.

### 4. **Self-Certifying Artifacts**
A report's validity is proven, not asserted. Anyone can verify:
- Dataset hash by recomputing from the file list
- Determinism by running twice with the same seed
- Feature activation by checking edge counts

## Integration with Evaluation Phases

Each phase (Mention Layer, Edge Semantics, etc.) produces reports by:

1. **Creating run metadata** from pipeline parameters
2. **Computing metrics** in the usual way
3. **Wrapping metrics** in UnifiedMetricReport
4. **Running determinism check** (optional: on second iteration)
5. **Serializing** to JSON or markdown with validity header

Example:

```python
from textgraphx.evaluation import (
    StandardizedEvaluationRunner,
    create_unified_report,
)

# During evaluation
runner = StandardizedEvaluationRunner(
    dataset_paths=gold_files,
    config_dict=cfg.to_dict(),
    seed=args.seed,
    strict_gate_enabled=args.strict_gate,
    fusion_enabled=args.fusion,
)

start = datetime.now()
metrics = compute_edge_metrics(...)  # Existing logic
elapsed = (datetime.now() - start).total_seconds()

meta = runner.create_run_metadata(start, elapsed)
report = runner.create_report(
    metric_type="edge_metrics",
    metrics=metrics,
    run_metadata=meta,
    determinism_pass=None,  # Will be checked in next run
    evidence={"edge_types": breakdown},
)

report.to_json_file(Path("reports/edges.json"))
report_md = report.to_markdown_with_header()
Path("reports/edges.md").write_text(report_md)
```

## Testing & Validation

All 25 tests in `test_unified_evaluation_schema.py` pass, covering:
- RunMetadata serialization and hashing
- ValidityHeader creation and rendering (YAML/JSON)
- Dataset and config hash computation (order-invariant, deterministic)
- Determinism comparison with tolerance
- Feature activation detection
- Report creation, export, and loading
- StandardizedEvaluationRunner initialization and metadata creation

## Next Steps (Milestones 2–7)

1. **Milestone 2**: Integrate into MentionLayer evaluation
2. **Milestone 3**: Integrate into EdgeSemantics evaluation
3. **Milestone 4+**: Extend to all phases, add end-to-end harness

Each phase will use the unified schema automatically, producing self-certifying reports.

## Quick Reference

| Class/Function | Purpose |
|---|---|
| `RunMetadata` | Captures dataset hash, config hash, seed, feature flags, timestamp |
| `ValidityHeader` | Certifies reproducibility, feature activation, conclusiveness |
| `UnifiedMetricReport` | Container for metrics + validity header |
| `create_unified_report()` | Factory to create reports with all required fields |
| `compare_metric_results()` | Determinism verification (compare two runs) |
| `check_fusion_activation()` | Verify feature produced expected effects |
| `StandardizedEvaluationRunner` | Orchestrator for unified evaluation runs |
| `load_evaluation_report()` | Deserialize saved reports |
