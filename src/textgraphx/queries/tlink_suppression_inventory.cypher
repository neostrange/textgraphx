// Summary of TLINK suppression outcomes from consistency filtering.
MATCH ()-[r:TLINK]->()
WHERE coalesce(r.suppressed, false) = true
RETURN coalesce(r.suppressedBy, 'UNSET') AS suppressed_by,
       coalesce(r.suppressionPolicy, 'UNSET') AS suppression_policy,
       coalesce(r.suppressionReason, 'UNSET') AS suppression_reason,
       coalesce(r.suppressedAgainstRelType, 'UNSET') AS against_rel_type,
       count(r) AS suppressed_count
ORDER BY suppressed_count DESC, suppressed_by ASC, suppression_reason ASC;