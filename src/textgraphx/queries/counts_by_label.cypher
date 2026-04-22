// Node counts by common pipeline labels
MATCH (n)
WITH labels(n) AS ls
UNWIND ls AS label
WITH label, count(*) AS c
RETURN label, c
ORDER BY c DESC, label ASC;
