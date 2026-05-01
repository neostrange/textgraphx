"""Top-level package for textgraphx."""

__version__ = "0.1.0"

# Import canonical classes for convenience
# (Note: old root-level imports are deprecated; prefer explicit imports from pipeline/orchestration)
try:
    from textgraphx.pipeline.ingestion.graph_based_nlp import GraphBasedNLP
    from textgraphx.orchestration.orchestrator import PipelineOrchestrator
except ImportError:
    # If dependencies aren't available, these will be imported on-demand
    pass

__all__ = ["__version__", "GraphBasedNLP", "PipelineOrchestrator"]
