// Most recent phase run markers
MATCH (r:PhaseRun)
RETURN r.phase AS phase,
       r.timestamp AS timestamp,
       r.duration_seconds AS duration_seconds,
       r.documents_processed AS documents_processed
ORDER BY r.timestamp DESC
LIMIT 50;
