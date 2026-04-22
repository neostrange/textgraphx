import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
annotated_file = ROOT / "src" / "textgraphx" / "datastore" / "annotated" / "96770_World_stocks_plunge_on_fears_on_US_recession.xml"

with annotated_file.open("r") as f:
    eval_xml = f.read()

root = ET.fromstring(eval_xml)

for elem in root.iter('EVENT'):
    print(elem.attrib)
