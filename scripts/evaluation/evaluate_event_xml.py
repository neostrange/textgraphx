import re
from pathlib import Path
from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()

# check what TTK returns for one of our batch files
ROOT = Path(__file__).resolve().parents[2]
batch_file = ROOT / "src" / "textgraphx" / "datastore" / "dataset_eval_batch" / "wsj_1008.xml"

with batch_file.open("r") as f:
    print("Opened")
