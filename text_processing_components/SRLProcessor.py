from py2neo import Graph, Relationship
from py2neo import Node


class SRLProcessor:
    def __init__(self, uri, username, password):
        """
        Initialize the SRLProcessor with the graph database connection details.

        Args:
        uri (str): The URI of the graph database.
        username (str): The username for authentication.
        password (str): The password for authentication.
        """
        self.uri = uri
        self.username = username
        self.password = password

    def process_srl(self, doc, flag_display=False):
        """
        Process the SRL (Semantic Role Labeling) for the given document.

        Args:
        doc: The document to process.
        flag_display (bool): A flag to control the display of the results. Defaults to False.
        """
        graph = Graph(self.uri, auth=(self.username, self.password))
        PARTICIPANT = Relationship.type("PARTICIPANT")
        PARTICIPATES_IN = Relationship.type("PARTICIPATES_IN")

        for tok in doc:
            frameDict = {}
            v = None
            sg = None

            for x, indices_list in tok._.SRL.items():
                for y in indices_list:
                    span = doc[y[0]: y[len(y) - 1] + 1]
                    token = span.root
                    if x == "V":
                        v = Node("Frame", headword= token.text, headTokenIndex= token.i, text=span.text, startIndex=y[0], endIndex=y[len(y) - 1])
                        for index in y:
                            query = "MATCH (x:TagOccurrence {tok_index_doc:" + str(
                                index) + "})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]-(:AnnotatedText {id:" + str(
                                doc._.text_id) + "}) RETURN x"
                            token_node = graph.evaluate(query)
                            token_verb_rel = PARTICIPATES_IN(token_node, v)
                            graph.create(token_verb_rel)

                        sg = v
                    else:
                        a = Node("FrameArgument", head= token.text, headTokenIndex= token.i, type=x, text=span.text, startIndex=y[0], endIndex=y[len(y) - 1])

                        if a is None:
                            continue

                        for index in y:
                            query = "MATCH (x:TagOccurrence {tok_index_doc:" + str(
                                index) + "})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]-(:AnnotatedText {id:" + str(
                                doc._.text_id) + "}) RETURN x"
                            token_node = graph.evaluate(query)

                            if token_node is None:
                                continue

                            token_arg_rel = PARTICIPATES_IN(token_node, a)
                            graph.create(token_arg_rel)

                        if x not in frameDict:
                            frameDict[x] = []
                        frameDict[x].append(a)

            if sg is not None:
                for i in frameDict:
                    for arg_node in frameDict[i]:
                        r = PARTICIPANT(arg_node, sg)
                        graph.create(r)

                try:
                    graph.create(sg)
                except BaseException as err:
                    print(f"Unexpected {err=}, {type(err)=}")