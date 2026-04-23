// Relationship distribution by edge type.
MATCH ()-[r]->()
RETURN type(r) AS rel_type,
       count(r) AS rel_count
ORDER BY rel_count DESC, rel_type ASC;