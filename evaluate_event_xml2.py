import re
import xml.etree.ElementTree as ET

with open("textgraphx/datastore/annotated/96770_World_stocks_plunge_on_fears_on_US_recession.xml", "r") as f:
    eval_xml = f.read()

root = ET.fromstring(eval_xml)

for elem in root.iter('EVENT'):
    print(elem.attrib)
