import logging

logger = logging.getLogger(__name__)
logger.info("textgraphx.Utils module imported")


def create_constraints(driver):
    """Create standard constraints using the provided driver session.

    This helper centralizes the common constraint creation logic used in
    several scripts.
    """
    with driver.session() as session:
        session.run("CREATE CONSTRAINT ON (u:Tag) ASSERT (u.id) IS NODE KEY")
        session.run("CREATE CONSTRAINT ON (i:TagOccurrence) ASSERT (i.id) IS NODE KEY")
        session.run("CREATE CONSTRAINT ON (t:Sentence) ASSERT (t.id) IS NODE KEY")
        session.run("CREATE CONSTRAINT ON (l:AnnotatedText) ASSERT (l.id) IS NODE KEY")
        session.run("CREATE CONSTRAINT ON (l:NamedEntity) ASSERT (l.id) IS NODE KEY")
