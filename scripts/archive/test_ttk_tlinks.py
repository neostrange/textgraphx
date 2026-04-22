from textgraphx.TlinksRecognizer import TlinksRecognizer
from textgraphx.neo4j_client import make_graph_from_config
import sys

def main():
    graph = make_graph_from_config()
    recognizer = TlinksRecognizer([sys.argv[0], "--debug"])
    doc_ids = recognizer.get_annotated_text()
    if not doc_ids:
        print("No annotated text found.")
        return
    
    doc_id = doc_ids[0]
    print(f"Testing document ID: {doc_id}")
    
    xml = recognizer._get_ttk_xml(doc_id)
    print("XML length:", len(xml) if xml else 0)
    print("Has content:", bool(xml))
    
    if xml:
       links = list(recognizer._iter_tlink_elements(xml))
       print(f"Found {len(links)} TLINK elements in XML.")
       if links:
           for link in links[:3]:
               print(link.attrib)

if __name__ == "__main__":
    main()
