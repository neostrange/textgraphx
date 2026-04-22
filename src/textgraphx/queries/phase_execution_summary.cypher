// Aggregate phase execution metrics from PhaseRun markers.
MATCH (pr:PhaseRun)
WITH pr.phase AS phase,
     count(pr) AS execution_count,
     coalesce(sum(pr.documents_processed), 0) AS documents_processed,
     coalesce(avg(pr.duration_seconds), 0.0) AS duration_seconds
RETURN phase,
       execution_count,
       documents_processed,
       duration_seconds
ORDER BY phase ASC;
