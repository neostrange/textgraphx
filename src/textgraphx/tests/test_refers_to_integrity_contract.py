"""Contract tests for REFERS_TO referential-integrity invariant.

Every mention (NamedEntity, EntityMention, NominalMention) that has a
REFERS_TO edge must point to a real canonical node (Entity / TEvent / TIMEX).
Orphan REFERS_TO edges break provenance lineage and MEANTIME evaluator matching.

Live Neo4j tests; auto-skipped when the server is unreachable.
"""
import pytest
from textgraphx.database.client import make_graph_from_config


@pytest.fixture(scope="module")
def graph():
    return make_graph_from_config()


@pytest.mark.integration
@pytest.mark.contract
def test_refers_to_target_exists(graph):
    """Every REFERS_TO edge must point to an Entity, TEvent, or TIMEX node."""
    query = """
        MATCH (m)-[r:REFERS_TO]->(target)
        WHERE NOT (target:Entity OR target:TEvent OR target:TIMEX)
        RETURN labels(m) AS mention_labels, labels(target) AS target_labels,
               m.id AS mention_id, target.id AS target_id
        LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], (
        f"REFERS_TO points to non-canonical targets: {rows}"
    )


@pytest.mark.integration
@pytest.mark.contract
def test_entity_id_is_not_raw_text(graph):
    """New disambiguator-produced Entity ids must never be raw surface text.

    This assertion is scoped to REFERS_TO edges created by the updated
    EntityDisambiguator path (edge source='entity_disambiguator') so legacy
    rows from pre-migration runs do not produce false failures.
    """
    query = """
        MATCH (:NamedEntity)-[r:REFERS_TO]->(e:Entity)
        WHERE r.source = 'entity_disambiguator'
          AND e.id IS NOT NULL
          AND NOT e.id STARTS WITH 'entity_'
        RETURN e.id AS raw_id, e.type AS type, r.provenance_rule_id AS provenance_rule_id
        LIMIT 10
    """
    rows = graph.run(query).data()
    assert rows == [], (
        f"EntityDisambiguator wrote non-canonical entity ids: {rows}"
    )


@pytest.mark.integration
@pytest.mark.contract
def test_entity_id_reproducibility__same_kb_id(graph):
    """Two Entity nodes with the same kb_id must have the same computed id.

    This guards against the case where make_entity_id is called inconsistently
    from different code paths.
    """
    query = """
        MATCH (e:Entity)
        WHERE e.kb_id IS NOT NULL
        WITH e.kb_id AS kb_id, collect(DISTINCT e.id) AS ids
        WHERE size(ids) > 1
        RETURN kb_id, ids
        LIMIT 5
    """
    rows = graph.run(query).data()
    assert rows == [], (
        f"Same kb_id mapped to multiple Entity.id values — "
        f"make_entity_id is being called inconsistently: {rows}"
    )
