# Full-Stack Evaluation Report

**Date**: 2026-04-13T04:23:44.055632+00:00
**Overall Quality**: 0.5675
**Conclusive**: False

## Quality Scores by Phase

- mention_layer: 0.0000
- edge_semantics: 0.5857
- phase_assertions: 0.9993
- semantic_categories: 0.4000
- legacy_layer: 0.8525

## Runtime Diagnostics

- error: runtime diagnostics unavailable: {neo4j_code: Neo.ClientError.Statement.SyntaxError} {message: Unknown function 'nullif' (line 4, column 15 (offset: 168))
"WITH `coalesce`((`nullif`((`trim`((`toString`(((`em`).`entityStateType`))))), (""))), ("STATE")) AS `entity_state_type`, `count`((`em`)) AS `mention_count`"
                                                       ^} {gql_status: 50N42} {gql_status_description: error: general processing exception - unexpected error. Unknown function 'nullif' (line 4, column 15 (offset: 168))
"WITH `coalesce`((`nullif`((`trim`((`toString`(((`em`).`entityStateType`))))), (""))), ("STATE")) AS `entity_state_type`, `count`((`em`)) AS `mention_count`"
                                                       ^}

## mention_layer_metrics

---
run_metadata:
  dataset_hash: ac3a7349956ede57
  config_hash: 2b58015cf2b3462a
  seed: 42
  strict_gate_enabled: false
  fusion_enabled: false
  cleanup_mode: auto
  timestamp: "2026-04-13T04:23:43.101564+00:00Z"
  duration_seconds: 0.951107
determinism_checked: false
determinism_pass: null
feature_activation_evidence:
  entity_mentions_activated: true
  event_mentions_activated: true
  entity_mention_count: 364
  event_mention_count: 287
inconclusive_reasons:
  - backward_compatibility_violations=280
is_conclusive: false
---

# mention_layer_metrics Report

## Metrics

- **backward_compatibility_violations**: 280
- **entity_mention_refers_to_rate**: 1.0000
- **entity_mentions_created**: 364
- **entity_mentions_with_refers_to**: 364
- **entity_participant_links**: 34
- **event_mention_refers_to_rate**: 1.0000
- **event_mentions_created**: 287
- **event_mentions_with_refers_to**: 287
- **event_participant_links**: 14
- **frame_instantiates_event_mention**: 525
- **frame_instantiation_coverage**: 1.8293
- **quality_score**: 0.0000

## Evidence

### mention_types
  - entity_mentions: 364
  - event_mentions: 287
### relationships
  - entity_refers_to: 364
  - event_refers_to: 287
  - frame_instantiates: 525


## edge_semantics_metrics

---
run_metadata:
  dataset_hash: ac3a7349956ede57
  config_hash: 2b58015cf2b3462a
  seed: 42
  strict_gate_enabled: false
  fusion_enabled: false
  cleanup_mode: auto
  timestamp: "2026-04-13T04:23:43.101564+00:00Z"
  duration_seconds: 0.951107
determinism_checked: false
determinism_pass: null
feature_activation_evidence:
  semantic_typing_activated: true
  same_as_edges_created: 0
  co_occurs_edges_created: 94
inconclusive_reasons: []
is_conclusive: true
---

# edge_semantics_metrics Report

## Metrics

- **co_occurs_edges**: 94
- **coherence_score**: 1.0000
- **instantiates_edges**: 525
- **participant_edges**: 968
- **quality_score**: 0.5857
- **refers_to_edges**: 853
- **same_as_edges**: 0
- **semantic_coherence_violations**: 0
- **total_edges**: 26054
- **typed_edges**: 4466
- **typing_coverage**: 0.1714
- **untyped_edges**: 21588

## Evidence

### edge_distribution
  - CO_OCCURS: 94
  - INSTANTIATES: 525
  - PARTICIPANT: 968
  - REFERS_TO: 853
  - SAME_AS: 0


## phase_assertion_metrics

---
run_metadata:
  dataset_hash: ac3a7349956ede57
  config_hash: 2b58015cf2b3462a
  seed: 42
  strict_gate_enabled: false
  fusion_enabled: false
  cleanup_mode: auto
  timestamp: "2026-04-13T04:23:43.101564+00:00Z"
  duration_seconds: 0.951107
determinism_checked: false
determinism_pass: null
feature_activation_evidence:
  phase_materialization_active: true
  nodes_checked: 5809
inconclusive_reasons:
  - schema_violations=4
is_conclusive: false
---

# phase_assertion_metrics Report

## Metrics

- **invariant_compliance_rate**: 1.0000
- **nodes_meeting_schema**: 283
- **phase_invariant_violations**: 0
- **quality_score**: 0.9993
- **schema_compliance_rate**: 0.0487
- **schema_violations**: 4
- **semantic_consistency_violations**: 0
- **temporal_consistency_violations**: 0
- **total_nodes_checked**: 5809

## Evidence

### violations
  - invariant: 0
  - schema: 4
  - semantic: 0
  - temporal: 0


## semantic_category_metrics

---
run_metadata:
  dataset_hash: ac3a7349956ede57
  config_hash: 2b58015cf2b3462a
  seed: 42
  strict_gate_enabled: false
  fusion_enabled: false
  cleanup_mode: auto
  timestamp: "2026-04-13T04:23:43.101564+00:00Z"
  duration_seconds: 0.951107
determinism_checked: false
determinism_pass: null
feature_activation_evidence:
  semantic_categorization_activated: false
  categorized_frames: 0
  category_assignments: 0
inconclusive_reasons:
  - "no frames categorized"
is_conclusive: false
---

# semantic_category_metrics Report

## Metrics

- **categorization_coverage**: 0.0000
- **category_consistency_violations**: 0
- **consistency_score**: 1.0000
- **frames_with_categories**: 0
- **orphaned_categories**: 0
- **quality_score**: 0.4000
- **total_categories_assigned**: 0
- **total_frames**: 317

## Evidence

### categorization_status
  - assignments: 0
  - categorized: 0
  - orphaned_categories: 0
  - total_frames: 317


## legacy_layer_metrics

---
run_metadata:
  dataset_hash: ac3a7349956ede57
  config_hash: 2b58015cf2b3462a
  seed: 42
  strict_gate_enabled: false
  fusion_enabled: false
  cleanup_mode: auto
  timestamp: "2026-04-13T04:23:43.101564+00:00Z"
  duration_seconds: 0.951107
determinism_checked: false
determinism_pass: null
feature_activation_evidence:
  legacy_data_preserved: true
  legacy_nodes: 287
  dual_labeled_nodes: 0
inconclusive_reasons:
  - orphaned_legacy_nodes=127
is_conclusive: false
---

# legacy_layer_metrics Report

## Metrics

- **legacy_nodes_active**: 287
- **legacy_nodes_total**: 861
- **legacy_orphans**: 127
- **legacy_preservation_rate**: 0.3333
- **legacy_relationship_preservation_rate**: 0.3516
- **legacy_relationships_active**: 1050
- **legacy_relationships_total**: 2986
- **migration_dual_nodes**: 0
- **migration_dual_rels**: 28
- **quality_score**: 0.8525

## Evidence

### legacy_population
  - nodes_active: 287
  - nodes_total: 861
  - relationships_active: 1050
  - relationships_total: 2986
### migration_status
  - dual_labeled_nodes: 0
  - dual_path_relationships: 28
  - orphaned_nodes: 127


