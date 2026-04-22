# Milestones 2-7: Phase-Specific Evaluators and Full-Stack Harness

**Date**: April 5, 2026  
**Status**: ✅ Complete (19 passing tests)

---

## Overview

Milestones 2-7 implement unified evaluation for all semantic enrichment phases, integrating with the Milestone 1 validity header framework. Each phase gets a dedicated evaluator that produces self-certifying reports with embedded reproducibility proof.

### Milestones Summary

| Milestone | Phase | Purpose | Status |
|-----------|-------|---------|--------|
| **M2** | Mention Layer (Phase 1) | EntityMention/EventMention introduction | ✅ Complete |
| **M3** | Edge Semantics (Phase 4) | Semantic edge enrichment | ✅ Complete |
| **M4** | Phase Assertions | Output contract validation | ✅ Complete |
| **M5** | Semantic Categories | Frame categorization quality | ✅ Complete |
| **M6** | Legacy Layer | Backward compatibility preservation | ✅ Complete |
| **M7** | Full-Stack Harness | End-to-end orchestration | ✅ Complete |

---

## Milestone 2: Mention Layer Integration

### Purpose
Evaluates that explicit mention-level semantics (EntityMention, EventMention) are correctly introduced and linked to canonical entities/events.

### Implementation: `textgraphx/evaluation/mention_layer_evaluator.py`

**MentionLayerEvaluator** measures:
- EntityMention node creation and REFERS_TO linkage
- EventMention node creation and REFERS_TO linkage  
- Frame → INSTANTIATES → EventMention relationships
- Backward compatibility (Entity→TEvent relationships still exist)

**Metrics**:
- `entity_mentions_created`: Total EntityMention nodes
- `entity_mentions_with_refers_to`: EntityMentions linked to Entity
- `event_mentions_created`: Total EventMention nodes
- `event_mentions_with_refers_to`: EventMentions linked to TEvent
- `frame_instantiates_event_mention`: Frame→EventMention links
- `backward_compatibility_violations`: Old relationships broken (should be 0)

**Quality Score**: Weighted average of:
- Entity mention REFERS_TO rate (30%)
- Event mention REFERS_TO rate (30%)
- Frame instantiation coverage (40%)

**Report Type**: `mention_layer_metrics`

**Example Report**:
```json
{
  "metric_type": "mention_layer_metrics",
  "validity_header": {...},
  "metrics": {
    "entity_mentions_created": 1250,
    "entity_mentions_with_refers_to": 1245,
    "event_mentions_created": 850,
    "event_mentions_with_refers_to": 848,
    "quality_score": 0.9856,
    "entity_mention_refers_to_rate": 0.996
  },
  "evidence": {
    "mention_types": {
      "entity_mentions": 1250,
      "event_mentions": 850
    }
  }
}
```

---

## Milestone 3: Edge Semantics Integration

### Purpose
Evaluates semantic typing and relationship enrichment (SAME_AS, CO_OCCURS, INSTANTIATES, etc.).

### Implementation: `textgraphx/evaluation/edge_semantics_evaluator.py`

**EdgeSemanticsEvaluator** measures:
- Total edges and typed edges
- Distribution of semantic types (SAME_AS, CO_OCCURS, PARTICIPANT, etc.)
- Semantic coherence violations (e.g., SAME_AS between incompatible types)
- Typing coverage rate

**Metrics**:
- `total_edges`: All relationships in graph
- `typed_edges`: Relationships with explicit type property
- `same_as_edges`: SAME_AS relationships
- `co_occurs_edges`: CO_OCCURS relationships
- `semantic_coherence_violations`: Type inconsistencies

**Quality Score**: 
- Typing coverage (50%)
- Coherence score (50%)

**Evidence**: Edge distribution breakdown by type

---

## Milestone 4: Phase Assertions and Contract Validation

### Purpose
Verifies that phase outputs satisfy published semantic contracts (schema compliance, invariants, constraints).

### Implementation: `textgraphx/evaluation/phase_assertion_evaluator.py`

**PhaseAssertionEvaluator** checks:
- Schema compliance (required properties exist)
- Phase invariants (e.g., every EventMention has REFERS_TO)
- Temporal consistency (span boundaries valid)
- Semantic consistency (no orphaned relationships)

**Metrics**:
- `total_nodes_checked`: Nodes validated
- `nodes_meeting_schema`: Nodes satisfying schema
- `schema_violations`: Required properties missing
- `phase_invariant_violations`: Invariants violated
- `temporal_consistency_violations`: Invalid spans
- `semantic_consistency_violations`: Orphaned edges

**Quality Score**: Linear 0-1 based on violation count

**Invariants Checked**:
- Every EventMention has REFERS_TO relationship
- Span boundaries: `start_tok < end_tok`
- No references to non-existent nodes

---

## Milestone 5: Semantic Categories Integration

### Purpose
Evaluates semantic frame categorization quality and consistency.

### Implementation: `textgraphx/evaluation/semantic_category_evaluator.py`

**SemanticCategoryEvaluator** measures:
- Frame categorization coverage
- Category consistency (frames with same predicate have coherent categories)
- Orphaned categories (unused SemanticCategory nodes)

**Metrics**:
- `total_frames`: All Frame nodes
- `frames_with_categories`: Frames with HAS_CATEGORY relationships
- `category_consistency_violations`: Inconsistent assignments
- `categorization_coverage`: % of frames categorized

**Quality Score**:
- Coverage (60%)
- Consistency (40%)

**Feature Activation**: Checked if `frames_with_categories > 0`

---

## Milestone 6: Legacy Layer Backward Compatibility

### Purpose
Ensures that legacy data patterns remain accessible after semantic upgrades (dual-label nodes, dual-path relationships).

### Implementation: `textgraphx/evaluation/legacy_layer_evaluator.py`

**LegacyLayerEvaluator** validates:
- Legacy node preservation (NamedEntity, TEvent, Frame still exist)
- Legacy relationship preservation (PARTICIPANT, DESCRIBES still work)
- Dual-labeled migration (NamedEntity AND EntityMention on same node)
- Dual-path availability (old and new paths both exist)
- Orphaned legacy data detection

**Metrics**:
- `legacy_nodes_total`: Legacy node count
- `legacy_nodes_active`: Active legacy nodes
- `migration_dual_nodes`: Nodes with both old and new labels
- `migration_dual_rels`: Relationships available via both paths
- `legacy_orphans`: Legacy data without new counterparts

**Quality Score**:
- Returns 0.0 if orphans exist (broken migration)
- Otherwise: Average of preservation rates

**Migration Status**: Reports percentage of dual-labeled nodes and dual-path relationships

---

## Milestone 7: Full-Stack Unified Evaluation Harness

### Purpose
Single entry point for complete pipeline evaluation with orchestrated phase reports, determinism verification, and comprehensive exports.

### Implementation: `textgraphx/evaluation/fullstack_harness.py`

**FullStackEvaluator** orchestrates:
1. Runs all 5 phase evaluations (M2-M6)
2. Collects RunMetadata from shared runner
3. Returns `EvaluationSuite` with all reports
4. Supports JSON, Markdown, and CSV export

**EvaluationSuite** provides:
```python
@property
def all_reports(self) -> List[UnifiedMetricReport]:
    """All 5 phase reports"""
    return [mention_layer, edge_semantics, phase_assertions, 
            semantic_categories, legacy_layer]

def quality_scores(self) -> Dict[str, float]:
    """Quality by phase"""
    
def overall_quality(self) -> float:
    """Macro-average across all phases"""
    
def conclusiveness(self) -> tuple[bool, List[str]]:
    """Overall conclusiveness + reasons for any inconclusiveness"""
```

### Export Formats

**JSON Export**:
```json
{
  "run_metadata": {...},
  "execution_time_seconds": 45.3,
  "quality_scores": {
    "mention_layer": 0.9856,
    "edge_semantics": 0.8740,
    ...
  },
  "overall_quality": 0.8913,
  "conclusiveness": {
    "conclusive": true,
    "reasons": []
  },
  "reports": {
    "mention_layer_metrics": {...},
    "edge_semantics_metrics": {...},
    ...
  }
}
```

**Markdown Export**:
- Main header with overall quality and conclusiveness
- Quality scores summary table
- Individual phase reports with validity headers (YAML frontmatter)
- Full metrics and evidence for each phase

**CSV Export**:
- Flattened format for easy comparison across runs
- Columns: metric_type, overall_quality, phase_quality, conclusive, seed, fusion_enabled

### Usage Example

```python
from textgraphx.evaluation import FullStackEvaluator
from pathlib import Path
from textgraphx.neo4j_client import make_graph_from_config

# Initialize evaluator
graph = make_graph_from_config()
evaluator = FullStackEvaluator(
    graph=graph,
    dataset_paths=[Path("gold/entities.json"), Path("gold/events.json")],
    config_dict={"model": "gpt4", "fusion": True},
    seed=42,
    fusion_enabled=True,
)

# Run evaluation
suite = evaluator.evaluate(determinism_pass=True)

# Check quality
print(f"Overall Quality: {suite.overall_quality():.4f}")
print(f"Conclusive: {suite.conclusiveness()[0]}")

# Export results
evaluator.export_json(suite, Path("results/eval.json"))
evaluator.export_markdown(suite, Path("results/eval.md"))
evaluator.export_csv(suite, Path("results/eval.csv"))
```

### Determinism Verification

Compare two evaluation suites:

```python
from textgraphx.evaluation import compare_evaluation_suites

is_consistent, messages = compare_evaluation_suites(
    suite1, suite2, tolerance=0.001
)

if is_consistent:
    print("✓ Runs are deterministic")
else:
    print("✗ Differences detected:")
    for msg in messages:
        print(f"  - {msg}")
```

---

## Shared Infrastructure

All evaluators use common patterns from Milestone 1:

### RunMetadata (Determinism Foundation)
- Dataset hash: Stable encoding of gold data
- Config hash: Stable encoding of runtime config
- Seed: Random seed for reproducibility
- Feature flags: Fusion, strict gate, cleanup mode
- Timestamp: Run start time (ISO 8601 UTC)

### ValidityHeader (Self-Certification)
- `run_metadata`: Complete parameter fingerprint
- `determinism_checked`: Was reproducibility verified?
- `determinism_pass`: Did it pass?
- `feature_activation_evidence`: Proof features activated
- `inconclusive_reasons`: Why result can't be trusted (if any)

### UnifiedMetricReport (Standardized Container)
- `metric_type`: Phase identifier
- `validity_header`: Embedded certification
- `metrics`: Computed metrics
- `evidence`: Supporting breakdown
- `metadata`: Additional context

---

## Test Coverage

**19 comprehensive tests** (all passing):

### M2 Tests (3)
- Mention layer metrics computation
- Quality score calculation
- Unified report creation

### M3 Tests (2)
- Edge semantics metrics
- Report creation

### M4 Tests (2)
- Phase assertion metrics
- Report creation

### M5 Tests (2)
- Semantic category metrics
- Report creation

### M6 Tests (2)
- Legacy layer metrics
- Report creation

### M7 Tests (8)
- Evaluator initialization
- Full suite evaluation
- Quality scores by phase
- Conclusiveness checking
- JSON export
- Markdown export
- CSV export
- Suite serialization

### Comparison Tests (1)
- Suite-to-dict serialization

---

## Integration Workflow

### Before Running Pipeline
```python
from textgraphx.evaluation import FullStackEvaluator
from pathlib import Path

evaluator = FullStackEvaluator(
    graph=graph,
    dataset_paths=list(Path("gold").glob("*.json")),
    config_dict=config,
    seed=args.seed,
    fusion_enabled=args.fusion,
)

# Run baseline
suite_baseline = evaluator.evaluate()
suite_baseline.to_dict()  # Record for comparison
```

### After Running Pipeline
```python
# Run with improvements
suite_improved = evaluator.evaluate()

# Compare directly or export for external analysis
from textgraphx.evaluation import compare_evaluation_suites

consistent, msgs = compare_evaluation_suites(suite_baseline, suite_improved)

if consistent:
    print("✓ Improvement is reproducible")
    print(f"  Overall quality: {suite_baseline.overall_quality():.4f} → {suite_improved.overall_quality():.4f}")
else:
    print("✗ Results vary between runs:")
    for msg in msgs:
        print(f"  {msg}")
```

---

## Key Design Decisions

### 1. **Phase-Specific Evaluators**
Each phase gets its own evaluator focusing on that phase's semantics. This allows:
- Independent testing of each phase
- Clear ownership and documentation
- Composability into full-stack check

### 2. **Unified Container**
All evaluators produce `UnifiedMetricReport` with common structure:
- Guarantees validity headers are always present
- Enables determinism checking across all phases
- Supports standardized export (JSON, CSV, Markdown)

### 3. **Feature Activation Evidence**
Each report tracks what features actually activated:
- Fusion enabled but created 0 edges → inconclusive
- Phase disabled but still ran → marked
- Helps avoid false comparisons

### 4. **Backward Compatibility**
M6 (Legacy Layer) ensures:
- Old code still works (Entity→TEvent still valid)
- New code coexists (Entity→EventMention→TEvent also works)
- Migration is trackable (dual-labeled nodes count)

### 5. **Determinism as First-Class**
- Embedded in every report
- Can be verified independently
- Required for safe comparisons

---

## Quality Metrics Across Phases

| Phase | Dimension 1 | Dimension 2 | Dimension 3 | Overall |
|-------|-------------|-------------|-------------|---------|
| **M2** | Entity REFERS_TO (30%) | Event REFERS_TO (30%) | Frame INSTANTIATES (40%) | Weighted avg |
| **M3** | Typing coverage (50%) | Coherence score (50%) | - | Weighted avg |
| **M4** | Compliance rate | Invariant rate | Violation count | 1.0 - (violations/nodes) |
| **M5** | Categorization coverage (60%) | Consistency (40%) | - | Weighted avg |
| **M6** | Node preservation | Rel preservation | Orphan detection | Weighted avg |
| **M7** | Macro-average across all phases |||| |

**M7 Overall Quality** = Mean of 5 phase quality scores

---

## Next Steps / Future Integration

1. **Threshold-based Gating**: Use quality scores to block merges if below threshold
2. **Trend Tracking**: Store reports over time, track quality trends
3. **Alerting**: Flag regressions (quality drops between runs)
4. **Competitive Evaluation**: Compare different models/configs on same dataset
5. **Automated Report Generation**: CI/CD integration to produce reports on every push

---

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| `mention_layer_evaluator.py` | 180 | M2: Mention layer metrics |
| `edge_semantics_evaluator.py` | 160 | M3: Edge semantics metrics |
| `phase_assertion_evaluator.py` | 160 | M4: Phase contract validation |
| `semantic_category_evaluator.py` | 160 | M5: Category quality |
| `legacy_layer_evaluator.py` | 210 | M6: Backward compatibility |
| `fullstack_harness.py` | 240 | M7: Orchestration + export |
| `test_milestones_2_7.py` | 400 | 19 comprehensive tests |

**Total**: ~1,500 lines of well-tested evaluation code

---

## Verification Checklist

- ✅ All 19 tests pass
- ✅ All evaluators inherit from Unity validity pattern
- ✅ Each evaluator produces `UnifiedMetricReport`
- ✅ FullStackEvaluator successfully orchestrates all 5
- ✅ JSON/Markdown/CSV export all working
- ✅ Mock graph correctly handles all query types
- ✅ Quality scores computed consistently
- ✅ Feature activation evidence tracked
- ✅ Conclusiveness reasons populated correctly
- ✅ Backward compatibility coverage in place

---

## Conclusion

Milestones 1-7 establish a complete, self-certifying evaluation framework that:

1. **Unifies** metric reporting across all phases
2. **Proves** reproducibility through determinism checking
3. **Verifies** feature activation to avoid false comparisons
4. **Enables** meaningful quality tracking and trend analysis
5. **Supports** automated CI/CD integration
6. **Preserves** backward compatibility through migration tracking

The framework is now ready for integration into the main evaluation pipeline and CI/CD workflows.
