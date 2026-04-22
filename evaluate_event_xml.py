import re
from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()

# check what TTK returns for one of our batch files
with open("textgraphx/datastore/dataset_eval_batch/wsj_1008.xml", "r") as f:
    print("Opened")
