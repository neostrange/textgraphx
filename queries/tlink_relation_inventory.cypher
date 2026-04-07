// Inventory of TLINK relation labels with canonicality diagnostics.
MATCH ()-[r:TLINK]-()
WITH coalesce(r.relType, 'UNSET') AS rel_type,
     coalesce(r.relTypeCanonical, 'UNSET') AS rel_type_canonical,
     count(r) AS rel_count
RETURN rel_type, rel_type_canonical, rel_count
ORDER BY rel_count DESC, rel_type ASC;