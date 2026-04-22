"""Tests for the textgraphx pipeline orchestration modules."""

import pytest
import json
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from textgraphx.orchestration.db_interface import (
    ExecutionHistory,
    ExecutionRecord,
    ExecutionStatistics,
    ExecutionStatus,
)
from textgraphx.orchestration.orchestrator import (
    PipelineOrchestrator,
    JobScheduler,
    PhaseResult,
    PipelineSummary,
)


pytestmark = [pytest.mark.orchestration, pytest.mark.scenario]


class TestExecutionHistory:
    """Tests for ExecutionHistory storage module."""

    def test_init_creates_file(self):
        """Test that initialization creates the history file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            assert Path(db_path).exists()

    def test_record_execution(self):
        """Test recording an execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            
            history.record_execution(
                execution_id="test-1",
                status="success",
                total_duration=10.5,
                documents_processed=5,
                phases=["ingestion", "refinement"],
                started_at=datetime.now().isoformat(),
                completed_at=datetime.now().isoformat(),
            )
            
            records = history.get_latest(limit=1)
            assert len(records) == 1
            assert records[0].execution_id == "test-1"
            assert records[0].status == "success"

    def test_get_statistics_empty(self):
        """Test statistics on empty history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            
            stats = history.get_statistics()
            assert stats is None

    def test_get_statistics_with_data(self):
        """Test statistics calculation with data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            
            # Record multiple executions
            now = datetime.now()
            for i in range(3):
                status = "success" if i < 2 else "failed"
                history.record_execution(
                    execution_id=f"test-{i}",
                    status=status,
                    total_duration=10.0 + i,
                    documents_processed=5,
                    phases=["ingestion"],
                    started_at=(now - timedelta(hours=i)).isoformat(),
                )
            
            stats = history.get_statistics()
            assert stats is not None
            assert stats.total_runs == 3
            assert stats.successful_runs == 2
            assert stats.failed_runs == 1
            assert stats.avg_duration > 0

    def test_get_by_status(self):
        """Test filtering by status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            
            now = datetime.now()
            for i in range(3):
                status = "success" if i < 2 else "failed"
                history.record_execution(
                    execution_id=f"test-{i}",
                    status=status,
                    total_duration=10.0,
                    documents_processed=5,
                    phases=["ingestion"],
                    started_at=(now - timedelta(hours=i)).isoformat(),
                )
            
            success_records = history.get_by_status("success")
            assert len(success_records) == 2
            assert all(r.status == "success" for r in success_records)
            
            failed_records = history.get_by_status("failed")
            assert len(failed_records) == 1
            assert all(r.status == "failed" for r in failed_records)

    def test_get_latest_ordering(self):
        """Test that records are returned in correct order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            
            base_time = datetime.now()
            for i in range(5):
                history.record_execution(
                    execution_id=f"test-{i}",
                    status="success",
                    total_duration=10.0,
                    documents_processed=5,
                    phases=["ingestion"],
                    started_at=(base_time - timedelta(hours=i)).isoformat(),
                )
            
            records = history.get_latest(limit=3)
            assert len(records) == 3
            # Most recent should be first
            assert records[0].execution_id == "test-0"
            assert records[1].execution_id == "test-1"
            assert records[2].execution_id == "test-2"

    def test_delete_old_records(self):
        """Test deletion of old records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.json")
            history = ExecutionHistory(db_path)
            
            # Record old and new executions
            now = datetime.now()
            old_time = now - timedelta(days=35)
            recent_time = now - timedelta(days=5)
            
            history.record_execution(
                execution_id="old",
                status="success",
                total_duration=10.0,
                documents_processed=5,
                phases=["ingestion"],
                started_at=old_time.isoformat(),
            )
            
            history.record_execution(
                execution_id="recent",
                status="success",
                total_duration=10.0,
                documents_processed=5,
                phases=["ingestion"],
                started_at=recent_time.isoformat(),
            )
            
            deleted_count = history.delete_old_records(days=30)
            assert deleted_count == 1
            
            records = history.get_latest()
            assert len(records) == 1
            assert records[0].execution_id == "recent"


class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    def test_init(self):
        """Test orchestrator initialization."""
        orchestrator = PipelineOrchestrator(directory="test_dir")
        assert orchestrator.directory == Path("test_dir")
        assert orchestrator.model_name == "en_core_web_trf"
        assert orchestrator.execution_id is not None

    def test_init_with_custom_model(self):
        """Test orchestrator with custom model."""
        orchestrator = PipelineOrchestrator(model_name="en_core_web_trf")
        assert orchestrator.model_name == "en_core_web_trf"

    def test_run_selected_creates_summary(self):
        """Test that run_selected creates a proper summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = PipelineOrchestrator(directory=tmpdir)
            
            # Mock the phase runners to avoid external dependencies
            with patch.object(orchestrator, '_run_ingestion', return_value={'documents_processed': 5}):
                with patch.object(orchestrator, '_run_refinement', return_value={'documents_processed': 5}):
                    orchestrator.run_selected(['ingestion', 'refinement'])
            
            summary = orchestrator.summary
            assert summary.phase_count == 2
            assert summary.success_count == 2
            assert summary.failed_count == 0
            assert summary.total_duration > 0

    def test_run_selected_handles_failures(self):
        """Test that run_selected handles phase failures gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = PipelineOrchestrator(directory=tmpdir)
            
            # Mock one phase to fail
            with patch.object(orchestrator, '_run_ingestion', side_effect=ValueError("Test error")):
                with pytest.raises(ValueError):
                    orchestrator.run_selected(['ingestion'])
            
            summary = orchestrator.summary
            assert summary.failed_count == 1

    def test_run_selected_resume_from_checkpoint_skips_completed(self):
        """Resume mode should skip phases that already have checkpoints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = PipelineOrchestrator(directory=tmpdir)
            doc_id = orchestrator._checkpoint_doc_id()
            orchestrator.checkpoint_manager.save_checkpoint(doc_id, "ingestion")
            orchestrator.checkpoint_manager.save_checkpoint(doc_id, "refinement")

            with patch.object(orchestrator, '_run_temporal', return_value={'documents_processed': 1}):
                with patch.object(orchestrator, '_run_event_enrichment', return_value={'documents_processed': 1}):
                    with patch.object(orchestrator, '_run_tlinks', return_value={'documents_processed': 1}):
                        orchestrator.run_selected(
                            ['ingestion', 'refinement', 'temporal', 'event_enrichment', 'tlinks'],
                            resume_from_checkpoint=True,
                        )

            assert "ingestion" not in orchestrator.summary.phases
            assert "refinement" not in orchestrator.summary.phases
            assert orchestrator.summary.phase_count == 3
            assert orchestrator.summary.success_count == 3

    def test_run_selected_fails_on_phase_error_status(self):
        """Phases returning status=error must fail the run deterministically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = PipelineOrchestrator(directory=tmpdir)

            with patch.object(
                orchestrator,
                '_run_temporal',
                return_value={"status": "error", "message": "temporal backend unavailable"},
            ):
                with pytest.raises(RuntimeError, match="returned error status"):
                    orchestrator.run_selected(['temporal'])

    @pytest.mark.unit
    def test_strict_transition_gate_fails_on_assertions_in_testing_mode(self, tmp_path):
        fake_cfg = MagicMock()
        fake_cfg.runtime.mode = "testing"
        fake_cfg.runtime.strict_transition_gate = None

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            orchestrator = PipelineOrchestrator(directory=str(tmp_path))

        with patch.object(
            orchestrator,
            "_run_ingestion",
            return_value={"documents_processed": 1, "assertions_passed": False},
        ):
            with pytest.raises(RuntimeError, match="Strict transition gate failed"):
                orchestrator.run_selected(["ingestion"])

    @pytest.mark.unit
    def test_strict_transition_gate_not_enforced_in_production_mode(self, tmp_path):
        fake_cfg = MagicMock()
        fake_cfg.runtime.mode = "production"
        fake_cfg.runtime.strict_transition_gate = None

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            orchestrator = PipelineOrchestrator(directory=str(tmp_path))

        with patch.object(
            orchestrator,
            "_run_ingestion",
            return_value={"documents_processed": 1, "assertions_passed": False},
        ):
            orchestrator.run_selected(["ingestion"])

        assert orchestrator.summary.success_count == 1
        assert orchestrator.summary.failed_count == 0

    @pytest.mark.unit
    def test_strict_transition_gate_can_be_disabled_in_testing_mode(self, tmp_path):
        fake_cfg = MagicMock()
        fake_cfg.runtime.mode = "testing"
        fake_cfg.runtime.strict_transition_gate = False

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            orchestrator = PipelineOrchestrator(directory=str(tmp_path))

        with patch.object(
            orchestrator,
            "_run_ingestion",
            return_value={"documents_processed": 1, "assertions_passed": False},
        ):
            orchestrator.run_selected(["ingestion"])

        assert orchestrator.summary.success_count == 1
        assert orchestrator.summary.failed_count == 0

    @pytest.mark.unit
    def test_strict_transition_gate_can_be_enabled_in_production_mode(self, tmp_path):
        fake_cfg = MagicMock()
        fake_cfg.runtime.mode = "production"
        fake_cfg.runtime.strict_transition_gate = True

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            orchestrator = PipelineOrchestrator(directory=str(tmp_path))

        with patch.object(
            orchestrator,
            "_run_ingestion",
            return_value={"documents_processed": 1, "assertions_passed": False},
        ):
            with pytest.raises(RuntimeError, match="Strict transition gate failed"):
                orchestrator.run_selected(["ingestion"])

    @pytest.mark.unit
    def test_prepare_review_run_resets_db_in_testing_mode(self, tmp_path):
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        xml_path = dataset / "doc.xml"
        xml_path.write_text(
            """
            <NAF>
              <nafHeader>
                <fileDesc filename="doc.xml"/>
                <public publicId="doc-1" uri="urn:test:doc-1"/>
              </nafHeader>
              <raw>hello world</raw>
            </NAF>
            """.strip()
        )

        orchestrator = PipelineOrchestrator(directory=str(dataset))

        fake_graph = MagicMock()
        fake_graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"count": 1}])),
            MagicMock(data=MagicMock(return_value=[{"count": 1}])),
            MagicMock(data=MagicMock(return_value=[{"count": 42}])),
        ]

        with patch("textgraphx.orchestration.orchestrator.get_config") as get_config_mock:
            get_config_mock.return_value.runtime.mode = "testing"
            result = orchestrator.prepare_review_run(graph=fake_graph)

        assert result["already_processed"] is True
        assert result["database_cleared"] is True
        assert result["matched_documents"] == ["doc.xml"]
        assert result["existing_document_count"] == 1
        assert result["foreign_documents_present"] is False
        assert fake_graph.run.call_count == 3

    @pytest.mark.unit
    def test_prepare_review_run_blocks_reset_in_production_mode(self, tmp_path):
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        xml_path = dataset / "doc.xml"
        xml_path.write_text(
            """
            <NAF>
              <nafHeader>
                <fileDesc filename="doc.xml"/>
                <public publicId="doc-1" uri="urn:test:doc-1"/>
              </nafHeader>
              <raw>hello world</raw>
            </NAF>
            """.strip()
        )

        orchestrator = PipelineOrchestrator(directory=str(dataset))
        fake_graph = MagicMock()
        fake_graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"count": 1}])),
            MagicMock(data=MagicMock(return_value=[{"count": 1}])),
        ]

        with patch("textgraphx.orchestration.orchestrator.get_config") as get_config_mock:
            get_config_mock.return_value.runtime.mode = "production"
            with pytest.raises(RuntimeError, match="testing mode"):
                orchestrator.prepare_review_run(graph=fake_graph)

        assert fake_graph.run.call_count == 2

    @pytest.mark.unit
    def test_prepare_review_run_clears_foreign_docs_in_testing_mode(self, tmp_path):
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        xml_path = dataset / "doc.xml"
        xml_path.write_text(
            """
            <NAF>
              <nafHeader>
                <fileDesc filename="doc.xml"/>
                <public publicId="doc-1" uri="urn:test:doc-1"/>
              </nafHeader>
              <raw>hello world</raw>
            </NAF>
            """.strip()
        )

        orchestrator = PipelineOrchestrator(directory=str(dataset))
        fake_graph = MagicMock()
        fake_graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"count": 0}])),
            MagicMock(data=MagicMock(return_value=[{"count": 3}])),
            MagicMock(data=MagicMock(return_value=[{"count": 77}])),
        ]

        with patch("textgraphx.orchestration.orchestrator.get_config") as get_config_mock:
            get_config_mock.return_value.runtime.mode = "testing"
            result = orchestrator.prepare_review_run(graph=fake_graph)

        assert result["already_processed"] is False
        assert result["database_cleared"] is True
        assert result["foreign_documents_present"] is True
        assert result["existing_document_count"] == 3
        assert fake_graph.run.call_count == 3

    @pytest.mark.unit
    def test_prepare_review_run_blocks_foreign_docs_in_production_mode(self, tmp_path):
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        xml_path = dataset / "doc.xml"
        xml_path.write_text(
            """
            <NAF>
              <nafHeader>
                <fileDesc filename="doc.xml"/>
                <public publicId="doc-1" uri="urn:test:doc-1"/>
              </nafHeader>
              <raw>hello world</raw>
            </NAF>
            """.strip()
        )

        orchestrator = PipelineOrchestrator(directory=str(dataset))
        fake_graph = MagicMock()
        fake_graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"count": 0}])),
            MagicMock(data=MagicMock(return_value=[{"count": 2}])),
        ]

        with patch("textgraphx.orchestration.orchestrator.get_config") as get_config_mock:
            get_config_mock.return_value.runtime.mode = "production"
            with pytest.raises(RuntimeError, match="AnnotatedText nodes already exist"):
                orchestrator.prepare_review_run(graph=fake_graph)

        assert fake_graph.run.call_count == 2

    @pytest.mark.unit
    def test_run_for_review_skips_preparation_for_dbpedia_only(self, tmp_path):
        orchestrator = PipelineOrchestrator(directory=str(tmp_path))

        with patch.object(orchestrator, "prepare_review_run") as prepare_mock:
            with patch.object(orchestrator, "run_selected") as run_selected_mock:
                with patch.object(orchestrator, "validate_materialization_gate") as gate_mock:
                    result = orchestrator.run_for_review(phases=["dbpedia_enrichment"])

        prepare_mock.assert_not_called()
        gate_mock.assert_not_called()
        run_selected_mock.assert_called_once_with(["dbpedia_enrichment"])
        assert result["review_preparation_skipped"] is True
        assert result["materialization_gate"]["skipped"] is True
        assert result["materialization_gate"]["reason"] == "maintenance_only_phases"

    @pytest.mark.unit
    def test_run_for_review_keeps_review_path_for_ingestion(self, tmp_path):
        orchestrator = PipelineOrchestrator(directory=str(tmp_path))

        with patch.object(orchestrator, "prepare_review_run", return_value={"already_processed": False}) as prepare_mock:
            with patch.object(orchestrator, "run_selected") as run_selected_mock:
                with patch.object(orchestrator, "validate_materialization_gate", return_value={"passed": True}) as gate_mock:
                    result = orchestrator.run_for_review(phases=["ingestion"])

        prepare_mock.assert_called_once()
        gate_mock.assert_called_once()
        run_selected_mock.assert_called_once_with(["ingestion"])
        assert result["materialization_gate"]["passed"] is True

    @pytest.mark.unit
    def test_assess_review_run_safety_blocks_in_production_with_existing_docs(self, tmp_path):
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        (dataset / "doc.xml").write_text(
            """
            <NAF>
              <nafHeader>
                <fileDesc filename="doc.xml"/>
                <public publicId="doc-1" uri="urn:test:doc-1"/>
              </nafHeader>
              <raw>hello world</raw>
            </NAF>
            """.strip()
        )

        fake_cfg = MagicMock()
        fake_cfg.runtime.mode = "production"
        fake_cfg.runtime.strict_transition_gate = None
        fake_cfg.runtime.enable_cross_document_fusion = False
        fake_cfg.features.enable_dbpedia_enrichment = False

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            orchestrator = PipelineOrchestrator(directory=str(dataset))

        fake_graph = MagicMock()
        fake_graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"count": 0}])),
            MagicMock(data=MagicMock(return_value=[{"count": 2}])),
        ]

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            posture = orchestrator.assess_review_run_safety(graph=fake_graph)

        assert posture["would_block_run"] is True
        assert posture["would_clear_graph"] is False
        assert posture["reason"] == "existing_documents_in_non_testing_mode"

    @pytest.mark.unit
    def test_assess_review_run_safety_reports_clear_in_testing(self, tmp_path):
        dataset = tmp_path / "dataset"
        dataset.mkdir()
        (dataset / "doc.xml").write_text(
            """
            <NAF>
              <nafHeader>
                <fileDesc filename="doc.xml"/>
                <public publicId="doc-1" uri="urn:test:doc-1"/>
              </nafHeader>
              <raw>hello world</raw>
            </NAF>
            """.strip()
        )

        fake_cfg = MagicMock()
        fake_cfg.runtime.mode = "testing"
        fake_cfg.runtime.strict_transition_gate = None
        fake_cfg.runtime.enable_cross_document_fusion = True
        fake_cfg.features.enable_dbpedia_enrichment = False

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            orchestrator = PipelineOrchestrator(directory=str(dataset))

        fake_graph = MagicMock()
        fake_graph.run.side_effect = [
            MagicMock(data=MagicMock(return_value=[{"count": 1}])),
            MagicMock(data=MagicMock(return_value=[{"count": 3}])),
        ]

        with patch("textgraphx.orchestration.orchestrator.get_config", return_value=fake_cfg):
            posture = orchestrator.assess_review_run_safety(graph=fake_graph)

        assert posture["would_block_run"] is False
        assert posture["would_clear_graph"] is True
        assert posture["cross_document_fusion_enabled"] is True
        assert posture["reason"] == "testing_mode_requires_clean_graph"


class TestConfigRuntimeMode:
    @pytest.mark.unit
    def test_load_config_reads_runtime_mode(self, tmp_path):
        from textgraphx.config import load_config

        cfg_path = tmp_path / "config.ini"
        cfg_path.write_text(
            """
            [runtime]
            mode = testing
            """.strip()
        )

        cfg = load_config(str(cfg_path), allow_env=False)
        assert cfg.runtime.mode == "testing"

    @pytest.mark.unit
    def test_load_config_reads_runtime_strict_transition_gate_true(self, tmp_path):
        from textgraphx.config import load_config

        cfg_path = tmp_path / "config.ini"
        cfg_path.write_text(
            """
            [runtime]
            mode = testing
            strict_transition_gate = true
            """.strip()
        )

        cfg = load_config(str(cfg_path), allow_env=False)
        assert cfg.runtime.strict_transition_gate is True

    @pytest.mark.unit
    def test_load_config_reads_runtime_strict_transition_gate_auto(self, tmp_path):
        from textgraphx.config import load_config

        cfg_path = tmp_path / "config.ini"
        cfg_path.write_text(
            """
            [runtime]
            mode = testing
            strict_transition_gate = auto
            """.strip()
        )

        cfg = load_config(str(cfg_path), allow_env=False)
        assert cfg.runtime.strict_transition_gate is None

    @pytest.mark.unit
    def test_load_config_reads_runtime_naf_sentence_mode(self, tmp_path):
        from textgraphx.config import load_config

        cfg_path = tmp_path / "config.ini"
        cfg_path.write_text(
            """
            [runtime]
            mode = testing
            naf_sentence_mode = meantime
            """.strip()
        )

        cfg = load_config(str(cfg_path), allow_env=False)
        assert cfg.runtime.naf_sentence_mode == "meantime"

    @pytest.mark.unit
    def test_load_config_rejects_invalid_runtime_naf_sentence_mode(self, tmp_path):
        from textgraphx.config import load_config

        cfg_path = tmp_path / "config.ini"
        cfg_path.write_text(
            """
            [runtime]
            mode = testing
            naf_sentence_mode = unsupported_mode
            """.strip()
        )

        with pytest.raises(ValueError, match="naf_sentence_mode"):
            load_config(str(cfg_path), allow_env=False)


class TestPipelineMaterializationGate:
    @pytest.mark.unit
    def test_validate_materialization_raises_when_threshold_not_met(self):
        orchestrator = PipelineOrchestrator(directory="test_dir")

        fake_graph = MagicMock()

        def _run(query, params=None):
            mapping = {
                "MATCH (n:AnnotatedText) RETURN count(n) AS c": 1,
                "MATCH (n:TEvent) RETURN count(n) AS c": 0,
            }
            value = mapping.get(query, 0)
            return MagicMock(data=MagicMock(return_value=[{"c": value}]))

        fake_graph.run.side_effect = _run

        with pytest.raises(RuntimeError, match="Materialization gate failed"):
            orchestrator.validate_materialization_gate(
                graph=fake_graph,
                thresholds={
                    "MATCH (n:AnnotatedText) RETURN count(n) AS c": 1,
                    "MATCH (n:TEvent) RETURN count(n) AS c": 1,
                },
            )

    @pytest.mark.unit
    def test_validate_materialization_passes_when_thresholds_met(self):
        orchestrator = PipelineOrchestrator(directory="test_dir")

        fake_graph = MagicMock()
        fake_graph.run.return_value.data.return_value = [{"c": 2}]

        result = orchestrator.validate_materialization_gate(
            graph=fake_graph,
            thresholds={"MATCH (n:AnnotatedText) RETURN count(n) AS c": 1},
        )
        assert result["passed"] is True
        assert result["checks"][0]["actual"] == 2


class TestJobScheduler:
    """Tests for JobScheduler."""

    def test_init(self):
        """Test scheduler initialization."""
        scheduler = JobScheduler()
        assert scheduler.jobs == {}

    def test_schedule_interval_job(self):
        """Test scheduling an interval-based job."""
        scheduler = JobScheduler()
        
        success = scheduler.schedule_interval(
            job_id="job-1",
            dataset_path="/test/path",
            phases=["ingestion", "refinement"],
            hours=2,
        )
        
        assert success is True
        assert "job-1" in scheduler.jobs
        assert scheduler.jobs["job-1"]["type"] == "interval"
        assert scheduler.jobs["job-1"]["hours"] == 2

    def test_schedule_cron_job(self):
        """Test scheduling a cron-based job."""
        scheduler = JobScheduler()
        
        success = scheduler.schedule_cron(
            job_id="job-1",
            dataset_path="/test/path",
            phases=["ingestion"],
            cron_expression="0 0 * * *",
        )
        
        assert success is True
        assert "job-1" in scheduler.jobs
        assert scheduler.jobs["job-1"]["type"] == "cron"
        assert scheduler.jobs["job-1"]["cron_expression"] == "0 0 * * *"

    def test_list_jobs(self):
        """Test listing scheduled jobs."""
        scheduler = JobScheduler()
        
        scheduler.schedule_interval("job-1", "/path1", ["ingestion"], 2)
        scheduler.schedule_cron("job-2", "/path2", ["refinement"], "0 0 * * *")
        
        jobs = scheduler.list_jobs()
        assert len(jobs) == 2
        assert "job-1" in jobs
        assert "job-2" in jobs

    def test_cancel_job(self):
        """Test canceling a job."""
        scheduler = JobScheduler()
        
        scheduler.schedule_interval("job-1", "/path", ["ingestion"], 1)
        assert len(scheduler.jobs) == 1
        
        success = scheduler.cancel_job("job-1")
        assert success is True
        assert len(scheduler.jobs) == 0

    def test_cancel_nonexistent_job(self):
        """Test canceling a job that doesn't exist."""
        scheduler = JobScheduler()
        
        success = scheduler.cancel_job("nonexistent")
        assert success is False


class TestExecutionRecord:
    """Tests for ExecutionRecord dataclass."""

    def test_create_record(self):
        """Test creating an execution record."""
        now = datetime.now().isoformat()
        record = ExecutionRecord(
            execution_id="test-1",
            status="success",
            total_duration=10.5,
            documents_processed=5,
            phases="ingestion,refinement",
            started_at=now,
            completed_at=now,
        )
        
        assert record.execution_id == "test-1"
        assert record.status == "success"
        assert record.total_duration == 10.5
        assert record.documents_processed == 5

    def test_record_with_error(self):
        """Test creating a record with error message."""
        now = datetime.now().isoformat()
        record = ExecutionRecord(
            execution_id="test-1",
            status="failed",
            total_duration=5.0,
            documents_processed=0,
            phases="ingestion",
            started_at=now,
            error_message="Test error occurred",
        )
        
        assert record.status == "failed"
        assert record.error_message == "Test error occurred"


class TestExecutionStatistics:
    """Tests for ExecutionStatistics dataclass."""

    def test_create_statistics(self):
        """Test creating statistics object."""
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
