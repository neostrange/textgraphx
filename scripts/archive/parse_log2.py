import logging
logging.basicConfig(level=logging.DEBUG)
from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase
p = EventEnrichmentPhase([])
res = p.create_event_mentions(76437)
print("CREATED MENTIONS:", res)
