import pytest
from textgraphx.reasoning_contracts import count_endpoint_violations
from textgraphx.neo4j_client import get_client

def debug_refers_to():
    graph = get_client().get_graph()
    q = """
    MATCH (s)-[r:REFERS_TO]->(t)
    WHERE NOT (
      (any(lbl IN labels(s) WHERE lbl = 'EntityMention') AND any(lbl IN labels(t) WHERE lbl = 'Entity')) OR
      (any(lbl IN labels(s) WHERE lbl = 'EventMention') AND any(lbl IN labels(t) WHERE lbl = 'TEvent')) OR
      (any(lbl IN labels(s) WHERE lbl = 'TimexMention') AND any(lbl IN labels(t) WHERE lbl = 'TIMEX')) OR
      (any(lbl IN labels(s) WHERE lbl = 'NamedEntity') AND any(lbl IN labels(t) WHERE lbl = 'Entity')) OR
      (any(lbl IN labels(s) WHERE lbl = 'NamedEntity') AND any(lbl IN labels(t) WHERE lbl = 'VALUE')) OR
      (any(lbl IN labels(s) WHERE lbl = 'FrameArgument') AND any(lbl IN labels(t) WHERE lbl = 'Entity')) OR
      (any(lbl IN labels(s) WHERE lbl = 'FrameArgument') AND any(lbl IN labels(t) WHERE lbl = 'NamedEntity')) OR
      (any(lbl IN labels(s) WHERE lbl = 'FrameArgument') AND any(lbl IN labels(t) WHERE lbl = 'NUMERIC'))
    )
    RETURN labels(s) AS s_labels, labels(t) AS t_labels, count(*) as count
    """
    rows = graph.run(q).data()
    print("ILLEGAL REFERS_TO EDGES:")
    for row in rows:
        print(row)

debug_refers_to()
