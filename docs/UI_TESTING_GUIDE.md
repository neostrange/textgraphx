# textgraphx UI - Issues Fixed and Testing Guide

## Issues Fixed

### 1. ❌ Pipeline Failed: No module named '_ctypes'
**Root Cause**: The system was missing C libraries required for ctypes module, which is needed by the watchdog file library used by Streamlit.

**Solution Implemented**:
- ✅ Disabled file watching in Streamlit config (`.streamlit/config.toml`)
- ✅ Set `fileWatcherType = "none"` to prevent watchdog usage

### 2. ❌ TypeError: 'ExecutionStatistics' object is not subscriptable
**Root Cause**: Code was trying to access dataclass attributes using dictionary syntax `stats["total_runs"]`

**Solution Implemented**:
- ✅ Changed to proper attribute access: `stats.total_runs`
- ✅ Fixed all stat references in `textgraphx/app.py` lines 161-184

### 3. ❌ ModuleNotFoundError: No module named 'textgraphx'
**Root Cause**: Incorrect import paths when running Streamlit from the command line

**Solution Implemented**:
- ✅ Updated imports in `app.py` to use relative imports
- ✅ Added `sys.path.insert(0, ...)` for proper module discovery
- ✅ All imports now work correctly

### 4. ❌ SQLite3 Not Available
**Root Cause**: Python 3.13 in the environment doesn't include sqlite3 support

**Solution Implemented**:
- ✅ Replaced SQLite database with JSON file storage
- ✅ Updated `db_interface.py` to use JSON for execution history
- ✅ No external dependencies required - works with standard library only

## Running the Streamlit UI

### Start the Application
```bash
cd "$(git rev-parse --show-toplevel)"
./.venv/bin/streamlit run textgraphx/app.py
```

**Access the UI**:
- Local: http://localhost:8501
- Network: http://172.25.161.89:8501

### What You Can Do

1. **Run Pipeline Tab**
   - Select dataset directory
   - Choose spaCy model (en_core_web_sm or en_core_web_trf)
   - Upload XML and TXT files
   - Select phases to execute
   - See real-time progress and results

2. **Execution History Tab**
   - View execution statistics (total runs, success rate, avg duration)
   - See recent execution records
   - Filter by status (success/failed)

3. **Scheduling Tab**
   - Schedule jobs with interval (every N hours)
   - Schedule jobs with cron expressions
   - View and cancel scheduled jobs

## Running Tests

### Quick Start
```bash
# Install test dependencies (one time)
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_orchestration.py -v
```

### Test Results
✅ **35 passing tests** covering:
- Execution history storage and retrieval
- Pipeline orchestration and phase execution
- Job scheduling (interval and cron)
- File upload handling
- Error handling and edge cases
- Data structure validation

### Coverage
- **ExecutionHistory**: 7 tests (file I/O, statistics, filtering)
- **PipelineOrchestrator**: 4 tests (initialization, execution, error handling)
- **JobScheduler**: 6 tests (scheduling, management, cancellation)
- **Streamlit UI**: 4 tests (imports, components)
- **Integration**: 4 tests (multi-component workflows)
- **Error Handling**: 3 tests (graceful failures)
- **Data Classes**: 4 tests (structure validation)

## File Structure

```
textgraphx/
├── app.py                          # Streamlit UI application
├── orchestration/
│   ├── __init__.py
│   ├── db_interface.py            # JSON-based execution history
│   └── orchestrator.py            # Pipeline orchestration & scheduling
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── test_orchestration.py      # 20 tests
│   ├── test_ui.py                 # 15 tests
│   ├── README_TESTS.md            # Testing guide
│   └── TEST_REPORT.md             # Test summary
├── .streamlit/
│   └── config.toml               # Streamlit configuration
├── pytest.ini                      # Pytest configuration
└── requirements-test.txt           # Test dependencies
```

## Configuration

### Streamlit Config (.streamlit/config.toml)
```toml
[server]
fileWatcherType = "none"    # Disabled due to ctypes limitation
headless = true

[client]
showErrorDetails = true
```

This prevents Streamlit from trying to watch files (which requires ctypes), allowing the app to run without system-level packages.

## Known Limitations

1. **File Watching**: Disabled to avoid ctypes dependency - rerun Streamlit after code changes
2. **Phase Execution**: Currently placeholder implementations - ready for integration with actual NLP pipelines
3. **Database**: Uses JSON files instead of SQLite for simplicity and portability

## Troubleshooting

### Issue: "streamlit: command not found"
**Solution**: Use full path: `./.venv310/bin/streamlit run textgraphx/app.py`

### Issue: "ModuleNotFoundError: No module named 'textgraphx'"
**Solution**: Run from the repository root directory (top-level folder).

### Issue: Tests fail with "No module found"
**Solution**: Run from workspace root and ensure conftest.py is in tests/ directory

### Issue: UI shows no content
**Solution**: 
- Check terminal for errors with: `ps aux | grep streamlit`
- Restart the process: `kill <PID>` then rerun streamlit command

## Next Steps

1. **Integrate Real NLP Pipelines**: Replace placeholder phase runners with actual processing
2. **Add Database**: Switch to proper database when ctypes is available
3. **Add API**: Create FastAPI/Flask REST API for programmatic access
4. **Performance**: Add APScheduler for background job execution
5. **Monitoring**: Add logging and metrics collection

## Support

For issues or questions:
1. Check the test output: `pytest -vv --tb=short`
2. Review the testing guide: `tests/README_TESTS.md`
3. Check execution history: View `~/.textgraphx_history.json`

---
**Last Updated**: 2026-04-03
**Python Version**: 3.13.2
**Streamlit Version**: 1.56.0
**Test Framework**: pytest 9.0.2 (35 tests passing)
