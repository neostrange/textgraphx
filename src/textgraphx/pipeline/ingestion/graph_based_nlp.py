import os
import spacy
import sys
import importlib
import argparse
from pathlib import Path
# When running this file directly (python textgraphx/GraphBasedNLP.py),
# make sure the repository root is on sys.path so package imports work.
if __package__ is None and __name__ == "__main__":
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))
from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel
from textgraphx.util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from textgraphx.util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
from textgraphx.pipeline.ingestion.text_processor import TextProcessor
import xml.etree.ElementTree as ET
if not hasattr(spacy, "__path__"):
    try:
        for module_name in list(sys.modules):
            if module_name == "spacy" or module_name.startswith("spacy."):
                del sys.modules[module_name]
        spacy = importlib.import_module("spacy")
    except Exception:
        pass

try:
    from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER
    from spacy.lang.char_classes import CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS
    from spacy.util import compile_infix_regex
except Exception:
    ALPHA = ALPHA_LOWER = ALPHA_UPPER = ""
    CONCAT_QUOTES = LIST_ELLIPSES = LIST_ICONS = []

    def compile_infix_regex(*_args, **_kwargs):
        raise RuntimeError("spaCy language char classes unavailable")
from neo4j import GraphDatabase
from textgraphx.text_processing_components.DocumentImporter import MeantimeXMLImporter, resolve_document_id_from_naf_root
from textgraphx.pipeline.ingestion.text_normalization import normalize_naf_raw_text
from textgraphx.infrastructure.config import get_config
# from spacy.util import load_config

# from spacy_llm.util import assemble
# from spacy_llm.registry import registry
# from text_processing_components.llm.registry import openai_llama_3_1_8b
# from spacy import util
import logging
import time
import zlib

# module logger
logger = logging.getLogger(__name__)

# Class representing a graph-based NLP model
class GraphBasedNLP(GraphDBBase):
    # Initializes the NLP model with the given arguments
    def __init__(self, argv, model_name: str = "en_core_web_trf", require_neo4j: bool = False):
        # Calls the parent class's constructor
        super().__init__(command=__file__, argv=argv)
        logger.info("Starting GraphBasedNLP initialization")
        logger.debug("Constructor args: argv=%s, model_name=%s, require_neo4j=%s", argv, model_name, require_neo4j)
        
        # self.config_path="/home/neo/environments/text2graphs/textgraphx/config.cfg"  # Default value provided for config_path argument
        # self.examples_path="/home/neo/environments/text2graphs/textgraphx/examples.json" 

        # Prefer GPU for processing when available
        try:
            spacy.prefer_gpu()
            logger.info("Requested GPU preference for spaCy")
        except Exception:
            # prefer_gpu may fail in some environments; continue on CPU
            logger.debug("spaCy prefer_gpu() failed or is not available; continuing on CPU")
            pass

        # For initial NLP, keep transformer as the default and avoid implicit
        # downgrades to sm/md unless explicitly requested by model_name.

        # Load the requested spaCy model (allow passing lightweight model for quick runs)
        try:
            self.nlp = spacy.load(model_name)
            logger.info("Loaded spaCy model '%s'", model_name)
        except Exception as e:
            fallback_model = os.getenv("TEXTGRAPHX_FALLBACK_MODEL", "").strip()
            fallback_allowed = (
                os.getenv('TEXTGRAPHX_ALLOW_MODEL_FALLBACK', '0') == '1'
                and fallback_model in {'en_core_web_sm', 'en_core_web_md'}
                and fallback_model != model_name
            )
            if not fallback_allowed:
                logger.exception(
                    "Failed to load requested spaCy model '%s' and fallback is disabled. "
                    "Set TEXTGRAPHX_ALLOW_MODEL_FALLBACK=1 and "
                    "TEXTGRAPHX_FALLBACK_MODEL=(en_core_web_sm|en_core_web_md) "
                    "to permit explicit downgrade.",
                    model_name,
                )
                raise
            logger.warning(
                "Failed to load spaCy model '%s': %s. Falling back to '%s'",
                model_name,
                e,
                fallback_model,
            )
            try:
                self.nlp = spacy.load(fallback_model)
                logger.info("Loaded fallback spaCy model '%s'", fallback_model)
            except Exception as e2:
                logger.exception("Failed to load fallback spaCy model '%s': %s", fallback_model, e2)
                raise

        #config = load_config("/home/neo/environments/text2graphs/textgraphx/config.cfg")


        # Add custom components
        # for component in config["nlp"]["pipeline"]:
        #     if component not in self.nlp.pipe_names:
        #         self.nlp.add_pipe(component, config=config["components"][component])
        
        
        
        #self.nlp = assemble(config_path=self.config_path, overrides={"paths.examples": str(self.examples_path)})
        #self.nlp = assemble(config_path=self.config_path)
        # config string may be large for transformer models; log cautiously
        try:
            logger.info("nlp config: %s", self.nlp.config.to_str())
        except Exception:
            logger.debug("nlp config not available or too large to serialize")
        #llm_component = self.nlp.add_pipe("llm", config=llm_config["components"]["llm"], last=True)


        logger.info("PIPELINE: %s", self.nlp.pipeline)
        logger.debug("spaCy pipeline components: %s", self.nlp.pipe_names)
        # Configure the tokenizer
        logger.info("Configuring tokenizer infixes and behavior")
        self._configure_tokenizer()
        # Add pipes to the model
        logger.info("Adding pipeline components/pipes")
        self._add_pipes()

        # Initialize the text processor
        t0 = time.time()
        self.__text_processor = TextProcessor(self.nlp, self._driver)
        self._naf_sentence_mode = get_config().runtime.naf_sentence_mode
        logger.info("TextProcessor initialized in %.3fs", time.time() - t0)
        # expose the neo4j repository from the TextProcessor for backwards compatibility
        try:
            self.neo4j_repository = self.__text_processor.neo4j_repository
            logger.info("Neo4j repository exposed from TextProcessor")
        except Exception:
            self.neo4j_repository = None
            logger.warning("TextProcessor did not expose neo4j_repository; continuing with None")

        # Create constraints in the database
        logger.info("Creating DB constraints (idempotent)")
        start_constraints = time.time()
        self.create_constraints()
        logger.info("create_constraints finished in %.3fs", time.time() - start_constraints)

        # Optionally enforce Neo4j connectivity early with a clear error
        # Allow optional retry attempts via NEO4J_CONNECT_RETRIES env var
        retries = int(os.getenv('NEO4J_CONNECT_RETRIES', '1'))
        try:
            self._check_neo4j(require=require_neo4j, retries=retries)
        except Exception:
            # if _check_neo4j raised, re-raise to fail fast
            raise

    def _check_neo4j(self, require: bool = False, retries: int = 1, backoff_seconds: float = 1.0) -> bool:
        """Test Neo4j connectivity. If `require` is True raise a RuntimeError on failure,
        otherwise log a warning and return False.
        """
        attempt = 0
        last_exc = None
        while attempt < max(1, int(retries)):
            try:
                # Driver.verify_connectivity is a lightweight way to check reachability
                t0 = time.time()
                self._driver.verify_connectivity()
                logger.info("Connected to Neo4j successfully on attempt %d (%.3fs)", attempt + 1, time.time() - t0)
                return True
            except Exception as e:
                last_exc = e
                attempt += 1
                if attempt < retries:
                    sleep_time = backoff_seconds * (2 ** (attempt - 1))
                    logger.warning("Neo4j connectivity check failed on attempt %d, retrying in %.1fs: %s", attempt, sleep_time, e)
                    try:
                        time.sleep(sleep_time)
                    except Exception:
                        pass
                    continue
                # no more retries
                if require:
                    logger.exception("Unable to connect to Neo4j at startup after %d attempt(s): %s", attempt, last_exc)
                    raise RuntimeError(f"Unable to connect to Neo4j after {attempt} attempts: {last_exc}") from last_exc
                else:
                    logger.warning("Neo4j connectivity check failed after %d attempt(s) (continuing in degraded mode): %s", attempt, last_exc)
                    return False

    # Configures the tokenizer with custom infixes
    def _configure_tokenizer(self):
        # Define custom infixes
        infixes = (
            LIST_ELLIPSES 
            + LIST_ICONS
            + [
                r"(?<=[0-9])[+\\-\\*^](?=[0-9-])",
                r"(?<=[{al}{q}])\\.(?=[{au}{q}])".format(
                    al=ALPHA_LOWER, au=ALPHA_UPPER, q=CONCAT_QUOTES
                ),
                r"(?<=[{a}]),(?=[{a}])".format(a=ALPHA),
                r"(?<=[{a}0-9])[:<>=/](?=[{a}])".format(a=ALPHA),
            ]
        )
        
        # Compile the infix regex
        infix_re = compile_infix_regex(infixes)
        
        # Set the infix finditer for the tokenizer
        self.nlp.tokenizer.infix_finditer = infix_re.finditer

    # Adds pipes to the model
    def _add_pipes(self):
        # Add the dbpedia spotlight pipe
        
        # Remove and re-add the srl pipe if it exists
        if "srl" in self.nlp.pipe_names:
            self.nlp.remove_pipe("srl")
            _ = self.nlp.add_pipe("srl")
        
        # Add the srl pipe
        self.nlp.add_pipe("srl")

    # Creates constraints in the database
    def create_constraints(self):
        # Define the constraints
        constraints = [
            "CREATE CONSTRAINT for (u:Tag) require u.id IS NODE KEY",
            "CREATE CONSTRAINT for (i:TagOccurrence) require i.id IS NODE KEY",
            "CREATE CONSTRAINT for (t:Sentence) require t.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:AnnotatedText) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:NamedEntity) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:NamedEntity) require l.uid IS UNIQUE",
            "CREATE CONSTRAINT for (l:EntityMention) require l.uid IS UNIQUE",
            "CREATE CONSTRAINT for (l:Entity) require (l.type, l.id) IS NODE KEY",
            "CREATE CONSTRAINT for (l:Evidence) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:Relationship) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:NounChunk) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:TEvent) require (l.eiid, l.doc_id) IS NODE KEY",
        ]
        
        # Execute each constraint
        for constraint in constraints:
            self.execute_without_exception(constraint)

    # Stores a corpus of text in the database
    def store_corpus(self, directory):
        
        # Keep ingestion deterministic for reproducible multi-document runs.
        existing_ids_query = "MATCH (n:AnnotatedText) RETURN n.id AS id"
        existing = self.neo4j_repository.execute_query(query=existing_ids_query, params={})
        used_doc_ids = set()
        for row in existing or []:
            raw_id = row.get("id")
            if isinstance(raw_id, int):
                used_doc_ids.add(raw_id)
            elif isinstance(raw_id, str) and raw_id.isdigit():
                used_doc_ids.add(int(raw_id))
        
        # Initialize the list of text tuples
        text_tuples = []
        
        # Iterate over each file in the directory
        for filename in sorted(os.listdir(directory)):
            # Construct the full path to the file
            f = os.path.join(directory, filename)
            
            # Check if the file is a file
            if os.path.isfile(f):
                # Log the filename being processed
                logger.info(filename)

                try:
                    # Parse the XML file
                    tree = ET.parse(directory+'/' + filename)
                    root = tree.getroot()

                    stable_fallback_id = self._stable_fallback_doc_id(filename, used_doc_ids)
                    resolved_text_id = resolve_document_id_from_naf_root(root, stable_fallback_id)
                    if isinstance(resolved_text_id, str) and resolved_text_id.isdigit():
                        resolved_text_id = int(resolved_text_id)
                    if not isinstance(resolved_text_id, int):
                        logger.warning(
                            "Resolved non-integer document id '%s' for file '%s'; using stable fallback id=%s",
                            resolved_text_id,
                            filename,
                            stable_fallback_id,
                        )
                        resolved_text_id = stable_fallback_id
                    used_doc_ids.add(resolved_text_id)

                    # Extract text and normalize it for robust sentence segmentation.
                    text = root[1].text if len(root) > 1 else ""
                    naf_sentence_mode = self._naf_sentence_mode
                    text = normalize_naf_raw_text(text, mode=naf_sentence_mode)
                    logger.debug(
                        "Applied NAF sentence normalization mode='%s' for file=%s",
                        naf_sentence_mode,
                        filename,
                    )
                    
                    # Read the text file
                    text_file = open(directory+'/'+filename, 'r')
                    data = text_file.read()
                    text_file.close()
                    
                    # Create an annotated text object
                    # # Usage
                    # driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
                    
                    # document_importer = None
                    # if document_type == "MEANTIME_XML":
                    #     document_importer = MeantimeXMLImporter(id, data, content, neo4j_repository)
                    # elif document_type == "ANOTHER_TYPE":
                    #     document_importer = AnotherDocumentImporter(id, data, content, neo4j_repository)

                    # if document_importer:
                    #     document_importer.import_document()
                    document_importer = MeantimeXMLImporter(resolved_text_id, data, text, self.neo4j_repository)
                    document_importer.import_document()
                    #self.__text_processor.create_annotated_text(data, text, text_id)
                    
                except Exception as e:
                    logger.exception("Error processing file %s", filename)
                
                # Append the annotated text to the list of text tuples
               # text_tuples.append(self.__text_processor.get_annotated_text())
        #text_tuples = tuple(self.__text_processor.get_annotated_text())
        text_tuples = tuple(self.neo4j_repository.get_all_annotated_text_docs())
        # Return the list of text tuples
        return tuple(text_tuples)

    @staticmethod
    def _stable_fallback_doc_id(filename, used_ids):
        # Use a deterministic integer id derived from filename and avoid collisions.
        base_id = zlib.crc32(str(filename).encode("utf-8")) & 0x7FFFFFFF
        if base_id == 0:
            base_id = 1
        doc_id = base_id
        while doc_id in used_ids:
            doc_id = (doc_id + 1) & 0x7FFFFFFF
            if doc_id == 0:
                doc_id = 1
        return doc_id

    # Tokenizes and stores the given text tuples
    def process_text(self, text_tuples, text_id, storeTag):
        # Check if the Doc object has a text_id extension
        if not Doc.has_extension("text_id"):
            # Set the text_id extension
            Doc.set_extension("text_id", default=None)

        # Pipe the text tuples through the model
        doc_tuples = self.nlp.pipe(text_tuples, as_tuples=True)
        
        # Initialize the list of documents
        docs = []
        
        # Iterate over each document and context
        for doc, context in doc_tuples:
            # Set the text_id attribute of the document
            doc._.text_id = context["text_id"]
            
            # Append the document to the list of documents
            docs.append(doc)

        # Iterate over each document
        for doc in docs:
            # Get the text ID from the document
            text_id = doc._.text_id
            
            # Process the sentences in the document
            spans = self.__text_processor.process_sentences(doc._.text_id, doc, storeTag, text_id)


            # Perform word sense disambiguation
           # wsd = self.__text_processor.perform_wsd(doc._.text_id)
            
            wsd = self.__text_processor.do_wsd(doc._.text_id)

            # Assign synset information to tokens
            #wn = self.__text_processor.assign_synset_info_to_tokens(doc._.text_id)
            wn_token_enricher = self.__text_processor.wn_token_enricher.assign_synset_info_to_tokens(text_id)
            # Process noun chunks
            noun_chunks = self.__text_processor.process_noun_chunks(doc, text_id)
            
            # Process entities
            nes = self.__text_processor.process_entities(doc, text_id)
            
            # Deduplicate named entities
            #deduplicate = self.__text_processor.deduplicate_named_entities(text_id)
            deduplicate = self.__text_processor.fuse_entities(text_id)
            
            # Perform coreference resolution
            #coref = self.__text_processor.do_coref2(doc, text_id)
            coref = self.__text_processor.coref.resolve_coreference(doc, text_id)


            # Build the entities inferred graph
            #self.__text_processor.build_entities_inferred_graph(text_id)
            self.__text_processor.disambiguate_entities(text_id)


            # Process SRL tags from spacy doc and store them into neo4j
            #self.__text_processor.process_srl(doc)
            self.__text_processor.srl_processor.process_srl(doc)

            # Optional: nominal SRL via the CogComp microservice. The call is a
            # no-op when `services.nom_srl_url` is unset (callNominalSrlApiBatch
            # returns [] of empty dicts in that case), so this block is safe to
            # leave in by default.
            try:
                from textgraphx.adapters.rest_caller import callNominalSrlApiBatch
                sents_list = list(doc.sents)
                nom_responses = callNominalSrlApiBatch([s.text for s in sents_list])
                nom_results = [
                    (sents_list[i].start, nom_responses[i])
                    for i in range(len(sents_list))
                    if nom_responses[i]
                ]
                if nom_results:
                    self.__text_processor.srl_processor.process_nominal_srl(
                        doc, nom_results,
                    )
            except Exception:  # pragma: no cover - service is advisory
                logger.exception("Nominal SRL pass failed; continuing without it")

            # Cross-framework frame fusion: create ALIGNS_WITH edges between
            # PROPBANK (verbal) and NOMBANK (nominal) frames that describe the
            # same predicate situation.  This is an advisory-tier enrichment;
            # failures must not abort the document.
            try:
                from textgraphx.adapters.srl_frame_aligner import (
                    run_cross_framework_alignment,
                )
                _graph = self.__text_processor.srl_processor.graph
                _aligned = run_cross_framework_alignment(_graph, text_id)
                if _aligned:
                    logger.debug(
                        "Cross-framework alignment: %d ALIGNS_WITH edges for doc %s",
                        _aligned, text_id,
                    )
            except Exception:  # pragma: no cover - advisory enrichment
                logger.exception(
                    "Cross-framework alignment failed for doc %s; continuing", text_id
                )
            # Define the rules for relationship extraction
            rules = [
                {
                    'type': 'RECEIVE_PRIZE',
                    'verbs': ['receive'],
                    'subjectTypes': ['PERSON', 'NP'],
                    'objectTypes': ['WORK_OF_ART']
                }
            ]
            
            # Extract relationships
            self.__text_processor.extract_relationships(text_id, rules)
            
            # Build the relationships inferred graph
            self.__text_processor.build_relationships_inferred_graph(text_id)







    def execute_cypher_query(self, query):
        try:
            # Connect to the database
            with self._driver.session() as session:
                # Run the Cypher query
                result = session.run(query)
                # Collect results
                records = [record.data() for record in result]
                return records
        except Exception as e:
            raise Exception(f"Error executing Cypher query: {e}")


def main() -> None:
    # Ensure logging is configured for CLI runs so users see console logs by default
    try:
        from textgraphx.infrastructure.logging_config import configure_logging
        configure_logging()
    except Exception:
        # If logging configuration fails, continue with the default logging setup
        import logging as _logging
        _logging.basicConfig(level=_logging.INFO)

    parser = argparse.ArgumentParser(prog="GraphBasedNLP", description="Run the Graph-based NLP pipeline")
    parser.add_argument('--dir', '-d', dest='directory',
                        default=str(Path(__file__).resolve().parent / 'datastore' / 'dataset'),
                        help='Path to datastore/dataset directory')
    parser.add_argument('--model', '-m', choices=['trf', 'sm', 'md'], default='trf',
                        help="Which spaCy model to load: 'trf' -> en_core_web_trf (default), 'sm' -> en_core_web_sm, 'md' -> en_core_web_md")
    parser.add_argument('--require-neo4j', dest='require_neo4j', action='store_true', default=False,
                        help='Fail fast if Neo4j is unreachable at startup')
    parser.add_argument('--neo4j-retries', dest='neo4j_retries', type=int, default=None,
                        help='Number of retries for Neo4j connectivity check (overrides NEO4J_CONNECT_RETRIES env var)')
    parser.add_argument('--neo4j-backoff', dest='neo4j_backoff', type=float, default=None,
                        help='Initial backoff seconds for Neo4j retries (exponential backoff multiplier)')
    # parse_known_args so we keep compatibility with GraphDBBase arg parsing (e.g., -b, -u, -p)
    args, unknown = parser.parse_known_args()

    model_map = {'trf': 'en_core_web_trf', 'sm': 'en_core_web_sm', 'md': 'en_core_web_md'}

    # Create a GraphBasedNLP object. Pass through any unknown args for GraphDBBase
    # Map CLI choices to model names
    model_name = model_map.get(args.model, 'en_core_web_trf')

    # If CLI provided explicit retries/backoff, set env vars so constructor picks them up
    if args.neo4j_retries is not None:
        os.environ['NEO4J_CONNECT_RETRIES'] = str(args.neo4j_retries)
    if args.neo4j_backoff is not None:
        os.environ['NEO4J_CONNECT_BACKOFF'] = str(args.neo4j_backoff)

    basic_nlp = GraphBasedNLP(unknown, model_name=model_name, require_neo4j=args.require_neo4j)

    # Store the corpus
    directory = args.directory
    text_tuples = basic_nlp.store_corpus(directory)

    # Tokenize and store the text tuples
    import time as _time
    _phase_start = _time.time()
    basic_nlp.process_text(text_tuples=text_tuples, text_id=1, storeTag=False)
    _phase_duration = _time.time() - _phase_start

    # Record an IngestionRun marker for restart visibility (Item 7)
    try:
        from textgraphx.pipeline.runtime.phase_assertions import record_phase_run
        from textgraphx.database.client import make_graph_from_config

        graph = make_graph_from_config()
        record_phase_run(
            graph,
            phase_name="ingestion",
            duration_seconds=_phase_duration,
            documents_processed=len(text_tuples) if text_tuples else 0,
        )
    except Exception:
        import logging as _log
        _log.getLogger(__name__).exception("Failed to write IngestionRun marker (non-fatal)")

    # Close the NLP object
    basic_nlp.close()


__all__ = ["GraphBasedNLP", "main"]


if __name__ == '__main__':
    main()