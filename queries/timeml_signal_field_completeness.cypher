// SIGNAL field completeness profile for Signal nodes.
MATCH (s:Signal)
WITH count(s) AS total,
     count(CASE WHEN s.text IS NOT NULL THEN 1 END) AS with_text,
     count(CASE WHEN s.start_tok IS NOT NULL THEN 1 END) AS with_start_tok,
     count(CASE WHEN s.end_tok IS NOT NULL THEN 1 END) AS with_end_tok,
     count(CASE WHEN s.text IS NULL OR s.start_tok IS NULL OR s.end_tok IS NULL THEN 1 END) AS missing_core
RETURN total,
       with_text,
       with_start_tok,
       with_end_tok,
       missing_core;