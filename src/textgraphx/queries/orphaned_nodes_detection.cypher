// Nodes with no incident relationships, grouped by primary label.
MATCH (n)
WHERE NOT (n)--()
RETURN coalesce(head(labels(n)), "<unlabeled>") AS label,
       count(*) AS orphan_count
ORDER BY orphan_count DESC, label ASC;