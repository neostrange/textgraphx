// Count endpoint contract violations by relationship type.
MATCH ()-[r]->()
WHERE r.endpoint_contract_violation = true
RETURN type(r) AS rel_type,
       count(r) AS violation_count
ORDER BY violation_count DESC, rel_type ASC;
