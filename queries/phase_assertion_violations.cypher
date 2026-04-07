// Summarize failed assertion payloads captured by phase wrappers.
MATCH (pr:PhaseRun)
WHERE pr.assertions_passed = false
UNWIND coalesce(pr.assertion_failures, []) AS failure
WITH pr.phase AS phase,
     coalesce(failure.label, 'unknown_assertion') AS assertion
RETURN phase,
       assertion,
       count(*) AS violation_count
ORDER BY violation_count DESC, phase ASC, assertion ASC;
