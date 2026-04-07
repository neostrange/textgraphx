// Inventory transitional NUMERIC/VALUE label usage against canonical VALUE nodes.
MATCH (ne:NamedEntity)
WHERE ne:NUMERIC
RETURN 'namedentity_numeric_labels' AS metric,
       count(ne) AS item_count
UNION ALL
MATCH (ne:NamedEntity)
WHERE ne:VALUE
RETURN 'namedentity_value_labels' AS metric,
       count(ne) AS item_count
UNION ALL
MATCH (v:VALUE)
RETURN 'canonical_value_nodes' AS metric,
       count(v) AS item_count
UNION ALL
MATCH (ne:NamedEntity)
WHERE coalesce(ne.value_tagged, false) = true
RETURN 'namedentity_value_tagged_history' AS metric,
       count(ne) AS item_count
ORDER BY metric ASC;
