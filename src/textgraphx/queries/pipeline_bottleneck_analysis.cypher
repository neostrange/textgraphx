// Identify the slowest phases from PhaseRun markers.
MATCH (pr:PhaseRun)
WITH pr.phase AS phase,
     count(pr) AS execution_count,
     coalesce(avg(pr.duration_seconds), 0.0) AS avg_duration_seconds,
     coalesce(max(pr.duration_seconds), 0.0) AS max_duration_seconds
RETURN phase,
       execution_count,
       avg_duration_seconds,
       max_duration_seconds
ORDER BY avg_duration_seconds DESC, phase ASC;