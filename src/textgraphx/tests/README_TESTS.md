# Testing Guide for textgraphx

This document explains how to run and write tests for the textgraphx pipeline.

## Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=textgraphx --cov-report=html --cov-report=term-missing
```

## Test Organization

Tests are organized in the `tests/` directory:

- **test_orchestration.py** - Tests for the orchestration modules
  - `TestExecutionHistory` - Database/storage tests
  - `TestPipelineOrchestrator` - Pipeline orchestration tests
  - `TestJobScheduler` - Job scheduling tests
  - `TestExecutionRecord` - Data structure tests
  - `TestExecutionStatistics` - Statistics calculation tests

- **test_ui.py** - Tests for the Streamlit UI application
  - `TestStreamlitApp` - UI component tests
  - `TestOrchestrationIntegration` - Integration tests
  - `TestErrorHandling` - Error handling tests
  - `TestDataClasses` - Data structure tests

## Running Specific Tests

### Run a specific test file
```bash
pytest tests/test_orchestration.py
```

### Run a specific test class
```bash
pytest tests/test_orchestration.py::TestExecutionHistory
```

### Run a specific test function
```bash
pytest tests/test_orchestration.py::TestExecutionHistory::test_init_creates_file
```

### Run tests matching a pattern
```bash
pytest -k "execution"
```

### Run tests with markers
```bash
pytest -m "unit"
pytest -m "integration"
pytest -m "orchestration"
```

## Test Markers

Tests are marked with the following markers for easier organization:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.ui` - UI tests
- `@pytest.mark.orchestration` - Orchestration tests

## Writing New Tests

### Basic Test Structure

```python
import pytest

class TestMyModule:
    """Tests for my_module."""
    
    def test_basic_functionality(self):
        """Test that basic functionality works."""
        # Setup
        obj = MyClass()
        
        # Action
        result = obj.do_something()
        
        # Assert
        assert result is not None
    
    def test_error_handling(self):
        """Test that errors are handled correctly."""
        with pytest.raises(ValueError):
            MyClass().invalid_operation()
```

### Using Fixtures

```python
def test_with_fixture(temp_dataset_dir):
    """Test using the temp_dataset_dir fixture."""
    # The fixture provides a temporary directory
    assert temp_dataset_dir.exists()
    
    # Use it in your test
    from orchestration import PipelineOrchestrator
    orchestrator = PipelineOrchestrator(directory=str(temp_dataset_dir))
```

## Test Utilities

### Available Fixtures

- `temp_dataset_dir` - Temporary dataset directory with sample files
- `execution_history_db` - Temporary execution history database
- `pipeline_orchestrator` - PipelineOrchestrator instance
- `job_scheduler` - JobScheduler instance

These are defined in `tests/conftest.py`.

## Coverage Report

After running `pytest --cov`, open the HTML coverage report:

```bash
# On Linux
xdg-open htmlcov/index.html

# On macOS
open htmlcov/index.html

# On Windows
start htmlcov/index.html
```

## Known Issues and Limitations

1. **Streamlit Testing**: The Streamlit UI tests use mocking since Streamlit's testing framework is still evolving. For more complete UI testing, consider using tools like Selenium.

2. **External Dependencies**: The orchestrator's phase execution functions are placeholders that don't call external NLP processes, avoiding dependency on spaCy models and ctypes.

3. **File System**: Tests use temporary directories provided by pytest to avoid side effects.

## Continuous Integration

For CI/CD pipelines, you can run:

```bash
# Run tests with verbose output and save results
pytest --verbose --junit-xml=test-results.xml --cov=textgraphx --cov-report=xml
```

## Debugging Tests

### Run with detailed output
```bash
pytest -vv
```

### Run with full tracebacks
```bash
pytest --tb=long
```

### Run and drop into debugger on failure
```bash
pytest --pdb
```

### Run and show print statements
```bash
pytest -s
```

## Performance Testing

For performance testing:

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run with timing
pytest --benchmark-only
```

## Test Best Practices

1. **One assertion per test** - Keep tests focused
2. **Clear test names** - Use descriptive names like `test_method_condition_result`
3. **Use fixtures** - Reduce setup code and improve readability
4. **Mock external dependencies** - Isolate the code under test
5. **Test edge cases** - Empty inputs, None values, large datasets
6. **Clean up** - Use fixtures with proper cleanup
