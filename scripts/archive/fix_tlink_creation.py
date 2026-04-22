from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.TlinksRecognizer import TlinksRecognizer
from textgraphx.config import get_config

def main():
    graph = make_graph_from_config()
    rec = TlinksRecognizer(["fix_tlink_creation.py"])
    doc_ids = rec.get_annotated_text()
    
    # Run creation links on all of them
    for did in doc_ids:
        rec.create_tlinks_e2e(did, precision_mode=True)
        rec.create_tlinks_e2t(did, precision_mode=True)
        rec.create_tlinks_t2t(did, precision_mode=True)
    
    res = graph.run("MATCH ()-[r:TLINK {source: 'ttk_xml'}]->() RETURN COUNT(r) AS c").data()
    print(f"Total ttk_xml links now in DB: {res[0]['c']}")
    
if __name__ == "__main__":
    main()
