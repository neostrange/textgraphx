from textgraphx.TlinksRecognizer import TlinksRecognizer
tr = TlinksRecognizer()
doc_id = "61327"
xml_text = tr._get_ttk_xml(doc_id)
found_tlinks = []
count_e2e = 0
for elem in tr._iter_tlink_elements(xml_text):
    rel_type = elem.attrib.get("relType")
    if "eventInstanceID" in elem.attrib and "relatedToEventInstance" in elem.attrib:
        count_e2e += 1
        found_tlinks.append(("E2E", elem.attrib))
print(f"Total E2E in XML: {count_e2e}")
print(found_tlinks[:2])
