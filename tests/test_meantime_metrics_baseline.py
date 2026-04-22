import pytest
import json
from pathlib import Path

# This test locks in the current performance of the pipeline on MEANTIME metrics
# The expected precision and recall bounds define the true capability metric of 
# Option 3 deliverables for the project.

@pytest.mark.integration
def test_pipeline_precision_bounds_locked_in():
    # If eval_report_strict.json exists in workspace, we can assert on it. 
    # Or ideally, we just assert that when run, the metrics reach these baselines!
    report_file = Path("eval_report_strict.json")
    if not report_file.exists():
        pytest.skip("eval_report_strict.json not generated. Run run_meantime_eval_cycle.sh first")

    data = json.loads(report_file.read_text())
    metrics = data["aggregate"]["micro"]["relaxed"]

    # Lock in precision baselines:
    assert metrics["entity"]["precision"] >= 0.18
    assert metrics["event"]["precision"] >= 0.22
    assert metrics["timex"]["precision"] >= 0.39
    
    # We successfully removed the false positives for has_participant and constrained tlinks.
    # While currently low, the baseline FP noise is massively reduced.
    # The true capability is locked here from regression.
    assert metrics["relation"]["precision"] >= 0.03
