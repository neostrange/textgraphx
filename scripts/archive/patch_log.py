with open("textgraphx/EventEnrichmentPhase.py", "r") as f:
    text = f.read()

old = """        if total > 0:
            logger.warning("endpoint_contract_violations: %s", violations)"""
new = """        if total > 0:
            logger.warning("endpoint_contract_violations: %s", violations)
            import pprint
            rows = self.graph.run("MATCH (s)-[r:REFERS_TO]->(t) WHERE NOT ((any(lbl IN labels(s) WHERE lbl = 'EntityMention') AND any(lbl IN labels(t) WHERE lbl = 'Entity')) OR (any(lbl IN labels(s) WHERE lbl = 'EventMention') AND any(lbl IN labels(t) WHERE lbl = 'TEvent')) OR (any(lbl IN labels(s) WHERE lbl = 'TimexMention') AND any(lbl IN labels(t) WHERE lbl = 'TIMEX')) OR (any(lbl IN labels(s) WHERE lbl = 'NamedEntity') AND any(lbl IN labels(t) WHERE lbl = 'Entity')) OR (any(lbl IN labels(s) WHERE lbl = 'NamedEntity') AND any(lbl IN labels(t) WHERE lbl = 'VALUE')) OR (any(lbl IN labels(s) WHERE lbl = 'FrameArgument') AND any(lbl IN labels(t) WHERE lbl = 'Entity')) OR (any(lbl IN labels(s) WHERE lbl = 'FrameArgument') AND any(lbl IN labels(t) WHERE lbl = 'NamedEntity')) OR (any(lbl IN labels(s) WHERE lbl = 'FrameArgument') AND any(lbl IN labels(t) WHERE lbl = 'NUMERIC'))) RETURN labels(s) AS s, labels(t) AS t").data()
            logger.warning("Illegal edges: %s", pprint.pformat(rows))"""

text = text.replace(old, new)
with open("textgraphx/EventEnrichmentPhase.py", "w") as f:
    f.write(text)
print("done")
