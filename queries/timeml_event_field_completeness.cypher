// TimeML EVENT field completeness profile for TEvent nodes.
MATCH (e:TEvent)
WITH count(e) AS total,
     count(CASE WHEN e.eid IS NOT NULL THEN 1 END) AS with_eid,
     count(CASE WHEN e.tense IS NOT NULL THEN 1 END) AS with_tense,
     count(CASE WHEN e.aspect IS NOT NULL THEN 1 END) AS with_aspect,
     count(CASE WHEN e.polarity IS NOT NULL THEN 1 END) AS with_polarity,
     count(CASE WHEN e.pos IS NOT NULL THEN 1 END) AS with_pos,
     count(CASE WHEN e.eid IS NULL OR e.tense IS NULL OR e.aspect IS NULL OR e.polarity IS NULL OR e.pos IS NULL THEN 1 END) AS missing_core
RETURN total,
       with_eid,
       with_tense,
       with_aspect,
       with_polarity,
       with_pos,
       missing_core;