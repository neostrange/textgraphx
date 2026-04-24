"""Compatibility alias for the canonical EntityFishing v2 linker module."""

import sys

from textgraphx.adapters import entity_fishing_v2 as _canonical_entity_fishing_v2


sys.modules[__name__] = _canonical_entity_fishing_v2
