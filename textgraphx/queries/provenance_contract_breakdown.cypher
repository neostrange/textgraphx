// Breakdown of missing provenance-contract fields by relationship type and source/rule buckets.
MATCH ()-[r]->()
WHERE type(r) IN ['TLINK', 'DESCRIBES', 'FRAME_DESCRIBES_EVENT', 'PARTICIPANT', 'EVENT_PARTICIPANT']
WITH type(r) AS rel_type,
     coalesce(r.evidence_source, 'UNSET') AS evidence_source,
     coalesce(r.rule_id, 'UNSET') AS rule_id,
     coalesce(r.authority_tier, 'UNSET') AS authority_tier,
     CASE WHEN r.confidence IS NULL THEN 1 ELSE 0 END AS missing_confidence,
     CASE WHEN r.evidence_source IS NULL THEN 1 ELSE 0 END AS missing_evidence_source,
     CASE WHEN r.rule_id IS NULL THEN 1 ELSE 0 END AS missing_rule_id,
     CASE WHEN r.authority_tier IS NULL THEN 1 ELSE 0 END AS missing_authority_tier,
     CASE WHEN r.source_kind IS NULL THEN 1 ELSE 0 END AS missing_source_kind,
     CASE WHEN r.conflict_policy IS NULL THEN 1 ELSE 0 END AS missing_conflict_policy
RETURN rel_type,
       evidence_source,
       rule_id,
       authority_tier,
       sum(missing_confidence) AS missing_confidence,
       sum(missing_evidence_source) AS missing_evidence_source,
       sum(missing_rule_id) AS missing_rule_id,
       sum(missing_authority_tier) AS missing_authority_tier,
       sum(missing_source_kind) AS missing_source_kind,
       sum(missing_conflict_policy) AS missing_conflict_policy,
       sum(
           missing_confidence + missing_evidence_source + missing_rule_id +
           missing_authority_tier + missing_source_kind + missing_conflict_policy
       ) AS total_missing_fields
ORDER BY total_missing_fields DESC, rel_type ASC, evidence_source ASC, rule_id ASC;