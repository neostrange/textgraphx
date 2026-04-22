import urllib.request
import json
from textgraphx.TlinksRecognizer import TlinksRecognizer
tr = TlinksRecognizer()
doc_id = "61327"
payload = tr.get_doc_text_and_dct(doc_id)
print(f"Payload input length: {len(payload.get('input',''))}")
print(f"Payload dct: {payload.get('dct')}")
try:
    req = urllib.request.Request('http://localhost:5050/annotate', data=json.dumps(payload).encode('utf8'), headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'): print(e.read().decode())
