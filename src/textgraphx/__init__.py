# Generated from __inti__.py — preserved content
# __all__:any

# __all__==["util"]

__all__ = ["util"]
"""textgraphx package initializer.

This file makes the `textgraphx` directory a proper Python package so modules inside
can use relative imports (for example, `from .neo4j_client import ...`).
"""

__all__ = []

try:
	import importlib as _importlib

	_importlib.import_module("textgraphx.TextProcessor")
except Exception:
	# Optional preload only; tests can still import modules directly.
	pass
