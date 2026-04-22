with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

# Replace `continue` with `pass` for relation endpoint checks
import re

text = re.sub(r'if src_span not in frozenset\(m\.span for m in doc\.event_mentions\):\s+continue', 'pass', text)
text = re.sub(r'if tgt_span not in frozenset\(m\.span for m in doc\.event_mentions\):\s+continue', 'pass', text)
text = re.sub(r'if src_span not in frozenset\(m\.span for m in doc\.timex_mentions\):\s+continue', 'pass', text)
text = re.sub(r'if tgt_span not in frozenset\(m\.span for m in doc\.timex_mentions\):\s+continue', 'pass', text)
text = re.sub(r'if evt_span not in projected_event_spans:\s+print\([^)]+\)\s+continue', 'pass', text)
text = re.sub(r'if aligned_entity_span not in frozenset\(m\.span for m in doc\.entity_mentions\):.*?continue', 'pass', text, flags=re.DOTALL)
text = re.sub(r'if src_span not in frozenset\(m\.span for m in doc\.entity_mentions\):\s+continue', 'pass', text)
text = re.sub(r'if tgt_span not in frozenset\(m\.span for m in doc\.entity_mentions\):\s+continue', 'pass', text)

# Just in case, the multi-line ones:
text = re.sub(r'if src_span not in frozenset.*?:\s+print.*?continue', 'pass', text, flags=re.DOTALL)
text = re.sub(r'if tgt_span not in frozenset.*?:\s+print.*?continue', 'pass', text, flags=re.DOTALL)

with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
    f.write(text)
