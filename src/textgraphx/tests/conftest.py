"""Pytest configuration and fixtures for textgraphx tests."""

import pytest
import socket
import sys
from pathlib import Path

# Add the parent directory to the path so we can import textgraphx modules
sys.path.insert(0, str(Path(__file__).parent.parent))


_NEO4J_AVAILABLE: bool | None = None


def _neo4j_is_reachable(host: str = "localhost", port: int = 7687, timeout: float = 0.5) -> bool:
    """Best-effort TCP probe for the Neo4j Bolt port. Cached per-session."""
    global _NEO4J_AVAILABLE
    if _NEO4J_AVAILABLE is not None:
        return _NEO4J_AVAILABLE
    try:
        with socket.create_connection((host, port), timeout=timeout):
            _NEO4J_AVAILABLE = True
    except (OSError, socket.timeout):
        _NEO4J_AVAILABLE = False
    return _NEO4J_AVAILABLE


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_neo4j: test requires a live Neo4j Bolt server at localhost:7687",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip ``requires_neo4j``-marked tests when Neo4j is unreachable."""
    if _neo4j_is_reachable():
        return
    skip_marker = pytest.mark.skip(reason="Neo4j Bolt server not reachable at localhost:7687")
    for item in items:
        if "requires_neo4j" in item.keywords:
            item.add_marker(skip_marker)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Convert Neo4j connection failures into skips when the server is unreachable.

    Many tests expect a live Neo4j Bolt server. Rather than tagging each file
    individually we treat ``ServiceUnavailable`` (and equivalent connection
    errors) raised during test execution as a skip when our session-cached probe
    confirms the server is unreachable.
    """
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    if _neo4j_is_reachable():
        return
    excinfo = call.excinfo
    if excinfo is None:
        return
    exc_repr = repr(excinfo.value)
    markers = (
        "ServiceUnavailable",
        "Couldn't connect to localhost:7687",
        "Connection refused",
        "ConnectionRefusedError",
    )
    if any(marker in exc_repr for marker in markers):
        report.outcome = "skipped"
        report.longrepr = (
            str(item.fspath),
            item.location[1] or 0,
            "Skipped: Neo4j Bolt server not reachable at localhost:7687",
        )


@pytest.fixture
def temp_dataset_dir(tmp_path):
    """Fixture providing a temporary dataset directory with sample files."""
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    
    # Create some sample files
    (dataset_dir / "test1.txt").write_text("Sample text document 1")
    (dataset_dir / "test2.txt").write_text("Sample text document 2")
    (dataset_dir / "test1.xml").write_text("<data>Sample XML document</data>")
    
    return dataset_dir


@pytest.fixture
def execution_history_db(tmp_path):
    """Fixture providing a temporary execution history database."""
    from textgraphx.orchestration import ExecutionHistory
    
    db_path = str(tmp_path / "history.json")
    history = ExecutionHistory(db_path)
    return history


@pytest.fixture
def pipeline_orchestrator(temp_dataset_dir):
    """Fixture providing a PipelineOrchestrator instance."""
    from textgraphx.orchestration import PipelineOrchestrator
    
    return PipelineOrchestrator(directory=str(temp_dataset_dir))


@pytest.fixture
def job_scheduler():
    """Fixture providing a JobScheduler instance."""
    from textgraphx.orchestration import JobScheduler
    
    return JobScheduler()
