"""RefinementPhase

This module implements the refinement stage of the text→graph pipeline.
It contains a collection of business-rule Cypher updates that enrich and
canonicalize nodes created by earlier phases (tokenization, SRL, NER,
coreference). The operations are intentionally small, idempotent Cypher
passes that can be executed individually during debugging or orchestrated in
sequence as part of a batch refinement step.

Typical usage (from code):
    rp = RefinementPhase()
    rp.get_and_assign_head_info_to_entity_multitoken()

You can also run the module as a script to execute a common sequence of
refinement passes; when executed as `python RefinementPhase.py` the module
adds the repository root to sys.path so the package imports resolve.
"""

import os
import spacy
import sys
# allow running the module as a script (so `python RefinementPhase.py` works)
# When the module is executed directly the package name is not set and
# imports like `from textgraphx.TextProcessor import ...` will fail. Add
# the repository root to sys.path so package-style imports resolve when
# running the file as a script.
if __package__ is None and __name__ == '__main__':
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

#import neuralcoref
#import coreferee
from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel
from textgraphx.util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from textgraphx.util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
from textgraphx.TextProcessor import TextProcessor
import xml.etree.ElementTree as ET
# py2neo removed: use bolt-driver wrapper via neo4j_client
import logging

from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.config import get_config

logger = logging.getLogger(__name__)




class RefinementPhase():
    """Graph refinement stage for the text→graph pipeline.

    This class contains a series of targeted refinement operations that are
    executed as individual Cypher updates. Each method implements one
    refinement rule used in the project's business pipeline (for example:
    assigning syntactic heads to `NamedEntity`/`FrameArgument` nodes, linking
    frame arguments to entity instances, and applying heuristic canonical-
    ization steps).

    Business context and contract:
    - Input: a Neo4j graph populated by upstream pipeline steps (tokenization,
        SRL frame extraction, NER/NEL and coreference resolution). Common node
        types used here are `AnnotatedText`, `Sentence`, `TagOccurrence`,
        `Frame`, `FrameArgument`, `NamedEntity`, `Entity`, `CorefMention`, and
        `Antecedent`.
    - Output / side effects: nodes may get new properties (e.g., `head`,
        `headTokenIndex`, `syntacticType`, `complement`) and new relationships
        (e.g., `REFERS_TO`, `PARTICIPANT`, `MENTIONS`) will be created. Methods
        generally return nothing (empty string) and perform in-place updates.
    - Preconditions: many operations assume previous pipeline phases ran and
        populated properties such as `tok_index_doc`, `f.type` and
        `ne.headTokenIndex`. Methods are intentionally idempotent: if the
        preconditions are not satisfied they will be no-ops (zero-row updates).

    Implementation notes:
    - The class delegates Cypher execution to the bolt-driver compatibility
        wrapper available via `neo4j_client.make_graph_from_config()` so code can
        be executed against a running Neo4j instance configured in
        `textgraphx/config.ini` or via environment variables.
    - Methods are named after the refinement rule they implement. Keep in
        mind these are business rules that encode heuristics; they may need to
        be tuned to your data.
    """

    uri = ""
    username = ""
    password = ""
    graph = ""

    # Iteration 3: refinement rules are grouped into families to make the
    # pipeline easier to reason about and selectively execute.
    RULE_FAMILIES = {
        "head_assignment": [
            "get_and_assign_head_info_to_entity_multitoken",
            "get_and_assign_head_info_to_entity_singletoken",
            "get_and_assign_head_info_to_antecedent_multitoken",
            "get_and_assign_head_info_to_antecedent_singletoken",
            "get_and_assign_head_info_to_corefmention_multitoken",
            "get_and_assign_head_info_to_corefmention_singletoken",
            "get_and_assign_head_info_to_all_frameArgument_singletoken",
            "get_and_assign_head_info_to_all_frameArgument_multitoken",
            "get_and_assign_head_info_to_frameArgument_singletoken",
            "get_and_assign_head_info_to_frameArgument_multitoken",
            "get_and_assign_head_info_to_frameArgument_with_preposition",
            "get_and_assign_head_info_to_temporal_frameArgument_singletoken",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_pcomp",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj",
            "get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp",
        ],
        "linking": [
            "link_antecedent_to_namedEntity",
            "link_frameArgument_to_namedEntity_for_nam_nom",
            "link_frameArgument_to_namedEntity_for_pobj",
            "link_frameArgument_to_namedEntity_for_pobj_entity",
            "link_frameArgument_to_namedEntity_for_pro",
            "link_frameArgument_to_new_entity",
            "link_frameArgument_to_numeric_entities",
            "link_frameArgument_to_entity_via_named_entity",
        ],
        "nel_correction": [
            "detect_correct_NEL_result_for_missing_kb_id",
        ],
        "numeric_value": [
            "tag_value_entities",
            "tag_numeric_entities",
            "detect_quantified_entities_from_frameArgument",
        ],
    }

    def get_rule_families(self):
        """Return the configured refinement rule families.

        Keys are family names and values are ordered method-name lists.
        """
        return self.RULE_FAMILIES

    def iter_rule_names(self):
        """Yield refinement rule method names in execution order."""
        for family, methods in self.RULE_FAMILIES.items():
            for method_name in methods:
                yield family, method_name

    def run_rule_family(self, family_name):
        """Execute one refinement rule family by name."""
        if family_name not in self.RULE_FAMILIES:
            raise ValueError(f"Unknown refinement rule family: {family_name}")
        for method_name in self.RULE_FAMILIES[family_name]:
            logger.info("Running refinement rule [%s]: %s", family_name, method_name)
            getattr(self, method_name)()

    def run_all_rule_families(self):
        """Execute all configured refinement rule families in order."""
        for family_name in self.RULE_FAMILIES:
            self.run_rule_family(family_name)

    def __init__(self, argv=None):
        # Create a bolt-driver backed compatibility graph object.
        # create graph and wrap it with a thin logger that records query text
        # and number of returned rows. This helps debugging when running the
        # refinement steps interactively or as a script.
        _raw_graph = make_graph_from_config()

        class LoggingGraphCompat:
            """Small wrapper around the compat graph to log each run() call.

            It delegates to the provided graph.run(...) but eagerly calls
            `.data()` so we can log the number of returned rows. The returned
            object implements the same `.data()` contract and returns the
            previously collected list so callers behave the same.
            """

            def __init__(self, graph, logger):
                self._graph = graph
                self._logger = logger

            def run(self, query, parameters=None):
                # Truncate long queries in logs for readability
                qshort = (query.strip().replace("\n", " ")[:200] + "...") if len(query) > 200 else query.strip()
                try:
                    inner = self._graph.run(query, parameters)
                    data = inner.data()
                    self._logger.info("Executed query: %s; rows=%d", qshort, len(data))
                except Exception:
                    self._logger.exception("Query failed: %s", qshort)
                    # Re-raise so callers that expect exceptions continue to get them
                    raise

                class _Result:
                    def __init__(self, data):
                        self._data = data

                    def data(self):
                        return self._data

                return _Result(data)

        # instantiate the wrapped graph and keep legacy attributes
        self.graph = LoggingGraphCompat(_raw_graph, logger)
        self.uri = None
        self.username = None
        self.password = None
    logger.info("RefinementPhase initialized; using graph wrapper for query logging")

    def diagnostic_report(self):
        """Run small diagnostics that count important node/relationship types

        This helps determine whether the refinement queries return zero rows
        because the required data isn't present or because of other logic
        issues.
        """
        checks = {
            'TagOccurrence': "MATCH (n:TagOccurrence) RETURN count(n) AS cnt",
            'NamedEntity': "MATCH (n:NamedEntity) RETURN count(n) AS cnt",
            'FrameArgument': "MATCH (n:FrameArgument) RETURN count(n) AS cnt",
            'Frame': "MATCH (n:Frame) RETURN count(n) AS cnt",
            'Antecedent': "MATCH (n:Antecedent) RETURN count(n) AS cnt",
            'CorefMention': "MATCH (n:CorefMention) RETURN count(n) AS cnt",
            'IS_DEPENDENT rels': "MATCH ()-[r:IS_DEPENDENT]-() RETURN count(r) AS cnt",
            'PARTICIPATES_IN rels': "MATCH ()-[r:PARTICIPATES_IN]-() RETURN count(r) AS cnt",
            'FrameArgument with headTokenIndex': "MATCH (f:FrameArgument) WHERE exists(f.headTokenIndex) RETURN count(f) AS cnt",
        }

        report = {}
        for name, q in checks.items():
            try:
                rows = self.graph.run(q).data()
                # rows is a list of mappings with key 'cnt'
                cnt = rows[0].get('cnt') if rows and isinstance(rows[0], dict) else None
                report[name] = cnt
            except Exception as e:
                report[name] = f"ERROR: {e}"

        # print a concise report
        logger.info("RefinementPhase diagnostic report:")
        for k, v in report.items():
            logger.info("  %s: %s", k, v)
        return report

    def tuning_notes(self) -> dict:
        """Return human-friendly tuning notes for the refinement phase.

        This helper is intentionally in-code so maintainers and operators can
        quickly see which rules are brittle, what upstream annotations they
        depend on, and a minimal set of diagnostics to run when a rule
        appears to match zero rows.

        The method returns a small mapping where keys are short rule names and
        values contain a brief rationale and suggested Cypher checks.
        """
        notes = {
            'head_finding': {
                'rationale': (
                    'Many head-finding passes assume dependency edges of type ' 
                    "'IS_DEPENDENT' and specific POS tags (NN, NNP, PRP etc.)."
                ),
                'upstream': ['TagOccurrence.pos', 'IS_DEPENDENT:type', 'tok_index_doc'],
                'diagnostics': [
                    "MATCH (n:TagOccurrence) RETURN count(n) AS cnt",
                    "MATCH ()-[r:IS_DEPENDENT]-() RETURN count(r) AS cnt",
                    "MATCH (f:FrameArgument) WHERE NOT exists(f.headTokenIndex) RETURN count(f) AS cnt",
                ],
            },
            'prepositional_complements': {
                'rationale': (
                    'Rules that extract complements from prepositional heads rely on '
                    'pobj/pcomp dependency labels. Parser label mismatches cause no matches.'
                ),
                'upstream': ['IS_DEPENDENT.type', 'TagOccurrence.pos', 'FrameArgument.type'],
                'diagnostics': [
                    "MATCH (f:FrameArgument) WHERE f.type = 'ARGM-TMP' RETURN count(f) AS cnt",
                    "MATCH ()-[r:IS_DEPENDENT {type: 'pobj'}]-() RETURN count(r) AS cnt",
                ],
            },
            'coref_propagation': {
                'rationale': (
                    'Copying KB metadata from antecedents assumes coref chains and ' 
                    'that antecedent nodes are correctly disambiguated. Verify coref coverage.'
                ),
                'upstream': ['CorefMention', 'Antecedent', 'NamedEntity.kb_id'],
                'diagnostics': [
                    "MATCH (a:Antecedent) RETURN count(a) AS cnt",
                    "MATCH (n:NamedEntity) WHERE n.kb_id IS NOT NULL RETURN count(n) AS cnt",
                ],
            }
        }

        return notes


# PHASE 1
# Identification of HEADWORD and assigning related metadata about headword
# Subjects include, NamedEntity, Antecedent, CorefMention, FrameArgument

    # NamedEntity Multitoken
    def get_and_assign_head_info_to_entity_multitoken(self):
        """Assign grammatical head token for multi-token NamedEntity spans.

        Preconditions:
        - `TagOccurrence` nodes exist and are connected with `PARTICIPATES_IN`
          to `NamedEntity` nodes.
        - Dependency edges `IS_DEPENDENT` exist between TagOccurrences.

        Side effects:
        - Sets `f.head`, `f.headTokenIndex` and `f.syntacticType` on the
          `NamedEntity` node when a head candidate is found.

        Business rationale:
        - Having a canonical head token for multi-token NamedEntity spans
          simplifies matching between different annotations and downstream
          entity linking steps. For instance, 'European Central Bank' should
          provide a single token ('Bank') as the head for consolidation
          and matching.
        """
        logger.debug("get_and_assign_head_info_to_entity_multitoken")
        graph = self.graph
        query = """
                        match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(f:NamedEntity), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc,
                        (case when a.pos in ['NNS', 'NN'] then f END).syntacticType ='NOMINAL',
                        (case when a.pos in ['NNP', 'NNPS'] then f END).syntacticType ='NAM'
                        return p

        """
        data = graph.run(query).data()

        return ""


    # NamedEntity Singletoken
    def get_and_assign_head_info_to_entity_singletoken(self):
        """Assign head information for single-token NamedEntity nodes.

        This method is a no-op for multi-token entities and focuses on cases
        where the NamedEntity is a single token; it sets `head`, `headTokenIndex`
        and `syntacticType` to allow consistent downstream comparisons.
        """
        logger.debug("get_and_assign_head_info_to_entity_singletoken")
        graph = self.graph
        query = """
                        match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(c:NamedEntity)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                        (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL',
                        (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM',
                        (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO'
                        return p

        """
        data = graph.run(query).data()

        return ""


    # Antecedent Multitoken
    def get_and_assign_head_info_to_antecedent_multitoken(self):
        """Assign head for multi-token Antecedent nodes created by coref.

        Antecedent nodes are generated by coreference processing and often span
        multiple tokens. This step assigns the most likely head token by
        consulting dependency edges and setting `head`/`headTokenIndex` on the
        Antecedent node to support linking to NamedEntity instances.
        """
        logger.debug("get_and_assign_head_info_to_antecedent_multitoken")
        graph = self.graph
        # TODO: the head for the NAM should include the whole extent of the name. see newsreader annotation guidelines
        # for more information.
        query = """
                        match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(f:Antecedent), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, 
                        (case when a.pos in ['NNS', 'NN'] then f END).syntacticType ='NOMINAL' ,
                        (case when a.pos in ['NNP', 'NNPS'] then f END).syntacticType ='NAM'
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""


    #Antecedent Singletoken
    def get_and_assign_head_info_to_antecedent_singletoken(self):
                """Assign head info for single-token Antecedent nodes.

                Preconditions:
                - Antecedent nodes exist and are linked to their token `TagOccurrence`
                    via `PARTICIPATES_IN`.
                - Dependency edges `IS_DEPENDENT` may or may not be present; this
                    method targets Antecedent instances where the head is a single
                    token (no dependents within the span).

                Side effects:
                - Sets `head`, `headTokenIndex` and `syntacticType` on the
                    `Antecedent` node to normalise representation for downstream
                    linking to NamedEntity or Entity instances.

                Business rationale:
                - Antecedents are used as authoritative targets for coreference
                    resolution; ensuring they have a canonical head token improves
                    entity linking and corrective NEL heuristics.
                """
                logger.debug("get_and_assign_head_info_to_antecedent_singletoken")
                graph = self.graph

                # query to find the head of an Antecedent when it is a single token
                query = """    
                                                match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(c:Antecedent)
                                                where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                                                WITH c, a, p
                                                set c.head = a.text, c.headTokenIndex = a.tok_index_doc, 
                                                (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL' , 
                                                (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM', 
                                                (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO'
                                                return p     
        
                """
                data= graph.run(query).data()
        
                return ""
        
    #CorefMention Multitoken    
    def get_and_assign_head_info_to_corefmention_multitoken(self):
        """Assign head info to multi-token CorefMention nodes.

        CorefMention nodes may be multi-token mentions produced by coreference
        resolution. This step selects a representative head token and records
        it so later passes can match mentions against NamedEntity nodes or
        resolve pronouns.
        """
        logger.debug("get_and_assign_head_info_to_corefmention_multitoken")
        graph = self.graph
        # TODO: the head for the NAM should include the whole extent of the name. see newsreader annotation guidelines 
        # for more information. 
        query = """    
                        match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(f:CorefMention), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, 
                        (case when a.pos in ['NNS', 'NN'] then f END).syntacticType ='NOMINAL' ,
                        (case when a.pos in ['NNP', 'NNPS'] then f END).syntacticType ='NAM'
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""


    #CorefMention Singletoken
    def get_and_assign_head_info_to_corefmention_singletoken(self):
        """Assign head metadata for single-token CorefMention nodes.

        This complements the multi-token corefmention pass by handling cases
        where the mention maps to a single token (no internal dependents). It
        sets `head`, `headTokenIndex` and a coarse `syntacticType` so later
        refinement rules can match coreference mentions against NamedEntity
        instances and propagate KB identifiers.
        """
        logger.debug("get_and_assign_head_info_to_corefmention_singletoken")
        graph = self.graph

        # query to find the head of a NamedEntity. (case is for entitities composed of  single token )
        query = """    
                        match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(c:CorefMention)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc, 
                        (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL' , 
                        (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM', 
                        (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO'
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""

    #To find head info for the FrameArgument i.e., with single token as head
    # here head is noun or pronoun
    def get_and_assign_head_info_to_frameArgument_singletoken(self):
        """Assign head tokens for single-token FrameArgument nodes.

        FrameArgument nodes represent argument spans from SRL. For single-token
        arguments this method records the head token and a syntactic type so
        later modules (entity linking, event enrichment) can match arguments
        to entities or event participants.
        """
        logger.debug("get_and_assign_head_info_to_frameArgument_singletoken")
        graph = self.graph

        query = """    
                        match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$'])--(c:FrameArgument)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                        (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL' , 
                        (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM', 
                        (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO'
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""


    #To find head info for the FrameArgument i.e., with single token as head
    # here head is noun or pronoun
    def get_and_assign_head_info_to_all_frameArgument_singletoken(self):
                """Assign head tokens for all single-token FrameArguments.

                This is a broad pass that assigns `head`, `headTokenIndex`, and
                `headPos` for FrameArgument nodes whose head is a single token and
                which do not contain internal dependents. It is intentionally
                general-purpose and should be safe to run early in the refinement
                sequence.

                Preconditions:
                - TagOccurrence nodes are present and connected to FrameArgument via
                    `PARTICIPATES_IN`.

                Side effects:
                - Mutates FrameArgument nodes to record head token metadata used by
                    later linking and canonicalisation steps.
                """
                logger.debug("get_and_assign_head_info_to_all_frameArgument_singletoken")
                graph = self.graph

                query = """    
                                                match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$'])--(c:FrameArgument)
                                                where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                                                WITH c, a, p
                                                set c.head = a.text, c.headTokenIndex = a.tok_index_doc, c.headPos = a.pos
                                                return p
    
        
                """
                data= graph.run(query).data()
        
                return ""



        

    #To find head info for the FrameArgument i.e., with single token as head
    # here head is noun or pronoun
    def get_and_assign_head_info_to_temporal_frameArgument_singletoken(self):
        """Handle single-token temporal FrameArguments (ARGM-TMP and alike).

        Temporal frame arguments often use adverbs or nominal expressions as
        single-token signals (e.g., 'yesterday', 'today', or 'soon'). This
        method captures those tokens and assigns `head`, `headTokenIndex` and
        a coarse `syntacticType` so the TemporalPhase can later link FAs to
        TIMEX/TEvent nodes during enrichment.
        """
        logger.debug("get_and_assign_head_info_to_temporal_frameArgument_singletoken")
        graph = self.graph
        # query = """    
        #                 match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$', 'RB'])--
        #                 (c:FrameArgument {type:'ARGM-TMP'})
        #                 where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
        #                 WITH c, a, p
        #                 set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
        #                 (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL' , 
        #                 (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM', 
        #                 (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO',
        #                 (case when a.pos in ['RB'] then c END).syntacticType ='ADV'
        #                 return p    
        
        # """

        query = """    
                        match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$', 'RB'])--
                        (c:FrameArgument)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                        (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL' , 
                        (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM', 
                        (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO',
                        (case when a.pos in ['RB'] then c END).syntacticType ='ADV'
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""


    #To find head info for the FrameArgument i.e., with multi token as head
    #here the head is noun or pronoun
    def get_and_assign_head_info_to_frameArgument_multitoken(self):
                """Assign head tokens for multi-token FrameArgument nodes.

                This pass looks for TagOccurrence tokens that participate in a
                multi-token FrameArgument and which act as the syntactic head (i.e.
                they have outgoing dependency links into the argument but no
                incoming dependents from inside the span). It records head text,
                token index and a coarse `syntacticType` derived from POS.

                Preconditions:
                - FrameArgument and TagOccurrence nodes exist and are linked via
                    `PARTICIPATES_IN`.

                Side effects:
                - Sets `head`, `headTokenIndex` and `syntacticType` on FrameArgument
                    nodes where a head can be determined.
                """
                logger.debug("get_and_assign_head_info_to_frameArgument_multitoken")
                graph = self.graph
        
                query = """    
                                                match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$'])-
                                                [:PARTICIPATES_IN]->(f:FrameArgument), q= (a)-[:IS_DEPENDENT]->()--(f)
                                                where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                                                WITH f, a, p
                                                set f.head = a.text, f.headTokenIndex = a.tok_index_doc, 
                                                (case when a.pos in ['NNS', 'NN'] then f END).syntacticType ='NOMINAL' , 
                                                (case when a.pos in ['NNP', 'NNPS'] then f END).syntacticType ='NAM',  
                                                (case when a.pos in ['PRP', 'PRP$'] then f END).syntacticType ='PRO'
                                                return p    
        
                """
                data= graph.run(query).data()
        
                return ""



 




    #General rule to get and assign head of all multi-token framearguments
    def get_and_assign_head_info_to_all_frameArgument_multitoken(self):
        """Assign head token metadata for all multi-token FrameArguments.

        This general pass is similar to the single-type version but records
        the `headPos` as well. Run this after token-level and dependency
        annotation are available. It is idempotent and safe to rerun.
        """
        logger.debug("get_and_assign_head_info_to_all_frameArgument_multitoken")
        graph = self.graph
        
        query = """    
                        match p= (a:TagOccurrence)-[:PARTICIPATES_IN]->(f:FrameArgument), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.headPos = a.pos 
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""

    # // This query first find out those FrameArguments of type ['ARG1', 'ARG0', 'ARG2', 'ARG3', 'ARG4', 'ARGA', 'ARGM-TMP'] and
    # // which have 'preposition' as a headword. 
    # // Then It finds out the complement (pobj) of the preposition and mark it as 
    # // complement. This complement will be used to refer to the entity. 
    # // NOTE: The preoposition word will help in understanding the type of association between frame and
    # // the frameargument with respect to the preposition and complement (noun) entity. 
    #// UPDATE: ARGM-TMP is added in the list of allowable types. 
    def get_and_assign_head_info_to_frameArgument_with_preposition(self):

        logger.debug("get_and_assign_head_info_to_frameArgument_with_preposition")
        graph = self.graph

        query = """    
                        match p= (a:TagOccurrence where a.pos in ['IN'])--
                        (f:FrameArgument where f.type in ['ARG1', 'ARG0', 'ARG2', 'ARG3', 'ARG4', 'ARGA', 'ARGM-TMP']), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='IN'
                        with *
                        match (a)-[x:IS_DEPENDENT]->(c) where x.type = 'pobj' 
                        set f.complement = c.text, f.complementIndex = c.tok_index_doc, 
                        f.complementFullText = substring(f.text, size(f.head)+1)
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""





    #To find head info for the FrameArgument i.e., with multi token as head
    #// It shows when an action took place
    # // case: when headword in an FA is a verb connected with preposition via MARK dep-parse relation.
    # // the text is a clause starts with some temporal preposition such as 
    # // after, before, 
    # #// COMMON OBSERVATIONS: 
    # #// - FA has type ARGM-TMP
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of TLINK  
    def get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark(self):

        logger.debug("get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark")
        graph = self.graph
        # Relax POS constraints: allow several verb POS tags (VBD/VB/VBG/VBZ/VBN/VBP)
        # so we don't miss eventive constructions due to tagging variation.
        query = """
                        match p= (s:TagOccurrence where s.pos = 'IN')<-[:IS_DEPENDENT {type: 'mark'}]
                        -(a:TagOccurrence where a.pos in ['VBD','VB','VBG','VBZ','VBN','VBP'])-
                        [:PARTICIPATES_IN]->(f:FrameArgument where f.type = 'ARGM-TMP'), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p,s
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = s.text
                        return p

        """
        data= graph.run(query).data()

        return ""



    #To find head info for the FrameArgument which has type of ARGM-TMP i.e., with multi token as head
    #// It shows when an action took place
    # // case: when headword in an FA is a preposition connected with verb gerund (complement) via pcomp dep-parse relation.
    # // the text is a clause starts with some temporal preposition such as 
    # // after, before,    
    #// COMMON OBSERVATIONS:
    #// - FA has type ARGM-TMP
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of TLINK
    def get_and_assign_head_info_to_temporal_frameArgument_multitoken_pcomp(self):
                        """Handle temporal FrameArguments where a preposition links to a VBG via pcomp.

                        Pattern: preposition (IN) participates in a FrameArgument of type
                        'ARGM-TMP' and has a 'pcomp' dependent that is a gerund (VBG).

                        Effect:
                        - Records `head`, `headTokenIndex`, `syntacticType='EVENTIVE'`,
                            `signal` (preposition text) and `complement` (the VBG text).

                        Business rationale:
                        - These constructions commonly express temporal relations (e.g.
                            "in following doing X") and capturing both the signal and the
                            gerund complement supports TLINK detection and event enrichment.
                        """
                        # use shared graph established in __init__
                        graph = self.graph

                        query = """    
                                                        match p= (f)--(v:TagOccurrence {pos: 'VBG'})<-[l:IS_DEPENDENT {type: 'pcomp'}]-
                                                        (a:TagOccurrence where a.pos in ['IN'])-[:PARTICIPATES_IN]->(f:FrameArgument where f.type = 'ARGM-TMP')
                                                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                                                        WITH f, a, p, v
                                                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = a.text, f.complement = v.text
                                                        return p     
        
                        """
                        data= graph.run(query).data()

                        return ""

#To find head info for the FrameArgument i.e., with multi token as head
    #// It shows when an action took place
    # // case: when headword in an FA is a preposition connected with verb gerund (complement) via pcomp dep-parse relation.  
    #// COMMON OBSERVATIONS:
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of Link
    def get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp(self):
        """Assign eventive metadata for FrameArguments with pcomp-linked gerunds.

        This method is a close variant of the temporal pcomp handler. It
        captures cases where a gerund (VBG) is attached through a pcomp
        dependency and records the same set of fields used by temporal
        processing: `head`, `headTokenIndex`, `syntacticType`, `signal`, and
        `complement`.
        """
        logger.debug("get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp")
        graph = self.graph

        query = """    
            match p= (f)--(v:TagOccurrence {pos: 'VBG'})<-[l:IS_DEPENDENT {type: 'pcomp'}]-
            (a:TagOccurrence where a.pos in ['IN'])-[:PARTICIPATES_IN]->(f:FrameArgument)
            where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
            WITH f, a, p, v
            set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = a.text, f.complement = v.text
            return p    
        
        """
        data= graph.run(query).data()

        return ""

    
    #To find head info for the FrameArgument which has type of ARGM-TMP i.e., with multi token as head
    #// CASE: has root as a verb. But this verb is acting like a preposition as it has POBJ link with an object. 
    #// example can be following in 'following the European Central Bank' 
    #// to see more detail: check pobj in https://downloads.cs.stanford.edu/nlp/software/dependencies_manual.pdf
    #// COMMON OBSERVATIONS: 
    #// - FA has type ARGM-TMP
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of TLINK
    def get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj(self):
        """Handle temporal FrameArguments where a preposition has a POBJ dependent.

        These patterns capture constructions like 'following the X' where the
        preposition (IN) governs a pobj that is the complement. We record the
        preposition as the `head/signal` and the pobj as the `complement` so
        later entity linking can match the complement against NamedEntities.
        """
        logger.debug("get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj")
        graph = self.graph
        # The original query filtered on a.text = 'following' which is too strict
        # and caused no matches. Remove that specific filter and accept the POS
        # constraints as-is so commonly observed prepositions (in, on, of, by)
        # are picked up.
        query = """
                        match p= (f)--(v:TagOccurrence)<-[l:IS_DEPENDENT {type: 'pobj'}]-
                        (a:TagOccurrence where a.pos in ['IN', 'VBG'])-[:PARTICIPATES_IN]->(f:FrameArgument where f.type = 'ARGM-TMP')
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p, v
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = a.text, f.complement = v.text
                        return p     
        """
        data= graph.run(query).data()

        return ""








# PHASE 2 
# Linking FA to NamedEntity

    # //WE JUST NEED TO CONNECT FA TO NAMED ENTITY. 
    # //CASE: when FA's headword is either a proper noun or common noun
    # // It is straight forward as the named entity and FA both sharing the same headword
    def link_frameArgument_to_namedEntity_for_nam_nom(self):
        """Link FrameArguments to NamedEntity nodes when heads match.

        This rule creates a REFERS_TO edge for FrameArguments whose head
        token index matches a NamedEntity head token. It targets proper
        noun and common-noun matches where the head token is sufficient to
        identify the entity instance.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_nam_nom")
        graph = self.graph

        query = """    
                        match p= (f:FrameArgument)<-[:PARTICIPATES_IN]-(head:TagOccurrence )-[:PARTICIPATES_IN]->(ne:NamedEntity)
                        where head.tok_index_doc = f.headTokenIndex and head.tok_index_doc = ne.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""

    # //WE JUST NEED TO CONNECT FA TO NAMED ENTITY. 
    # //CASE: when FA's headword is a prepostion. In this case we gonna see the POBJ headword and match it with namedEntity.
    # TODO: add pobj as type of refers_to relationship
    def link_frameArgument_to_namedEntity_for_pobj(self):
        """Link prepositional FrameArguments to NamedEntity using complement index.

        For FAs whose syntactic head is a preposition, the actual referent is
        often the preposition's object (complement). This rule links the FA
        to a NamedEntity whose headTokenIndex matches the recorded
        `complementIndex`.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_pobj")
        graph = self.graph

        query = """    
                        match p= (f:FrameArgument)<-[:PARTICIPATES_IN]-(complementHead:TagOccurrence )-[:PARTICIPATES_IN]->(ne:NamedEntity)
                        where complementHead.tok_index_doc = f.complementIndex and complementHead.tok_index_doc = ne.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""



    # //WE JUST NEED TO CONNECT FA (prepositional) TO NAMED ENTITY. 
    # //CASE:  when FA refereing to an entity but not named entity. usually such situation it refering to nominal. 
    # //CASE: when FA's headword is a prepostion. In this case we gonna see the POBJ headword and match it with Entity.
    # // this query try to find those FAs who do not have any entity instance created during NER or NEL.  
    # // MISSING: fields such as extent, type(set here temporarily). Further, entity disambiguation and deduplication may be required. 
    # // coreferencing information can be employed to deduplicate entities.  
    def link_frameArgument_to_namedEntity_for_pobj_entity(self):
        """Create Entity nodes when a complement doesn't map to a NamedEntity.

        Some prepositional complements refer to nominal entities that were not
        recognized by NER/NEL. This rule creates a lightweight `Entity`
        node using the complement's full text and links the FrameArgument to
        it. This is a best-effort step and may require later deduplication or
        KB linking.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_pobj_entity")
        graph = self.graph

        query = """    
                        MATCH p= (f:FrameArgument where f.type in ['ARG0','ARG1','ARG2','ARG3','ARG4'])-[:PARTICIPATES_IN]-
                        (complementHead:TagOccurrence)
                        where f.complementIndex = complementHead.tok_index_doc and not exists 
                        ((complementHead)-[]-(:NamedEntity {headTokenIndex: complementHead.tok_index_doc})) and not exists
                        ((f)-[:REFERS_TO]-(:NamedEntity))
                        MERGE (e:Entity {id: f.complementFullText})
                        ON CREATE SET e.type = complementHead.pos, e.syntacticType = complementHead.pos, e.head = f.complement, e.headTokenIndex = f.complementIndex
                        MERGE (complementHead)-[:PARTICIPATES_IN]->(e)
                        MERGE (f)-[:REFERS_TO]->(e)
                        RETURN p   
        
        """
        data= graph.run(query).data()
        
        return ""
    

    # //WE JUST NEED TO CONNECT FA TO NAMED ENTITY. 
    # //CASE: when FA's headword is a pronominal i.e., having pos value as PRP or PRP$
    # // we designed this query because we need to deal with FAs who have pronominal token. 
    # //we need the path to the named entity via coref-antecedent links
    def link_frameArgument_to_namedEntity_for_pro(self):
        """Link pronominal FrameArguments to NamedEntity using coreference.

        For FAs headed by pronouns, we follow CorefMention -> Antecedent ->
        NamedEntity chains to resolve the pronoun to an entity and create a
        REFERS_TO link. This allows pronoun-bearing arguments to participate
        in event enrichment.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_pro")
        graph = self.graph

        query = """    
                        match p= (f:FrameArgument)<-[:PARTICIPATES_IN]-(head:TagOccurrence )-[:PARTICIPATES_IN]->
                        (crf:CorefMention)--(ant:Antecedent)-[:REFERS_TO]->(ne:NamedEntity)
                        where head.pos in ['PRP','PRP$'] and head.tok_index_doc = f.headTokenIndex and head.tok_index_doc = crf.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""

    # // this query try to find those FAs who do not have any entity instance created during NER or NEL.  
    # // TODO: fields such as extent, type(set here temporarily). Further, entity disambiguation and deduplication may be required. 
    # // coreferencing information can be employed to deduplicate entities.
    # // CASES NOT COVERED: 
    # // 1: when FA has text span which has more than one entity. For example, 'millions of people', here we have million as numeric and millions of people as nominal.
    # //    -- perhaps these overlapping spans denoting multiple entities can be handled using SPANCAT. R&D is required 
    # //    -- presently, the pipeline tag 'millions' as CARDINAL and refers_to connection is establish between FA and CARDINAL entity. However this connection is not
    # //    -- correct as the correct entity is 'millions of people' which is NOMINAL.  Though head of FA is 'millions' in this phrase. 
    def link_frameArgument_to_new_entity(self):
        """Create generic Entity nodes for FrameArguments not mapped to NamedEntity.

        When an FA does not refer to a NamedEntity (e.g., common nouns or
        nominal phrases), this rule creates an `Entity` node and links the
        FA to it. The created Entity uses the FA text as a simple identifier
        and stores syntactic metadata to support later deduplication.
        """
        logger.debug("link_frameArgument_to_new_entity")
        graph = self.graph

        query = """    
                        MATCH p= (f:FrameArgument where f.type in ['ARG0','ARG1','ARG2','ARG3','ARG4'] and f.syntacticType <> 'PRO')
                        -[:PARTICIPATES_IN]-(h:TagOccurrence where not  h.pos  in ['IN'])
                        where f.headTokenIndex = h.tok_index_doc 
                        and not exists ((h)-[]-(:NamedEntity {headTokenIndex: h.tok_index_doc}))
                        merge (e:Entity {id:f.text, type:f.syntacticType, 
                        syntacticType:f.syntacticType, head:f.head})
                        merge (f)-[:REFERS_TO]->(e)
                        RETURN p     
        
        """
        data= graph.run(query).data()
        
        return ""

    # //WE JUST NEED TO CONNECT ANTECEDENT TO NAMED ENTITY.
    def link_antecedent_to_namedEntity(self):
        """Link Antecedent nodes to NamedEntity instances when heads match.

        Antecedents produced by coreference resolution often correspond to
        NamedEntity instances. This rule creates a REFERS_TO relation when
        the head token index matches; it is useful to propagate authoritative
        entity identifiers into coreference structures.
        """
        logger.debug("link_antecedent_to_namedEntity")
        graph = self.graph

        query = """    
                        match p= (f:Antecedent)<-[:PARTICIPATES_IN]-(head:TagOccurrence )-[:PARTICIPATES_IN]->(ne:NamedEntity)
                        where head.tok_index_doc = f.headTokenIndex and head.tok_index_doc = ne.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""

        


    
# //It will add another label to named entities that are qualified as value.
    def tag_numeric_entities(self):
        """Add a `NUMERIC` label to NamedEntity nodes representing numeric values.

        This is a lightweight normalization step that marks certain NE
        semantic types (MONEY, QUANTITY, PERCENT) with an additional label
        to simplify downstream numeric handling and event enrichment.
        """
        logger.debug("tag_numeric_entities")
        graph = self.graph

        query = """    
                        match (ne:NamedEntity) where ne.type in ['MONEY', 'QUANTITY', 'PERCENT']
                        set ne:NUMERIC   
        
        """
        data= graph.run(query).data()
        
        return ""



    # //It will add another label to named entities that are qualified as value.
    def tag_value_entities(self):
        """Add a `VALUE` label to NamedEntity nodes that represent counted or measured values.

        This includes cardinal/ordinal and other value-like types to make it
        easier to find and operate on numeric or quantified entities during
        enrichment and evaluation.
        """
        logger.debug("tag_value_entities")
        graph = self.graph

        query = """    
                        match (ne:NamedEntity) where ne.type in ['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']
                        set ne:VALUE   
        
        """
        data= graph.run(query).data()
        
        return ""


    #// CASE Incorrect Named Entity Disambiguation (Example 1: JIM CRAMER detected as PIETER CRAMER which is wrong)
    #// 
    #// NED processing has not accurately disambiguated an entity. We are using Coref information to detect and correct the incorrect result
    #// ASSUMPTION: that the antecedent is correctly disambiguated and we should rely on it. d
    #// Here we are giving preference to NamedEntity refered by Antecedent node. Replacing the incorrect with the correct one.  
    #// PRECONDITION: KB_ID attributes of both NamedEntities are not null. This query should be run before the Frameargument linking with NamedEntity
    #// cases - 1. kb_id of both namedEntities are not null (DONE in this query)
    #//         2. ne1 doesnt have kb_id and ne2 has kb_id  (e.g., Fed as a spacy entity but actually refering to dbpedia Federal Researve)(DONE in next query v2)
    #//               
    def detect_correct_NEL_result_for_having_kb_id(self):
        """Correct Named Entity Linking (NEL) when both NE candidates have KB ids.

        Uses coreference chains to prefer the entity linked from the
        Antecedent/coref chain when two different NamedEntity nodes (ne1,
        ne2) with different KB identifiers are observed for the same
        mention. The method copies authoritative KB metadata from ne2 to ne1
        and consolidates Entity nodes.
        """
        logger.debug("detect_correct_NEL_result_for_having_kb_id")
        graph = self.graph

        query = """    
                        match p= (e1:Entity)<-[:REFERS_TO]-(ne1:NamedEntity)<-[:PARTICIPATES_IN]-(t1:TagOccurrence)-[:PARTICIPATES_IN]->(coref:CorefMention)-[:COREF]->(ant:Antecedent)-[:REFERS_TO]->(ne2:NamedEntity)-[:REFERS_TO]->(e2:Entity)
                        where t1.text = ne1.head and t1.text = coref.head and ne1.kb_id is not null and ne2.kb_id is not null and ne1.kb_id <> ne2.kb_id
                        set ne1.kb_id = ne2.kb_id, ne1.description = ne2.description, ne1.normal_term = ne2.normal_term, ne1.url_wikidata = ne2.url_wikidata,ne1.type = ne2.type
                        detach delete e1
                        merge (ne1)-[:REFERS_TO]->(e2)
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""




    #// detecting and correcting named entities result. 
    #// Using the coreferencing information, and assuming antecedent refering to correct entity.
    #// CONDITION: if entity of token from any of the corefmention is not equal to entity refered by antecedent.
    #// CONDITION: ne1 doesnt have kb_id and ne2 has kb_id  (e.g., Fed as a spacy entity but actually refering to dbpedia Federal Researve)              
    def detect_correct_NEL_result_for_missing_kb_id(self):
        """Copy KB metadata when a coreferent NE has a KB id and the other lacks it.

        If a NamedEntity `ne1` lacks a KB id but its coreferent `ne2` has one,
        prefer `ne2`'s metadata and link `ne1` to the authoritative Entity.
        This helps salvage disambiguation information from coreference.
        """
        logger.debug("detect_correct_NEL_result_for_missing_kb_id")
        graph = self.graph

        query = """    
                        match p= (e1:Entity)<-[:REFERS_TO]-(ne1:NamedEntity)<-[:PARTICIPATES_IN]-(t1:TagOccurrence)-[:PARTICIPATES_IN]->(coref:CorefMention)-[:COREF]->(ant:Antecedent)-[:REFERS_TO]->(ne2:NamedEntity)-[:REFERS_TO]->(e2:Entity)
                        where t1.text = ne1.head and t1.text = coref.head and ne1.kb_id is null and ne2.kb_id is not null
                        set ne1.kb_id = ne2.kb_id, ne1.spacyType = ne1.type, ne1.type = ne2.type, ne1.description = ne2.description, ne1.normal_term = ne2.normal_term, ne1.url_wikidata = ne2.url_wikidata
                        detach delete e1
                        merge (ne1)-[:REFERS_TO]->(e2)
                        return p    
        
        """
        data= graph.run(query).data()
        return ""
         



    # // This method detects the presence of quantified entities and create a new instance of it. 
    # // It will first see whether the head token in frameArgument denotes a NUMERIC value (as a namedEntity) or some quantified signal such as all, some, many etc
    # // and it is satisfying the following noun phrase composition:
    # // (head {any quantifier}) --- (preposition {text:'of'}) --- (noun) e.g., millions of people, some of the players etc.
    # // it deletes the existing REFERS_TO relationship between frameArgument and (numeric)NamedEntity. creates a new Entity and link frameArgument with that entity. 
    # // PRECONDITIONS: should be executed after NER, NEL, head-identification, linking FA to namedEntities, entities.    
    # // TODO: currently it only assign a type as NOMINAL to newly created entity. But it needs to be improved to detect PARTITIVE constructions. 
    # // also it should be able to differentiate between partitive and nominal instances. for more detail see page 20 of 
    # // 'NEWSREADER GUIDELINES FOR ANNOTATION AT DOCUMENT LEVEL' NWR-2014-2-2
    def detect_quantified_entities_from_frameArgument(self):
        """Detect and create Entity nodes for quantified constructions.

        Example patterns: 'millions of people', 'some of the players'. The
        method looks for 'head of pobj' constructions where the head is a
        quantifier or linked to a CARDINAL NamedEntity and replaces numeric
        NE links with a new nominal `Entity` representing the quantified
        group.
        """
        logger.debug("detect_quantified_entities_from_frameArgument")
        graph = self.graph

        query = """    
                            match p = (pobj:TagOccurrence where pobj.pos in ['NNS','NNP','NN', 'NNPS','PRP', 'PRP$'])<-[dep2:IS_DEPENDENT {type: 'pobj'}]
                            -(prep:TagOccurrence where prep.text= 'of')<-[dep1:IS_DEPENDENT {type: 'prep'}]-(head:TagOccurrence {tok_index_doc : fa.headTokenIndex})-
                            [:PARTICIPATES_IN]->(fa:FrameArgument), (pobj)--(fa)
                            where exists ((head)-[:PARTICIPATES_IN]->(:NamedEntity {type: 'CARDINAL'})) OR head.lemma in ['all', 'some', 'many', 'group']
                            merge (fa)-[:REFERS_TO]->(e:Entity {id: fa.text, type: 'NOMINAL'})
                            with fa,p
                            match (fa)-[r:REFERS_TO]->(ne:NamedEntity)
                            delete r
                            return p    
        
        """
        data= graph.run(query).data()
        
        return ""


    # Link FA to Entity by using their links with NamedEntities. path = FA --> NE --> E  implies FA --> E
    def link_frameArgument_to_entity_via_named_entity(self):
        """Propagate Entity links from NamedEntity targets to FrameArguments.

        If a FrameArgument refers to a NamedEntity which in turn refers to an
        Entity, this method creates a direct REFERS_TO edge between the FA
        and the Entity. Useful to flatten indirection and make entity
        attributes accessible to FA-based enrichment.
        """
        logger.debug("link_frameArgument_to_entity_via_named_entity")
        graph = self.graph

        query = """    
                        match p = (fa:FrameArgument)-[:REFERS_TO]->(ne:NamedEntity)-[:REFERS_TO]-(e:Entity)
                        merge (fa)-[:REFERS_TO]-(e)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""


    #//It connects frame argument to numeric entities.
    #//PRECONDITION: query 'detect_quantified_entities_from_frameArgument' in refinment phase must be run before this. 
    #//Because, cases like 'millions of people' actually refering to nominal rather numeric
    #//It checks that frame argument is not yet connected to entity. If it exists it means it is a case about quantified entities. 
    def link_frameArgument_to_numeric_entities(self):
        """Link FrameArguments to numeric NamedEntity nodes (labelled NUMERIC).

        Numeric NamedEntities (e.g., MONEY, QUANTITY) are marked with the
        `NUMERIC` label by earlier passes. This method connects FAs whose
        head token matches a numeric NamedEntity and which are not already
        linked to a generic Entity.
        """
        logger.debug("link_frameArgument_to_numeric_entities")
        graph = self.graph

        query = """    
                        MATCH p = (f:FrameArgument)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:PARTICIPATES_IN]->(e:NUMERIC)
                        where f.headTokenIndex = t.tok_index_doc and not exists ((f)-[:REFERS_TO]-(:Entity))
                        merge (f)-[:REFERS_TO]-(e)
                        return p
        
        """
        data= graph.run(query).data()
        
        return ""





if __name__ == '__main__':
    tp= RefinementPhase(sys.argv[1:])
    tp.run_all_rule_families()

    # Record a lightweight run marker in the database so we can detect that
    # the refinement sequence was executed. This is intentionally minimal: a
    # single node with a timestamp and the list of passes we ran. It is safe
    # to run repeatedly (MERGE by id) and useful for audits / CI checks.
    try:
        from datetime import datetime
        run_id = datetime.utcnow().isoformat()
        passes = [name for _, name in tp.iter_rule_names()]

        marker_q = """
        MERGE (r:RefinementRun {id: $id})
        SET r.timestamp = $ts, r.passes = $passes
        RETURN id(r) as result
        """
        tp.graph.run(marker_q, {"id": run_id, "ts": run_id, "passes": passes}).data()
        logger.info("Recorded RefinementRun %s with %d passes", run_id, len(passes))
    except Exception:
        logger.exception("Failed to write refinement run marker (non-fatal)")






# custom labels for non-core arguments and storing it as a node attribute: argumentType. The second step the value in the fa.argumentType 
# will be set as a label for this node. It will perform event enrichment fucntion as well as attaching propbank modifiers arguments 
# with the event node. 
# TODO: Though we have found fa nodes with duplicates content with same label or arg type but we will deal with it later. 
# 
# 
# MATCH (event:TEvent)<-[:DESCRIBES]-(f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
# WHERE not fa.type IN ['ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'ARGM-TMP']
# WITH event, f, fa
# SET fa.argumentType=
#     CASE fa.type
#     WHEN 'ARGM-MNR' THEN 'Manner'
#     WHEN 'ARGM-ADV' THEN 'Adverbial'
#     WHEN 'ARGM-DIR' THEN 'Direction'
#     WHEN 'ARGM-DIS' THEN 'Discourse'
#     WHEN 'ARGM-LOC' THEN 'Location'
#     WHEN 'ARGM-PRP' THEN 'Purpose'
#     WHEN 'ARGM-CAU' THEN 'Cause'
#     WHEN 'ARGM-EXT' THEN 'Extent'
#     ELSE 'NonCore'
#     END
# MERGE (fa)-[r:PARTICIPANT]->(event)
# SET r.type = fa.type,
#     (CASE WHEN fa.syntacticType IN ['IN'] THEN r END).prep = fa.head 
# RETURN event, f, fa, r




#VERSION 2 of the previous query with additional propbank arguments
# MATCH (event:TEvent)<-[:DESCRIBES]-(f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
# WHERE NOT fa.type IN ['ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'ARGM-TMP']
# WITH event, f, fa
# SET fa.argumentType =
#     CASE fa.type
#     WHEN 'ARGM-COM' THEN 'Comitative'
#     WHEN 'ARGM-LOC' THEN 'Locative'
#     WHEN 'ARGM-DIR' THEN 'Directional'
#     WHEN 'ARGM-GOL' THEN 'Goal'
#     WHEN 'ARGM-MNR' THEN 'Manner'
#     WHEN 'ARGM-TMP' THEN 'Temporal'
#     WHEN 'ARGM-EXT' THEN 'Extent'
#     WHEN 'ARGM-REC' THEN 'Reciprocals'
#     WHEN 'ARGM-PRD' THEN 'SecondaryPredication'
#     WHEN 'ARGM-PRP' THEN 'PurposeClauses'
#     WHEN 'ARGM-CAU' THEN 'CauseClauses'
#     WHEN 'ARGM-DIS' THEN 'Discourse'
#     WHEN 'ARGM-MOD' THEN 'Modals'
#     WHEN 'ARGM-NEG' THEN 'Negation'
#     WHEN 'ARGM-DSP' THEN 'DirectSpeech'
#     WHEN 'ARGM-ADV' THEN 'Adverbials'
#     WHEN 'ARGM-ADJ' THEN 'Adjectival'
#     WHEN 'ARGM-LVB' THEN 'LightVerb'
#     WHEN 'ARGM-CXN' THEN 'Construction'
#     ELSE 'NonCore'
#     END
# MERGE (fa)-[r:PARTICIPANT]->(event)
# SET r.type = fa.type,
#     (CASE WHEN fa.syntacticType IN ['IN'] THEN r END).prep = fa.head 
# RETURN event, f, fa, r


# 2nd step where we set the labels for the non-core fa arguments
# MATCH (fa:FrameArgument)
# WHERE fa.argumentType is not NULL
# CALL apoc.create.addLabels(id(fa), [fa.argumentType]) YIELD node
# RETURN node



##
#


#
##









