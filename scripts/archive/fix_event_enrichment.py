import re

with open("textgraphx/EventEnrichmentPhase.py", "r") as f:
    content = f.read()

# Clean up participant_linking_core queries:
content = re.sub(r'r\.is_core = true,?\s+r\.is_core = false', 'r.is_core = false', content)
content = re.sub(r'nr\.is_core = false,?\s+[\n\s]+.*?nr\.is_core = true', 'nr.is_core = false', content, flags=re.DOTALL)

with open("textgraphx/EventEnrichmentPhase.py", "w") as f:
    f.write(content)
