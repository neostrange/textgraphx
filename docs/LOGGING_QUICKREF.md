# Logging Quick Reference

## TL;DR - Just Want Detailed Logs?

### 1. Enable Debug Logging
```bash
export TEXTGRAPHX_LOG_LEVEL=DEBUG
```

### 2. Run Streamlit
```bash
cd "$(git rev-parse --show-toplevel)"
source .venv310/bin/activate
streamlit run textgraphx/app.py
```

### 3. Watch Logs in Real-Time
```bash
# In another terminal:
tail -f ~/.textgraphx_logs/*.log
```

---

## What You'll See

The system now logs **everything**:

```
[INFO] Initialized PipelineOrchestrator (ID: 550e8400-e29b-41d4-a716-446655440000)
[INFO] Execution ID: 550e8400-e29b-41d4-a716-446655440000
[INFO] Phases to execute: ingestion, refinement, temporal, event_enrichment, tlinks

============================================================
▶ INGESTION PHASE - GraphBasedNLP
============================================================

  ⟶ Importing GraphBasedNLP...
    ✓ Importing GraphBasedNLP (0.38s)
  
  ⟶ Processing directory: /dataset...
  Found 5 documents (XML: 3, TXT: 2)
    ✓ Processing directory (0.01s)
  
  [... more detailed operations ...]

✓ INGESTION PHASE - GraphBasedNLP completed in 11.53s
============================================================

  ⟶ Phase 2/5: REFINEMENT...
    [... 7 refinement steps with timing ...]
  ✓ Phase 2/5: REFINEMENT (0.87s)

  [... phases 3, 4, 5 ...]

============================================================
PIPELINE EXECUTION SUMMARY
============================================================
Execution ID: 550e8400-e29b-41d4-a716-446655440000
Total Duration: 18.53s
Phases Completed: 5/5
Documents Processed: 5
Status: SUCCESS
============================================================
```

---

## Log Files

All logs are saved to `~/.textgraphx_logs/`:

```bash
~/.textgraphx_logs/
├── orchestrator.log          # Pipeline orchestration
├── phase_wrappers.log        # Phase wrapper execution
├── graphbasednlp.log         # Ingestion phase details
├── refinement.log            # Refinement phase details
├── temporal.log              # Temporal phase details
├── enrichment.log            # Event enrichment details
└── tlinks.log                # TLINKS recognition details
```

---

## Commands to View Logs

```bash
# Real-time tail of all logs
tail -f ~/.textgraphx_logs/*.log

# View just orchestrator logs
tail -f ~/.textgraphx_logs/orchestrator.log

# Find all errors
grep ERROR ~/.textgraphx_logs/*.log

# Find warnings
grep WARNING ~/.textgraphx_logs/*.log

# Find slowest operations (> 1 second)
grep -E "[1-9]\d\.\d+s" ~/.textgraphx_logs/*.log

# Count log lines per level
cat ~/.textgraphx_logs/*.log | awk '{print $2}' | sort | uniq -c
```

---

## Configuration Options

### Environment Variables

```bash
# Set log level (DEBUG < INFO < WARNING < ERROR < CRITICAL)
export TEXTGRAPHX_LOG_LEVEL=DEBUG

# Use JSON output for log aggregation
export TEXTGRAPHX_LOG_JSON=1

# Fine-grained per-module levels
export TEXTGRAPHX_LOG_LEVELS="textgraphx.phase_wrappers=DEBUG,textgraphx.orchestration=INFO"
```

### Log File Location

Logs automatically save to `~/.textgraphx_logs/` by default.

To change:
```bash
export TEXTGRAPHX_LOG_FILE=/var/log/textgraphx/app.log
```

---

## Understanding Log Format

```
2026-04-03 15:30:42,123 [INFO    ] [textgraphx.orchestration:run_selected:120] Processing documents
                   ^            ^    ^                                      ^    ^
                timestamp       level module path:function:line  message
```

- **Timestamp**: When the event occurred
- **Level**: DEBUG / INFO / WARNING / ERROR / CRITICAL
- **Module**: Where the log came from (textgraphx.orchestration, etc.)
- **Function:Line**: Which function, which line number
- **Message**: What happened

---

## Troubleshooting with Logs

### "Phases are taking 0 seconds"
```bash
# Check if phases are actually running:
tail -f ~/.textgraphx_logs/*.log | grep "Importing"
# Should see: "Importing GraphBasedNLP", etc.

# If not appearing, check log level:
echo $TEXTGRAPHX_LOG_LEVEL
# Should be: INFO or DEBUG
```

### "My debug statements aren't showing"
```bash
# Ensure DEBUG level is enabled:
export TEXTGRAPHX_LOG_LEVEL=DEBUG

# Remove per-module overrides that might filter it:
unset TEXTGRAPHX_LOG_LEVELS
```

### "Logs aren't persisting to files"
```bash
# Check directory exists:
ls -la ~/.textgraphx_logs/

# If missing, create it:
mkdir -p ~/.textgraphx_logs
chmod 755 ~/.textgraphx_logs

# Restart the UI
```

---

## Example: Debugging a Phase Failure

**Scenario**: Temporal phase is failing

1. **Check the logs**:
   ```bash
   tail -100 ~/.textgraphx_logs/temporal.log
   ```

2. **Look for patterns**:
   ```
   ✗ Failed: TemporalPhase execution failed:  ...
   Error in temporal phase: No module named '...'
   ```

3. **Increase verbosity**:
   ```bash
   export TEXTGRAPHX_LOG_LEVELS="textgraphx.phase_wrappers.TemporalPhase=DEBUG"
   ```

4. **Rerun pipeline** - logs will now show all debug info including:
   - Function calls with arguments
   - Variable values at each step
   - Detailed error context

---

## For Developers

### Add Logging to Your Code

```python
from textgraphx.logging_utils import get_logger, log_section

logger = get_logger(__name__)

def my_function():
    with log_section(logger, "MY_OPERATION"):
        logger.info("Starting operation")
        logger.debug(f"Variable x = {x}")
        # your code here
        logger.info("Operation completed")
```

### Time Your Functions
```python
from textgraphx.logging_utils import timer_log

@timer_log("database_query")
def fetch_data():
    # automatically logs start, completion, and duration
    return results
```

### Track Progress
```python
from textgraphx.logging_utils import ProgressLogger

progress = ProgressLogger(logger, 100, "Processing")
for item in items:
    process(item)
    progress.update(message=f"Processed {item.id}")
progress.finish()
```

---

## Log Levels Explained

| Level | Use For | Example |
|-------|---------|---------|
| **DEBUG** | Detailed diagnostics, variable values, loop iterations | `logger.debug(f"x = {x}, y = {y}")` |
| **INFO** | Important operations, phase starts, completions | `logger.info("Processing started")` |
| **WARNING** | Unexpected conditions, missing optionals | `logger.warning("No documents found")` |
| **ERROR** | Failures that can be recovered | `logger.error("Connection failed, retrying")` |
| **CRITICAL** | System-breaking failures | `logger.critical("Cannot initialize DB")` |

---

## Real-World Example

```bash
# Run with maximum verbosity
export TEXTGRAPHX_LOG_LEVEL=DEBUG
export TEXTGRAPHX_LOG_JSON=0

# Launch UI
./.venv310/bin/streamlit run textgraphx/app.py

# In another terminal, watch logs
tail -f ~/.textgraphx_logs/orchestrator.log

# Upload files and run pipeline in UI...

# You'll see output like:
```

```
2026-04-03 15:30:42 [INFO    ] [textgraphx.app] Saving uploaded files to /dataset
2026-04-03 15:30:43 [DEBUG   ] [textgraphx.app] Saved: doc1.xml (2561 bytes)
2026-04-03 15:30:43 [DEBUG   ] [textgraphx.app] Saved: doc2.xml (3142 bytes)
2026-04-03 15:30:43 [INFO    ] [textgraphx.app] Successfully saved 2 files
2026-04-03 15:30:44 [INFO    ] [textgraphx.app] Running pipeline with phases: [ingestion, refinement]

============================================================
▶ PIPELINE EXECUTION - 2 phases
============================================================

2026-04-03 15:30:44 [INFO    ] [textgraphx.orchestration] Execution ID: 550e8400...
2026-04-03 15:30:44 [INFO    ] [textgraphx.orchestration] Phases to execute: ingestion, refinement

  ⟶ Phase 1/2: INGESTION...
2026-04-03 15:30:44 [INFO    ] [textgraphx.phase_wrappers] Initialized GraphBasedNLPWrapper
2026-04-03 15:30:44 [INFO    ] [textgraphx.phase_wrappers] Found 2 documents (XML: 2, TXT: 0)

  [11.53 seconds of detailed NLP processing...]

✓ Phase 1/2: INGESTION (11.53s)

  ⟶ Phase 2/2: REFINEMENT...

  [0.87 seconds of refinement...]

✓ Phase 2/2: REFINEMENT (0.87s)

============================================================
PIPELINE EXECUTION SUMMARY
============================================================
Total Duration: 12.40s
Phases Completed: 2/2
Documents Processed: 2
Status: SUCCESS
============================================================
```

---

## That's It!

You now have **complete visibility** into everything happening in your pipeline. The logs show:

✅ Every operation with timing  
✅ Phase transitions  
✅ Document processing  
✅ Errors and warnings  
✅ Performance metrics  
✅ Full execution flow  

All logged to files for later analysis!
