"""Compatibility alias for the canonical EntityFishing linker module."""

import sys

from textgraphx.adapters import entity_fishing as _canonical_entity_fishing


sys.modules[__name__] = _canonical_entity_fishing
