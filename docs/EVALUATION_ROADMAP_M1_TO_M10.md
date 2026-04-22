# Complete Evaluation Roadmap: From M1-M7 to Real Goal

**Current Status**: Just completed Milestones 1-7 (Unified Phase Evaluation)  
**Overall Goal**: End-to-end proof of reproducible, high-quality knowledge graph pipeline

---

## 🎯 The Real Goal

Transform TextGraphX from a "pipeline that produces graphs" -> **"a validated, reproducible system where every output can be certified for quality, determinism, and completeness."**

### Success Criteria
1. **Quality**: Gold-standard validation (MEANTIME recall/precision/F1 > threshold)
2. **Reproducibility**: Two runs with same config produce identical results (determinism proof)
3. **Completeness**: All pipeline phases materialize expected outputs
4. **Traceability**: Every metric backed by parameter documentation
5. **Automation**: CI/CD gates based on quality thresholds

---

## 📊 Evaluation Layer Stack

```
┌─────────────────────────────────────────────────────────┐
│          LAYER 4: CI/CD Gating & Reporting              │
│  (Quality thresholds, merge gates, automated alerts)     │
└────────────────────┬────────────────────────────────────┘
                     ↑
┌─────────────────────────────────────────────────────────┐
│        LAYER 3: End-to-End Validation Harness           │
│  (Cross-phase consistency, determinism + MEANTIME)       │
│  📦 NEW MILESTONE 8                                      │
└────────────────────┬────────────────────────────────────┘
                     ↑
┌─────────────────────────────────────────────────────────┐
│    LAYER 2: External Standard Validation (MEANTIME)     │
│  (Precision/Recall/F1 against gold XML)                  │
│  ✅ EXISTING: evaluate_meantime.py CLI                  │
└────────────────────┬────────────────────────────────────┘
                     ↑
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: Phase-Level Evaluation (M1-M7)                │
│  (Unified validity headers, determinism, feature proof)  │
│  ✅ COMPLETED: 5 phase evaluators + orchestrator        │
└─────────────────────────────────────────────────────────┘
```

---

## 🛣️ Complete Roadmap (8 Milestones → Real Goal)

### ✅ **M1-M7: COMPLETE** 
**Unified Phase Evaluation Framework**
- ✅ Validity headers with parameter documentation
- ✅ Determinism verification 
- ✅ Feature activation tracking
- ✅ 5 phase evaluators (Mention Layer, Edge Semantics, Phase Assertions, etc.)
- ✅ Full-stack orchestrator with JSON/Markdown/CSV export
- ✅ 44 passing tests

**What this gives you**:
- Every phase report includes RunMetadata (dataset hash, config hash, seed, timestamp)
- Can compare two reports for identity
- Can mark results as "inconclusive" if features didn't activate
- Can verify reproducibility

**What it doesn't cover**:
- Comparison to external gold standard (MEANTIME)
- Cross-phase consistency validation
- CI/CD integration
- Automated quality gating

---

### 🔄 **M8: NEXT - End-to-End Validation Harness**
**Bridge M1-M7 with MEANTIME evaluation + cross-phase constraints**

#### 8a: MEANTIME Integration Bridge (M8a)
**Integrate unified metrics with gold-standard evaluation**

Files to create:
- `textgraphx/evaluation/meantime_bridge.py`: Adapter between M1-M7 reports and MEANTIME evaluator
- `textgraphx/evaluation/cross_phase_validator.py`: Cross-phase consistency checks

Purpose:
- Take UnifiedMetricReport from M7 full-stack evaluator
- Run MEANTIME evaluation in parallel against gold XML
- Combine phase-level scores with MEANTIME precision/recall/F1
- Report consolidated "quality index" combining both perspectives

Example workflow:
```python
from textgraphx.evaluation import FullStackEvaluator
from textgraphx.evaluation.meantime_bridge import MEANTIMEBridge

# Run unified evaluation (M1-M7)
evaluator = FullStackEvaluator(graph, dataset_paths, config)
suite = evaluator.evaluate()

# Compare against MEANTIME gold standard
bridge = MEANTIMEBridge(
    gold_xml_path=Path("gold/document.xml"),
    evaluation_mapping={...},  # Entity/event/timex attribute mappings
)
meantime_results = bridge.evaluate_against_gold(suite)

# Get consolidated quality report
consolidated_report = bridge.consolidate(suite, meantime_results)
print(f"Phase Quality: {suite.overall_quality():.4f}")  # M1-M7
print(f"MEANTIME F1: {meantime_results.macro_f1:.4f}")   # Gold comparison
print(f"Consolidated: {consolidated_report.overall_score:.4f}")  # Combined
```

**Tests needed** (15 tests):
- Bridge instantiation and configuration
- MEANTIME metrics aggregation
- Score consolidation (weighted average of phase + MEANTIME)
- Feature activation vs MEANTIME coverage correlation
- Determining when phase quality doesn't match MEANTIME (diagnostic)

**Why it matters**:
- Phase evaluators tell you "the pipeline is complete"
- MEANTIME evaluator tells you "the output quality is high"
- Combined: "We have a complete, high-quality system"

---

#### 8b: Cross-Phase Consistency Validator (M8b)
**Ensure semantic coherence across phase boundaries**

Files to create:
- `textgraphx/evaluation/cross_phase_validator.py`: Consistency rules

Purpose:
- Verify Phase 1 → Phase 4 invariants (mention mentions should have edge properties)
- Check Phase 4 → Phase 5 assumptions (edges should have semantic categories)
- Detect "orphaned" nodes (created by one phase, not consumed by later phase)
- Check backward compat consistency (M6 validates but we can go deeper)

Example constraints to validate:
1. **Phase cascade**: Every EventMention (M2) should have semantics from M3
2. **Sanity checks**: If M5 categorized frames, check M3 created appropriate edges
3. **Density**: If fusion (M3) is enabled, expect certain SAME_AS/CO_OCCURS counts
4. **Backward compat**: Every Entity→TEvent relationship from M6 should also have Entity→EventMention path

```python
validator = CrossPhaseValidator(graph, phase_reports)
consistency_report = validator.validate()

# Returns violations like:
# - "1250 EventMentions created, but only 1100 have category evidence"
# - "Fusion enabled but SAME_AS edge count suspiciously low (expected 1000, got 20)"
# - "42 orphaned EventMention nodes with no Frame INSTANTIATES"
```

**Tests needed** (12 tests):
- Invariant checking logic
- Orphan detection
- Density thresholds
- Sanity check rules
- Backward compatibility edges

---

#### 8c: Consolidated Report Builder (M8c)
**Single report combining M1-M7 + MEANTIME + cross-phase checks**

```python
consolidated = ConsolidatedEvaluationReport(
    unified_suite=suite,           # M1-M7 results
    meantime_results=meantime,     # Gold standard validation
    cross_phase_checks=consistency # Phase boundary checks
)

# Properties:
consolidated.overall_quality       # 0.0-1.0 across all dimensions
consolidated.breakdown()           # Quality by dimension
consolidated.passed_quality_gate() # True if > threshold
consolidated.to_markdown()         # Rich markdown for humans
consolidated.to_json()             # Machine-readable
consolidated.to_ci_report()        # GitHub Actions / CI format
```

---

### 🏗️ **M9: NEXT NEXT - Determinism Gate & Regression Detection**

**Purpose**: Ensure pipeline improvements are real (not random variation)

#### 9a: Baseline Capture
```python
# First production run - save as baseline
baseline_suite = evaluator.evaluate()
baseline_suite.to_json_file(Path("baselines/v1.0.json"))

# Run again - check for regressions
current_suite = evaluator.evaluate()
regression_report = compare_against_baseline(baseline_suite, current_suite)
# Returns: quality_delta, regressions (phases that got worse)
```

#### 9b: Determinism Verification
```python
# Run twice with same seed, ensure identical results
suite1 = evaluator.evaluate(seed=42)
suite2 = evaluator.evaluate(seed=42)

is_deterministic, violations = compare_evaluation_suites(suite1, suite2, tolerance=0.0)
# If false, report which phases are non-deterministic
```

#### 9c: Statistical Significance
```python
# Run 5x with different random seeds
suites = [evaluator.evaluate(seed=i) for i in range(5)]
variance_report = compute_variance(suites)

print(f"Quality variance: mean={variance_report.mean:.4f}, std={variance_report.std:.4f}")
print(f"Confidence: {variance_report.confidence_interval}")
```

---

### 🚀 **M10: CI/CD Integration & Quality Gates**

**Purpose**: Automate quality, make it enforceable

#### 10a: GitHub Actions Workflow
```yaml
name: Evaluation Gate
on: [pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Full Evaluation
        run: |
          python -m textgraphx.evaluation.run_consolidated \
            --dataset gold/ \
            --output eval_report.json
      
      - name: Check Quality Gate
        run: |
          python -c "
          import json
          with open('eval_report.json') as f:
              report = json.load(f)
          assert report['overall_quality'] >= 0.85, 'Quality < 0.85'
          assert report['meantime_f1'] >= 0.80, 'MEANTIME F1 < 0.80'
          assert report['deterministic'], 'Non-deterministic'
          "
      
      - name: Comment on PR
        if: success()
        run: |
          # Post evaluation report as PR comment for visibility
```

#### 10b: Local Pre-commit Hook
```bash
#!/bin/bash
# In .git/hooks/pre-commit
python -m textgraphx.evaluation.run_consolidated --quick
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
  echo "Evaluation gate failed. Run with --full for details."
  exit 1
fi
```

---

## 📈 Roadmap Timeline

| Milestone | Scope | Tests | Code | Time |
|-----------|-------|-------|------|------|
| **M1-M7** | ✅ Phase eval + harness | 44 | ~2500 | DONE |
| **M8** | Bridge + cross-phase | 27 | ~1000 | **NEXT: 2-3 days** |
| **M9** | Regression + variance | 15 | ~800 | **AFTER M8: 1-2 days** |
| **M10** | CI/CD + gates | 10 | ~500 | **AFTER M9: 1 day** |

**Total Timeline**: ~5-7 days to complete real goal ✅

---

## 🎁 Intermediaries & Dependencies

### What You Already Have

1. **MEANTIME Evaluator** (`textgraphx/evaluation/meantime_evaluator.py`)
   - Parses gold XML (entities, events, timex, relations)
   - Computes precision/recall/F1 with strict/relaxed matching
   - Can read from XML or Neo4j projection
   - CLI: `python -m textgraphx.tools.evaluate_meantime`

2. **Phase Assertions** (`textgraphx/phase_assertions.py`)
   - Contract validation after each phase
   - Checks schema compliance, invariants, relationships
   - Already integrated into orchestrator

3. **Integration Tests**
   - `test_integration_phase_assertions.py`: Validates all phases run
   - `test_integration_pipeline_materialization.py`: Checks output density
   - `test_smoke_e2e.py`: End-to-end smoke test

### What M8-M10 Will Connect

```
M1-M7 (Phase Metrics)
      ↓
    [M8a: Bridge]    ← New: Connect to MEANTIME
      ↓
M1-M7 + MEANTIME  ← Two evaluation streams
      ↓
    [M8b: Validator]  ← New: Cross-phase checks
      ↓
Consolidated Report
      ↓
    [M9: Regression]  ← New: Variance & baselines
      ↓
Determinism Proof + Baselines
      ↓
    [M10: CI/CD]     ← New: Automated gates
      ↓
✅ Production-Ready Pipeline
```

---

## 🎯 What Each Milestone Answers

| Milestone | Question | Answer |
|-----------|----------|--------|
| **M1-M7** | Is the pipeline running? | ✅ Reports on all 5 phases |
| **M8a** | Does it make sense linguistically? | ✅ Comparison to gold standard |
| **M8b** | Are all phases coherent together? | ✅ Cross-phase consistency |
| **M9** | Is the improvement real or random? | ✅ Determinism + variance proof |
| **M10** | Is this safe to deploy? | ✅ Automated quality gates |

---

## 🚀 How to Proceed

### Immediate Next Steps (M8a - MEANTIME Bridge):

```python
# Step 1: Create the adapter
# File: textgraphx/evaluation/meantime_bridge.py
class MEANTIMEBridge:
    def __init__(self, gold_xml_path, evaluation_mapping):
        # Load gold standard
        # Initialize evaluator
    
    def evaluate_against_gold(self, unified_suite):
        # Run MEANTIME evaluation
        # Return results in standard format
    
    def consolidate(self, unified_suite, meantime_results):
        # Combine M1-M7 scores with MEANTIME scores
        # Return consolidated report

# Step 2: Integration test
# tests/test_meantime_bridge.py
def test_bridge_consolidation():
    # Verify bridge combines metrics correctly
```

### Then M8b - Cross-Phase Validator:

```python
# File: textgraphx/evaluation/cross_phase_validator.py
class CrossPhaseValidator:
    def validate(self):
        # Check phase invariants
        # Detect orphaned nodes
        # Verify cascade semantics
        # Return violation report
```

---

## 📊 Expected Output Example

After M8-M10 complete, running evaluation will produce:

```json
{
  "timestamp": "2026-04-05T12:00:00Z",
  "run_metadata": {
    "dataset_hash": "abc123...",
    "config_hash": "xyz789...",
    "seed": 42
  },
  "evaluation_layers": {
    "phase_metrics": {
      "mention_layer": 0.9856,
      "edge_semantics": 0.8740,
      "phase_assertions": 0.9500,
      "semantic_categories": 0.8200,
      "legacy_layer": 0.9800,
      "overall": 0.8819
    },
    "meantime_validation": {
      "entity_f1": 0.8750,
      "event_f1": 0.8200,
      "timex_f1": 0.7900,
      "relation_f1": 0.7650,
      "macro_f1": 0.8125
    },
    "cross_phase_consistency": {
      "phase_cascade_violations": 0,
      "orphaned_nodes": 0,
      "density_checks_passed": true,
      "score": 1.0
    },
    "determinism": {
      "run_pairs_tested": 5,
      "deterministic": true,
      "variance_std": 0.0012
    }
  },
  "consolidated_quality": {
    "score": 0.8441,  # Weighted: 40% phases, 40% MEANTIME, 20% consistency
    "passed_quality_gate": true,
    "quality_tier": "PRODUCTION_READY"
  },
  "regression_analysis": {
    "vs_baseline_v1_0": {
      "quality_delta": -0.0050,
      "status": "ACCEPTABLE",
      "confidence": 0.95
    }
  }
}
```

---

## Summary: Where We Stand

### ✅ Completed (M1-M7)
- 5 phase evaluators with unified validity headers
- Determinism verification embedded in every report
- Feature activation tracking
- 44 passing tests
- Ready for production phase validation

### 🔄 Next (M8-M10)
- Connect to MEANTIME gold-standard evaluation
- Validate cross-phase coherence
- Prove statistical significance and regression-free
- Set up CI/CD quality gates
- Achieve "Production Ready" certification

### 🎯 Real Goal
**A TextGraphX pipeline you can confidently say**: 
> "Every output is reproducible, validated against gold standards, phase-coherent, and statistically significant."

---

Want me to start building M8a (MEANTIME Bridge) right now? 🚀
