"""Pytest configuration and fixtures for textgraphx tests."""

import pytest
import sys
from pathlib import Path

# Add the parent directory to the path so we can import textgraphx modules
sys.path.insert(0, str(Path(__file__).parent.parent))


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
