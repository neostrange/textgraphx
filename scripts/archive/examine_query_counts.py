from neo4j import GraphDatabase
import os
import json
import glob

# Try to connect if textgraphx.neo4j or similar is available. 
# But wait, I can just see how many rows were returned in the evaluator.
# Actually, I can patch meantime_evaluator to print out the counts!
