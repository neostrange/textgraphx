// Count inferred relationships missing provenance contract fields.
// Intended for governance dashboards and runbook triage.
MATCH ()-[r]->()
WHERE type(r) IN ['TLINK', 'DESCRIBES', 'FRAME_DESCRIBES_EVENT', 'PARTICIPANT', 'EVENT_PARTICIPANT']
WITH type(r) AS rel_type, r
WHERE r.confidence IS NULL
   OR r.evidence_source IS NULL
   OR r.rule_id IS NULL
   OR r.authority_tier IS NULL
   OR r.source_kind IS NULL
   OR r.conflict_policy IS NULL
RETURN rel_type, count(r) AS missing_contract_count
ORDER BY missing_contract_count DESC, rel_type ASC;