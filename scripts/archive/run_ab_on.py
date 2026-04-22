from textgraphx.config import get_config
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.phase_wrappers import TlinksRecognizerWrapper

cfg = get_config()
cfg.runtime.enable_tlink_xml_seed = True

g = make_graph_from_config()
w = TlinksRecognizerWrapper(g)
w.execute()
