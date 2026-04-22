import re

with open("textgraphx/EventEnrichmentPhase.py", "r") as f:
    text = f.read()

# I need to place it before `return mentions_created`
text = text.replace(
"""            logger.info("create_event_mentions: created %d EventMention nodes for doc_id=%s", mentions_created, doc_id)
            return mentions_created
        except Exception:
            logger.exception("Failed to create event mentions for doc_id=%s", doc_id)
            return 0

        self.normalize_event_boundaries(doc_id)""",
"""            logger.info("create_event_mentions: created %d EventMention nodes for doc_id=%s", mentions_created, doc_id)
            self.normalize_event_boundaries(doc_id)
            return mentions_created
        except Exception:
            logger.exception("Failed to create event mentions for doc_id=%s", doc_id)
            return 0""")


with open("textgraphx/EventEnrichmentPhase.py", "w") as f:
    f.write(text)
