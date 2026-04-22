from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.TemporalPhase import TemporalPhase
import xml.etree.ElementTree as ET

g = make_graph_from_config()
res = g.run("MATCH (a:AnnotatedText) RETURN a.id LIMIT 4").data()

import nltk
nltk.download('wordnet')

for r in res:
    doc_id = r['a.id']

    t = TemporalPhase(None)
    xml = t._get_ttk_xml(doc_id)

    root = ET.fromstring(xml)
    allowed_nouns = []
    denied_nouns = []
    verb_events = []

    for event in root.iter():
        if event.tag.endswith("EVENT"):
            form_lc = (event.attrib.get('form') or '').lower()
            raw_pos = (event.attrib.get('pos') or '').upper()
            
            if raw_pos in {"NN", "NNS"}:
                if t._is_eventive_nominal(form_lc):
                    allowed_nouns.append(form_lc)
                else:
                    denied_nouns.append(form_lc)
            elif raw_pos.startswith("VB"):
                verb_events.append(form_lc)

    print(f"--- Doc {doc_id} ---")
    print("Allowed Nouns:")
    print(", ".join(allowed_nouns))
    print("Denied Nouns:")
    print(", ".join(denied_nouns))

