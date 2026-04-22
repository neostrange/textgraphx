// TLINK completeness profile for canonicalized relation fields.
MATCH ()-[r:TLINK]->()
WITH count(r) AS total,
     count(CASE WHEN r.relType IS NOT NULL THEN 1 END) AS with_rel_type,
     count(CASE WHEN r.relTypeCanonical IS NOT NULL THEN 1 END) AS with_rel_type_canonical,
     count(CASE WHEN r.relTypeOriginal IS NOT NULL THEN 1 END) AS with_rel_type_original,
     count(CASE WHEN r.relTypeCanonical IS NULL THEN 1 END) AS missing_canonical
RETURN total,
       with_rel_type,
       with_rel_type_canonical,
       with_rel_type_original,
       missing_canonical;