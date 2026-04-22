import re

with open('textgraphx/EventEnrichmentPhase.py', 'r') as f:
    content = f.read()

content = content.replace(
    "logger.info(\"create_event_mentions: created %d EventMention nodes for doc_id=%s\", mentions_created, doc_id)\n            self.normalize_event_boundaries(doc_id)",
    "logger.info(\"create_event_mentions: created %d EventMention nodes for doc_id=%s\", mentions_created, doc_id)\n            self.normalize_event_boundaries(doc_id)\n            self.tag_timeml_core_events(doc_id)"
)

with open('textgraphx/EventEnrichmentPhase.py', 'w') as f:
    f.write(content)
