import urllib.request
import json
from textgraphx.TlinksRecognizer import TlinksRecognizer
tr = TlinksRecognizer()
doc_id = 61327 # INT!
payload = tr.get_doc_text_and_dct(doc_id)
print(f"Payload input length: {len(payload.get('input',''))}")
print(f"Payload dct: {payload.get('dct')}")
try:
    import requests
    response = requests.post('http://localhost:5050/annotate', json=payload, timeout=30)
    response.raise_for_status()
    print("Success:", response.status_code)
except Exception as e:
    print(f"Error: {e}")
