// TimeML TIMEX field completeness profile for TIMEX nodes.
MATCH (x:TIMEX)
WITH count(x) AS total,
     count(CASE WHEN x.tid IS NOT NULL THEN 1 END) AS with_tid,
     count(CASE WHEN x.type IS NOT NULL THEN 1 END) AS with_type,
     count(CASE WHEN x.value IS NOT NULL THEN 1 END) AS with_value,
     count(CASE WHEN x.tid IS NULL OR x.type IS NULL OR x.value IS NULL THEN 1 END) AS missing_core
RETURN total,
       with_tid,
       with_type,
       with_value,
       missing_core;