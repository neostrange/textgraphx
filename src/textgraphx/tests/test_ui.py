"""Tests for the textgraphx Streamlit UI application."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add the textgraphx module to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestStreamlitApp:
    """Tests for the Streamlit UI application."""

    @pytest.fixture
    def app_module(self):
        """Import the app module for testing."""
        # Mock streamlit before importing the app
        with patch('streamlit') as mock_st:
            # Set up mock streamlit functions
            mock_st.set_page_config = Mock()
            mock_st.title = Mock()
            mock_st.caption = Mock()
            mock_st.header = Mock()
            mock_st.subheader = Mock()
            mock_st.text_input = Mock(return_value="/test/path")
            mock_st.selectbox = Mock(return_value="en_core_web_sm")
            mock_st.checkbox = Mock(return_value=True)
            mock_st.button = Mock(return_value=False)
            mock_st.file_uploader = Mock(return_value=None)
            mock_st.metric = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock(), Mock(), Mock()])
            mock_st.empty = Mock()
            mock_st.progress = Mock()
            mock_st.divider = Mock()
            mock_st.sidebar = Mock()
            mock_st.success = Mock()
            mock_st.error = Mock()
            mock_st.warning = Mock()
            mock_st.info = Mock()
            mock_st.status = MagicMock()
            mock_st.exception = Mock()
            mock_st.dataframe = Mock()
            mock_st.write = Mock()
            mock_st.rerun = Mock()
            mock_st.tabs = Mock(return_value=[Mock(), Mock(), Mock()])
            
            sys.modules['streamlit'] = mock_st
            
            # Now import app
            from textgraphx import app
            yield app

    def test_app_imports(self):
        """Test that the app module imports successfully."""
        import sys
        from unittest.mock import MagicMock
        
        # Mock streamlit before import
        mock_st = MagicMock()
        sys.modules['streamlit'] = mock_st
        
        try:
            from textgraphx import app
            assert app is not None
        finally:
            # Clean up
            if 'streamlit' in sys.modules:
                del sys.modules['streamlit']

    def test_phase_options_defined(self):
        """Test that phase options are properly defined."""
        import sys
        from unittest.mock import MagicMock
        
        mock_st = MagicMock()
        sys.modules['streamlit'] = mock_st
        
        try:
            from textgraphx import app
            assert hasattr(app, 'PHASE_OPTIONS')
            assert len(app.PHASE_OPTIONS) == 5
            phase_names = [p[0] for p in app.PHASE_OPTIONS]
            assert "ingestion" in phase_names
            assert "refinement" in phase_names
            assert "temporal" in phase_names
            assert "event_enrichment" in phase_names
            assert "tlinks" in phase_names
        finally:
            if 'streamlit' in sys.modules:
                del sys.modules['streamlit']

    def test_save_uploaded_files(self):
        """Test the file upload saving function."""
        import sys
        from unittest.mock import MagicMock, Mock
        
        mock_st = MagicMock()
        sys.modules['streamlit'] = mock_st
        
        try:
            from textgraphx import app
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create mock file objects
                mock_file1 = Mock()
                mock_file1.name = "test1.txt"
                mock_file1.getbuffer.return_value = b"content1"
                
                mock_file2 = Mock()
                mock_file2.name = "test2.xml"
                mock_file2.getbuffer.return_value = b"<data>test</data>"
                
                uploaded_files = [mock_file1, mock_file2]
                
                # Call the save function
                saved_count = app.save_uploaded_files(uploaded_files, tmpdir)
                
                assert saved_count == 2
                assert (Path(tmpdir) / "test1.txt").exists()
                assert (Path(tmpdir) / "test2.xml").exists()
        finally:
            if 'streamlit' in sys.modules:
                del sys.modules['streamlit']

    def test_main_function_exists(self):
        """Test that the main function exists and is callable."""
        import sys
        from unittest.mock import MagicMock
        
        mock_st = MagicMock()
        sys.modules['streamlit'] = mock_st
        
        try:
            from textgraphx import app
            assert hasattr(app, 'main')
            assert callable(app.main)
        finally:
            if 'streamlit' in sys.modules:
                del sys.modules['streamlit']


class TestOrchestrationIntegration:
    """Integration tests with the orchestration modules."""

    def test_pipeline_orchestrator_can_be_imported(self):
        """Test that PipelineOrchestrator can be imported and initialized."""
        from textgraphx.orchestration import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator()
        assert orchestrator is not None
        assert orchestrator.execution_id is not None

    def test_execution_history_can_be_imported(self):
        """Test that ExecutionHistory can be imported."""
        from textgraphx.orchestration import ExecutionHistory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            history = ExecutionHistory(str(Path(tmpdir) / "history.json"))
            assert history is not None

    def test_job_scheduler_can_be_imported(self):
        """Test that JobScheduler can be imported and initialized."""
        from textgraphx.orchestration import JobScheduler
        
        scheduler = JobScheduler()
        assert scheduler is not None
        assert len(scheduler.list_jobs()) == 0

    def test_full_orchestration_workflow(self):
        """Test a complete orchestration workflow."""
        from textgraphx.orchestration import PipelineOrchestrator, ExecutionHistory, JobScheduler
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create orchestrator
            orchestrator = PipelineOrchestrator(directory=tmpdir)
            
            # Mock the phase runners
            with patch.object(orchestrator, '_run_ingestion', return_value={'documents_processed': 0}):
                orchestrator.run_selected(['ingestion'])
            
            # Check summary was created
            assert orchestrator.summary is not None
            assert orchestrator.summary.phase_count == 1
            
            # Create history and verify it can be initialized
            history = ExecutionHistory()
            stats = history.get_statistics()
            # Stats might be None if no records yet
            assert stats is None or hasattr(stats, 'total_runs')


class TestErrorHandling:
    """Tests for error handling in the UI and orchestration."""

    def test_orchestrator_handles_missing_directory(self):
        """Test that orchestrator handles missing directories gracefully."""
        from textgraphx.orchestration import PipelineOrchestrator
        
        orchestrator = PipelineOrchestrator(directory="/nonexistent/path")
        
        with patch.object(orchestrator, '_run_ingestion', return_value={'documents_processed': 0}):
            orchestrator.run_selected(['ingestion'])
        
        # Should not crash, should complete
        assert orchestrator.summary is not None

    def test_execution_history_handles_invalid_json(self):
        """Test that ExecutionHistory handles corrupted JSON."""
        from textgraphx.orchestration import ExecutionHistory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            
            # Create invalid JSON file
            Path(db_path).write_text("{invalid json")
            
            # Should handle gracefully
            history = ExecutionHistory(db_path)
            stats = history.get_statistics()
            assert stats is None  # Should return None for empty/corrupted data

    def test_job_scheduler_handles_duplicate_job_ids(self):
        """Test scheduler behavior with duplicate job IDs."""
        from textgraphx.orchestration import JobScheduler
        
        scheduler = JobScheduler()
        
        # Schedule first job
        scheduler.schedule_interval("job-1", "/path1", ["ingestion"], 1)
        jobs_after_first = len(scheduler.jobs)
        
        # Schedule job with same ID (should be overwritten)
        scheduler.schedule_interval("job-1", "/path2", ["refinement"], 2)
        jobs_after_second = len(scheduler.jobs)
        
        assert jobs_after_first == 1
        assert jobs_after_second == 1  # Should still be 1, not 2
        assert scheduler.jobs["job-1"]["dataset_dir"] == "/path2"


class TestDataClasses:
    """Tests for dataclass behavior."""

    def test_execution_record_dataclass(self):
        """Test ExecutionRecord dataclass."""
        from textgraphx.orchestration.db_interface import ExecutionRecord
        
        record = ExecutionRecord(
            execution_id="test",
            status="success",
            total_duration=10.0,
            documents_processed=5,
            phases="ingestion",
            started_at="2026-01-01T00:00:00",
        )
        
        assert record.execution_id == "test"
        assert record.status == "success"

    def test_execution_statistics_dataclass(self):
        """Test ExecutionStatistics dataclass."""
        from textgraphx.orchestration.db_interface import ExecutionStatistics
        
        stats = ExecutionStatistics(
            total_runs=10,
            successful_runs=8,
            failed_runs=2,
            avg_duration=15.5,
        )
        
        assert stats.total_runs == 10
        assert stats.successful_runs == 8
        assert stats.failed_runs == 2
        assert stats.avg_duration == 15.5

    def test_phase_result_dataclass(self):
        """Test PhaseResult dataclass."""
        from textgraphx.orchestration.orchestrator import PhaseResult
        
        result = PhaseResult(
            name="ingestion",
            status="completed",
            duration=10.5,
            documents_processed=5,
        )
        
        assert result.name == "ingestion"
        assert result.status == "completed"
        assert result.duration == 10.5

    def test_pipeline_summary_dataclass(self):
        """Test PipelineSummary dataclass."""
        from textgraphx.orchestration.orchestrator import PipelineSummary
        
        summary = PipelineSummary(
            execution_id="test-id",
            phase_count=2,
            success_count=2,
            failed_count=0,
            total_duration=20.0,
        )
        
        assert summary.execution_id == "test-id"
        assert summary.phase_count == 2
        assert summary.success_count == 2
        assert summary.failed_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
