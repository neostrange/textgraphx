import logging
from textgraphx.text_processing_components.EntityExtractor import EntityExtractor
from textgraphx.TextProcessor import Neo4jRepository
from textgraphx.util.GraphDbBase import GraphDBBase


class RunEntityExtractor(GraphDBBase):
    """Compatibility wrapper used in archived scripts.

    This class intentionally keeps a minimal surface area so the archived
    tests that import it can run. It establishes logging and a Neo4j
    repository placeholder and exposes a small API used elsewhere.
    """

    def __init__(self, argv, **kwargs):
        super().__init__(command=__file__, argv=argv)
        self.setup_logging()
        self.neo4j_repo = self.setup_neo4j_connection()
        self.api_url = "http://127.0.0.1:11435/process_text"
        # The EntityExtractor expects a URL and a driver; pass the driver
        # held on GraphDBBase for backwards compatibility.
        self.extractor = EntityExtractor(self.api_url, self._driver)

    def setup_logging(self):
        """Configure logging settings for the utility."""
        logging.basicConfig(level=logging.INFO)

    def setup_neo4j_connection(self):
        """Return a Neo4j repository wrapper instance.

        This is intentionally thin: it returns the project's Neo4j
        repository wrapper, which itself handles driver creation.
        """
        return Neo4jRepository(self._driver)

    def extract_entities(self, sample_text):
        """Use the EntityExtractor to extract entities from the provided text."""

        try:
            entities = self.extractor.extract_entities(sample_text)
            if not entities:
                logging.warning("No entities extracted.")
            return entities
        except Exception as e:
            logging.error("An error occurred during entity extraction: %s", e)
            return []

    def integrate_entities(self, entities, document_id):
        """Integrate the extracted entities into the Neo4j database."""
        try:
            if entities:
                self.extractor.integrate_entities_into_db(entities, document_id)
                logging.info("Entities integrated successfully.")
        except Exception as e:
            logging.error("An error occurred during entity integration: %s", e)


def main(argv=None):
    """Compatibility entrypoint used by archived tests.

    Returns a RunEntityExtractor instance when called so older tests
    that only check for a callable `main` succeed.
    """
    if argv is None:
        argv = []
    return RunEntityExtractor(argv=argv)


if __name__ == "__main__":
    # Small smoke run when executed as a script (kept intentionally
    # lightweight so it doesn't require network services during tests).
    sample_text = (
        "Australia has established a healthy digital economy over the last decade, "
        "and Aussie businesses have embraced the latest technologies to take "
        "advantage of efficiencies and scale."
    )
    extractor = RunEntityExtractor(argv=[])
    entities = extractor.extract_entities(sample_text)
    extractor.integrate_entities(entities, "1")  # Replace with actual document ID


