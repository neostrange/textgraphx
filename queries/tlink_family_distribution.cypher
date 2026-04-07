// TLINK yield by rule family/provenance with suppression visibility.
MATCH ()-[r:TLINK]->()
RETURN coalesce(r.evidence_source, 'UNSET') AS evidence_source,
       coalesce(r.rule_id, 'UNSET') AS rule_id,
       coalesce(r.authority_tier, 'UNSET') AS authority_tier,
       coalesce(r.relTypeCanonical, r.relType, 'UNSET') AS rel_type,
       coalesce(r.suppressed, false) AS suppressed,
       count(r) AS rel_count
ORDER BY rel_count DESC, evidence_source ASC, rule_id ASC, rel_type ASC;