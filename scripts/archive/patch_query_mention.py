with open("textgraphx/EventEnrichmentPhase.py", "r") as f:
    text = f.read()

text = text.replace(
    "r.created_at = coalesce(r.created_at, datetime().epochMillis)",
    "r.created_at = coalesce(r.created_at, datetime().epochMillis),\n                        r.is_core = true"
)

text = text.replace(
    "nr.created_at = coalesce(nr.created_at, datetime().epochMillis)",
    "nr.created_at = coalesce(nr.created_at, datetime().epochMillis),\n                        nr.is_core = true"
)

with open("textgraphx/EventEnrichmentPhase.py", "w") as f:
    f.write(text)
