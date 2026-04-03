"""EventEnrichmentPhase

Attach frames to temporalized events and populate participant relationships
between canonical `Entity`/`NUMERIC` nodes and `TEvent` nodes. This phase
assumes frames and TIMEX/TEvent nodes are already present in the graph and
performs idempotent MERGE updates to create `DESCRIBES` and `PARTICIPANT`
edges.
"""

import os
import spacy
import sys

# When run as a script, allow imports by ensuring repo root is available.
if __name__ == '__main__' and __package__ is None:
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
#import neuralcoref

from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel
from textgraphx.util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from textgraphx.util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
from textgraphx.TextProcessor import TextProcessor
import xml.etree.ElementTree as ET
# legacy py2neo imports removed; use bolt-driver wrapper via neo4j_client
import logging

from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.config import get_config

logger = logging.getLogger(__name__)



# This phase will run after the TemporalPhase.
# NOTES: 
## 
class EventEnrichmentPhase():

    uri=""
    username =""
    password =""
    graph=""

    def __init__(self, argv):
        # Initialize a shared py2neo Graph from config
        self.graph = make_graph_from_config()
        # keep legacy attrs for compatibility
        self.uri = None
        self.username = None
        self.password = None
        #self.__text_processor = TextProcessor(self.nlp, self._driver)
        #self.create_constraints()
    logger.info("EventEnrichmentPhase initialized; graph session ready")

         


    # Link Frame to TEvent via DESCRIBES relationship.
    # Two complementary paths are used to maximise coverage (Item 6 refactor):
    #   Path 1 – direct:   TagOccurrence PARTICIPATES_IN Frame  AND  TRIGGERS TEvent
    #   Path 2 – via args: TagOccurrence PARTICIPATES_IN FrameArgument PARTICIPANT Frame
    #                      AND same TagOccurrence TRIGGERS TEvent
    # Both paths are idempotent (MERGE) so running them together is safe.
    def link_frameArgument_to_event(self):
        logger.debug("link_frameArgument_to_event")
        graph = self.graph
        linked = 0

        # Path 1: token directly participates in Frame and triggers TEvent
        query_direct = """
            MATCH (f:Frame)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
            MERGE (f)-[:DESCRIBES]->(event)
            RETURN count(*) AS linked
        """
        rows = graph.run(query_direct).data()
        if rows:
            linked += rows[0].get("linked", 0)

        # Path 2: token participates in FrameArgument whose Frame triggers TEvent
        query_via_arg = """
            MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
            MATCH (fa)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
            MERGE (f)-[:DESCRIBES]->(event)
            RETURN count(*) AS linked
        """
        rows = graph.run(query_via_arg).data()
        if rows:
            linked += rows[0].get("linked", 0)

        logger.info("link_frameArgument_to_event: %d DESCRIBES relationships merged", linked)
        return linked




    #// PURPOSE: To add/link core-participants to an Event object. Core-Participants include ['ARG0','ARG1','ARG2','ARG3','ARG4']
    #// PRECONDITION: Event is already linked with the corresponding Frame
    #//               FrameArgument is referring to an Entity or a NUMERIC
    #// POSTCONDITION: some attributes need to be added as a relationship properties such as participant 
    #// role (e.g., ARG0, 1), preposition (in case of prepostional frame argument) 
    #// DESCRIPTION: It will not include contextual or adjunts particpants such as MNR, TMP, CAU etc.
    #// version 1.1 : added support for NUMERIC participants.                  

    def add_core_participants_to_event(self):
        logger.debug("add_core_participants_to_event")
        graph = self.graph

        query = """    
                    match p= (event:TEvent)<-[:DESCRIBES]-(f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument where fa.type in 
                    ['ARG0','ARG1','ARG2','ARG3','ARG4'])-[:REFERS_TO]->(e)
                    where e:Entity OR e:NUMERIC
                    merge (e)-[r:PARTICIPANT]->(event)
                    set r.type = fa.type, (case when fa.syntacticType in ['IN'] then r END).prep = fa.head 
                    return p     
        
        """
        data= graph.run(query).data()
        
        return ""
    


# custom labels for non-core arguments and storing it as a node attribute: argumentType. The second step the value in the fa.argumentType 
# will be set as a lable for this node. It will perform event enrichment fucntion as well as attaching propbank modifiers arguments 
# with the event node. 
# TODO: Though we have found fa nodes with duplicates content with same label or arg type but we will deal with it later.                 

    def add_non_core_participants_to_event(self):
        logger.debug("add_non_core_participants_to_event")
        graph = self.graph

        query = """    
                    MATCH (event:TEvent)<-[:DESCRIBES]-(f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
                    WHERE NOT fa.type IN ['ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'ARGM-TMP']
                    WITH event, f, fa
                    SET fa.argumentType =
                        CASE fa.type
                        WHEN 'ARGM-COM' THEN 'Comitative'
                        WHEN 'ARGM-LOC' THEN 'Locative'
                        WHEN 'ARGM-DIR' THEN 'Directional'
                        WHEN 'ARGM-GOL' THEN 'Goal'
                        WHEN 'ARGM-MNR' THEN 'Manner'
                        WHEN 'ARGM-TMP' THEN 'Temporal'
                        WHEN 'ARGM-EXT' THEN 'Extent'
                        WHEN 'ARGM-REC' THEN 'Reciprocals'
                        WHEN 'ARGM-PRD' THEN 'SecondaryPredication'
                        WHEN 'ARGM-PRP' THEN 'PurposeClauses'
                        WHEN 'ARGM-CAU' THEN 'CauseClauses'
                        WHEN 'ARGM-DIS' THEN 'Discourse'
                        WHEN 'ARGM-MOD' THEN 'Modals'
                        WHEN 'ARGM-NEG' THEN 'Negation'
                        WHEN 'ARGM-DSP' THEN 'DirectSpeech'
                        WHEN 'ARGM-ADV' THEN 'Adverbials'
                        WHEN 'ARGM-ADJ' THEN 'Adjectival'
                        WHEN 'ARGM-LVB' THEN 'LightVerb'
                        WHEN 'ARGM-CXN' THEN 'Construction'
                        ELSE 'NonCore'
                        END
                    MERGE (fa)-[r:PARTICIPANT]->(event)
                    SET r.type = fa.type,
                        (CASE WHEN fa.syntacticType IN ['IN'] THEN r END).prep = fa.head 
                    RETURN event, f, fa, r     
        
        """
        data= graph.run(query).data()
        
        return ""
    



 # 2nd step where we set the labels for the non-core fa arguments are assigned

    def add_label_to_non_core_fa(self):
        logger.debug("add_label_to_non_core_fa")
        graph = self.graph

        query = """    
                   
                    MATCH (fa:FrameArgument)
                    WHERE fa.argumentType is not NULL
                    CALL apoc.create.addLabels(id(fa), [fa.argumentType]) YIELD node
                    RETURN node     
        
        """
        data= graph.run(query).data()
        
        return ""



if __name__ == '__main__':
    import time as _time
    tp = EventEnrichmentPhase(sys.argv[1:])

    _phase_start = _time.time()
    tp.link_frameArgument_to_event()
    tp.add_core_participants_to_event()
    tp.add_non_core_participants_to_event()
    tp.add_label_to_non_core_fa()
    _phase_duration = _time.time() - _phase_start

    # Record a PhaseRun marker in the graph for restart visibility (Item 7)
    try:
        from textgraphx.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="event_enrichment",
            duration_seconds=_phase_duration,
            metadata={"passes": "link,core_participants,non_core_participants,label_non_core"},
        )
    except Exception:
        logger.exception("Failed to write EventEnrichmentRun marker (non-fatal)")










