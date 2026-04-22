# Comprehensive Logging Implementation - Summary

## What Was Implemented

A **detailed logging mechanism** has been added throughout the textgraphx project to provide complete visibility into all events and actions being performed.

---

## Key Features

### 1. **Structured Logging Utilities** (`textgraphx/logging_utils.py`)
New reusable logging utilities:
- `get_logger()` - Get configured loggers for any module
- `log_section()` - Context manager for major operations with visual formatting
- `log_subsection()` - Context manager for sub-operations
- `@timer_log()` - Decorator to automatically time functions
- `@debug_log()` - Decorator to log function calls with args/returns
- `ProgressLogger` - Track progress through loops with percentage updates
- `log_exception()` - Log exceptions with full context
- `setup_component_logging()` - Setup per-component logging with file output

### 2. **Phase Wrappers Enhanced** (`textgraphx/phase_wrappers.py`)
All 5 phase wrappers now include detailed logging:
- **GraphBasedNLPWrapper**
  - Logs model initialization
  - Logs file discovery (XML, TXT count)
  - Logs corpus extraction with timing
  - Logs NLP processing progress with per-document breakdown
  - Logs Neo4j storage results

- **RefinementPhaseWrapper**
  - Logs all 7 refinement steps with individual timing
  - Logs completion status per refinement operation

- **TemporalPhaseWrapper**
  - Logs document ID extraction
  - Logs 5 temporal operations per document
  - Progress tracking across all documents
  - Error handling with document context

- **EventEnrichmentPhaseWrapper**
  - Logs all 4 enrichment steps with timing
  - Individual step completion status

- **TlinksRecognizerWrapper**
  - Logs all 6 TLINK case patterns
  - Individual case timing and completion

### 3. **Orchestrator Enhanced** (`textgraphx/orchestration/orchestrator.py`)
Pipeline orchestration now includes:
- Initialization logging (execution ID, directory, model)
- Phase-by-phase execution with detailed timing
- Phase transition logging
- Overall pipeline summary with formatted output
- Error handling with detailed error context
- Progress tracking across all phases

**Example Output:**
```
============================================================
▶ PIPELINE EXECUTION - 5 phases
============================================================

Execution ID: 550e8400-e29b-41d4-a716-446655440000
Phases to execute: ingestion, refinement, temporal, event_enrichment, tlinks

  ⟶ Phase 1/5: INGESTION...
  ✓ Phase 1/5: INGESTION (11.53s)
  
  ⟶ Phase 2/5: REFINEMENT...
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

### 4. **Streamlit UI Enhanced** (`textgraphx/app.py`)
UI now logs:
- Component initialization
- Configuration settings
- File uploads with byte counts
- Phase selection
- Pipeline start/completion
- Execution results

### 5. **Log Files**
Logs are automatically saved to `~/.textgraphx_logs/` with daily rotation:
- `orchestrator.log` - Pipeline coordination
- `phase_wrappers.log` - Phase execution
- `graphbasednlp.log` - Ingestion details
- `refinement.log` - Refinement details
- `temporal.log` - Temporal details
- `enrichment.log` - Enrichment details
- `tlinks.log` - TLINKs details

### 6. **Documentation**
Two comprehensive guides created:
- **LOGGING_GUIDE.md** - Complete reference with examples and troubleshooting
- **LOGGING_QUICKREF.md** - Quick start and common commands

---

## How to Use

### Enable Detailed Logging
```bash
export TEXTGRAPHX_LOG_LEVEL=DEBUG
```

### Run Pipeline
```bash
cd "$(git rev-parse --show-toplevel)"
source .venv310/bin/activate
streamlit run textgraphx/app.py
```

### Watch Logs in Real-Time
```bash
# In another terminal:
tail -f ~/.textgraphx_logs/*.log
```

### View Specific Logs
```bash
# Orchestrator
tail -f ~/.textgraphx_logs/orchestrator.log

# Phase execution
tail -f ~/.textgraphx_logs/phase_wrappers.log

# All errors
grep ERROR ~/.textgraphx_logs/*.log
```

---

## What You'll See

### Console Output (Real-Time Progress)
✅ Phase progress with visual indicators  
✅ Timing for each operation  
✅ Success/failure indicators (✓/✗)  
✅ Overall execution summary  

### Log Files (Detailed Records)
✅ Timestamps with millisecond precision  
✅ Module name and line number  
✅ Function call tracking  
✅ Variable values at important points  
✅ Error messages with full context  
✅ Performance metrics  

---

## Configuration Options

### Environment Variables
```bash
# Log level
export TEXTGRAPHX_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Per-module control
export TEXTGRAPHX_LOG_LEVELS="textgraphx.phase_wrappers=DEBUG,textgraphx.orchestration=INFO"

# JSON format (for log aggregation)
export TEXTGRAPHX_LOG_JSON=1

# Custom log file location
export TEXTGRAPHX_LOG_FILE=/var/log/textgraphx/app.log
```

### Config File (`config.ini`)
```ini
[logging]
level = INFO
json = false
file = ~/.textgraphx_logs/app.log
```

---

## Examples of What Gets Logged

### Before (No Logging)
```
✅ Ingestion - 0.00s
✅ Refinement - 0.00s
```

### After (With Logging)
```
============================================================
▶ INGESTION PHASE - GraphBasedNLP
============================================================

  ⟶ Processing directory: /dataset...
  Found 5 documents (XML: 3, TXT: 2)
    ✓ Processing directory (0.01s)

  ⟶ Storing corpus and extracting text...
  Extracted 5 text tuples in 0.32s
    ✓ Storing corpus and extracting text (0.32s)

  ⟶ Processing extracted text with NLP...
  NLP Processing: 0/5 (0%)
  NLP Processing: 20/5 (20%)
  NLP Processing: 100/5 (100%)
    ✓ Processing extracted text with NLP (8.45s)

  ⟶ Storing results in Neo4j...
    ✓ Storing results in Neo4j (0.12s)

✓ INGESTION PHASE - GraphBasedNLP completed in 11.53s
============================================================
```

---

## Files Modified

| File | Changes |
|------|---------|
| `textgraphx/logging_utils.py` | **NEW** - Core logging utilities |
| `textgraphx/phase_wrappers.py` | Updated - Added detailed logging |
| `textgraphx/orchestration/orchestrator.py` | Updated - Enhanced orchestration logging |
| `textgraphx/app.py` | Updated - Added UI logging |
| `LOGGING_GUIDE.md` | **NEW** - Comprehensive guide |
| `LOGGING_QUICKREF.md` | **NEW** - Quick reference |

---

## Testing the Logging

```bash
# 1. Enable debug logging
export TEXTGRAPHX_LOG_LEVEL=DEBUG

# 2. Run UI
./.venv310/bin/streamlit run textgraphx/app.py

# 3. In another terminal, watch logs
tail -f ~/.textgraphx_logs/*.log

# 4. Upload sample documents via UI
# 5. Run pipeline
# 6. Observe detailed logs appearing in real-time!
```

---

## Benefits

✅ **Complete Visibility** - See every operation happening  
✅ **Performance Analysis** - Identify slow operations with timing  
✅ **Debugging** - Full context and call stack for errors  
✅ **Monitoring** - Track execution progress in real-time  
✅ **Auditing** - Persistent logs for compliance  
✅ **Integration** - JSON format for log aggregation systems  
✅ **Flexible** - Per-module log level control  

---

## Next Steps

1. **Enable Detailed Logging:**
   ```bash
   export TEXTGRAPHX_LOG_LEVEL=DEBUG
   ```

2. **Run Streamlit:**
   ```bash
   ./.venv310/bin/streamlit run textgraphx/app.py
   ```

3. **Watch Logs:**
   ```bash
   tail -f ~/.textgraphx_logs/*.log
   ```

4. **Upload Documents and Run Pipeline** via the UI

5. **Observe Detailed Logs** appearing in real-time with complete visibility into every action!

---

## Questions?

See:
- **LOGGING_GUIDE.md** - Complete reference with examples
- **LOGGING_QUICKREF.md** - Quick start commands
- `~/.textgraphx_logs/` - Your log files with all recorded events
