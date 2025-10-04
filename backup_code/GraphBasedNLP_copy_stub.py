"""
Stub replacement for the legacy `GraphBasedNLP copy.py` file. Imports of the
original copy caused package discovery to try to load optional LLM modules
that are not available in the trimmed runtime.

This file exists to make `import textgraphx` safe. Use
`textgraphx.GraphBasedNLP` (without "copy") for the canonical implementation.
"""

raise ImportError("Disabled duplicate module. Use 'textgraphx.GraphBasedNLP' instead.")
