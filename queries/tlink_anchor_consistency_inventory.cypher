// Inventory of TLINK anchor consistency signals and suppression outcomes.
MATCH ()-[r:TLINK]->()
RETURN 'inconsistent_tlinks' AS metric,
       count(CASE WHEN coalesce(r.anchorConsistency, true) = false THEN 1 END) AS item_count
UNION ALL
MATCH ()-[r:TLINK]->()
RETURN 'self_link_tlinks' AS metric,
       count(CASE WHEN coalesce(r.anchorConsistencyReason, '') = 'self_link' THEN 1 END) AS item_count
UNION ALL
MATCH ()-[r:TLINK]->()
RETURN 'endpoint_violation_tlinks' AS metric,
       count(CASE WHEN coalesce(r.anchorConsistencyReason, '') = 'endpoint_contract_violation' THEN 1 END) AS item_count
UNION ALL
MATCH ()-[r:TLINK]->()
RETURN 'anchor_filter_suppressed_tlinks' AS metric,
       count(CASE WHEN coalesce(r.suppressed, false) = true
                   AND coalesce(r.suppressedBy, '') = 'tlink_anchor_consistency_filter'
                  THEN 1 END) AS item_count
UNION ALL
MATCH ()-[r:TLINK]->()
RETURN 'missing_anchor_metadata_tlinks' AS metric,
       count(CASE WHEN r.sourceAnchorType IS NULL OR r.targetAnchorType IS NULL THEN 1 END) AS item_count;
