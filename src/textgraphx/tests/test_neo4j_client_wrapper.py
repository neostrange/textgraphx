"""Compatibility tests for the root Neo4j client wrapper."""

import pytest

from textgraphx.database.client import (
    BoltGraphCompat as CanonicalBoltGraphCompat,
    get_config_section as canonical_get_config_section,
    make_bolt_driver_from_config as canonical_make_bolt_driver_from_config,
    make_graph_from_config as canonical_make_graph_from_config,
)
from textgraphx.neo4j_client import (
    BoltGraphCompat,
    get_config_section,
    make_bolt_driver_from_config,
    make_graph_from_config,
)


pytestmark = [pytest.mark.unit]


def test_root_neo4j_client_wrapper_reexports_canonical_symbols():
    assert BoltGraphCompat is CanonicalBoltGraphCompat
    assert get_config_section is canonical_get_config_section
    assert make_bolt_driver_from_config is canonical_make_bolt_driver_from_config
    assert make_graph_from_config is canonical_make_graph_from_config