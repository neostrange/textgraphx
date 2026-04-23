// Documents with isolated temporal anchors or no unsuppressed TLINK connectivity.
MATCH (anchor)
WHERE anchor:TEvent OR anchor:TIMEX OR anchor:Timex3 OR anchor:EventMention OR anchor:TimexMention
WITH coalesce(anchor.doc_id, anchor.document_id) AS document_id,
     collect(DISTINCT anchor) AS anchors
WHERE document_id IS NOT NULL AND size(anchors) > 1
WITH document_id, anchors, size(anchors) AS total_anchors
UNWIND anchors AS anchor
OPTIONAL MATCH (anchor)-[r:TLINK]-()
WITH document_id,
     total_anchors,
     anchor,
     count(CASE WHEN coalesce(r.suppressed, false) = false THEN 1 END) AS active_tlink_count
WITH document_id,
     total_anchors,
     sum(CASE WHEN active_tlink_count = 0 THEN 1 ELSE 0 END) AS isolated_anchor_count,
     sum(CASE WHEN active_tlink_count > 0 THEN 1 ELSE 0 END) AS connected_anchor_count
WHERE isolated_anchor_count > 0 OR connected_anchor_count = 0
RETURN document_id,
       total_anchors,
       connected_anchor_count,
       isolated_anchor_count
ORDER BY isolated_anchor_count DESC, total_anchors DESC, document_id ASC;