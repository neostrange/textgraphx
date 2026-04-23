# Comprehensive Logging System for TextGraphX

## Overview

This document explains the detailed logging mechanism implemented throughout the textgraphx project. The logging system provides:

- **Structured logging** with timestamps, module names, function names, and line numbers
- **Hierarchical logging** with context managers for sections and subsections
- **Performance tracking** with decorators for timing and debug logging
- **Progress tracking** for long-running operations
- **Multiple outputs** - console (colored), file-based, and JSON formats
- **Configurable levels** per module for fine-grained control

---

## Quick Start

### Enable Detailed Logging

```bash
# Set environment variable for log level
export TEXTGRAPHX_LOG_LEVEL=DEBUG

# Run the pipeline
cd "$(git rev-parse --show-toplevel)"
source .venv310/bin/activate
./run.sh
```

### View Logs

**Console Output:**
```
2026-04-03 15:30:42 [INFO    ] [textgraphx.logging_utils:get_logger:25] Logger initialized
2026-04-03 15:30:43 [INFO    ] [textgraphx.orchestration.orchestrator:__init__:72] Initialized PipelineOrchestrator (ID: abc123...)
```

**Log Files:**
```bash
# Logs are stored in ~/.textgraphx_logs/
ls ~/.textgraphx_logs/

# View logs in real-time
tail -f ~/.textgraphx_logs/orchestrator.log
tail -f ~/.textgraphx_logs/graphbasednlp.log
tail -f ~/.textgraphx_logs/refinement.log
```

---

## Configuration

### Environment Variables

```bash
# Set the root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
export TEXTGRAPHX_LOG_LEVEL=INFO

# Use JSON format for logs (useful for log aggregation)
export TEXTGRAPHX_LOG_JSON=1

# Write logs to a file as well as console
export TEXTGRAPHX_LOG_FILE=/home/neo/.textgraphx_logs/app.log

# Set per-module log levels (comma-separated key=value pairs)
export TEXTGRAPHX_LOG_LEVELS="textgraphx.phase_wrappers=DEBUG,textgraphx.GraphBasedNLP=DEBUG"
```

### Config File

In `config.ini`:
```ini
[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
level = INFO

# Use JSON format (default: false)
json = false

# Optional: Write to file with automatic daily rotation
file = ~/.textgraphx_logs/app.log
```

---

## Logging Architecture

### Module Hierarchy

```
textgraphx
├── orchestration.orchestrator (pipeline coordination)
├── phase_wrappers (phase execution)
│   ├── phase_wrappers.GraphBasedNLP
│   ├── phase_wrappers.RefinementPhase
│   ├── phase_wrappers.TemporalPhase
│   ├── phase_wrappers.EventEnrichmentPhase
│   └── phase_wrappers.TlinksRecognizer
├── run_pipeline (CLI entrypoint)
├── GraphBasedNLP (actual ingestion component)
├── RefinementPhase (actual refinement component)
├── TextProcessor (utility processor)
└── logging_utils (logging infrastructure)
```

Each module logs to a dedicated file in `~/.textgraphx_logs/`:
- `orchestrator.log` - Pipeline orchestration
- `phase_wrappers.log` - Phase wrapper calls
- `graphbasednlp.log` - Ingestion phase
- `refinement.log` - Refinement phase
- `temporal.log` - Temporal phase
- `enrichment.log` - Event enrichment phase
- `tlinks.log` - TLINKS recognition phase

---

## Using the Logging Utilities

### 1. Getting a Logger

```python
from textgraphx.logging_utils import get_logger

logger = get_logger(__name__)

logger.info("Operation started")
logger.debug("Detailed debug message")
logger.warning("Something unexpected happened")
logger.error("An error occurred")
```

### 2. Context Managers for Sections

Log major sections of your code:

```python
from textgraphx.logging_utils import get_logger, log_section, log_subsection

logger = get_logger(__name__)

with log_section(logger, "DATABASE MIGRATION"):
    # Your code here - automatically logs timing
    migrate_schema()
    migrate_data()
    
# Output:
# ============================================================
# ▶ DATABASE MIGRATION
# ============================================================
# ⟶ Migrating schema...
#   ✓ Migrating schema (0.45s)
# ⟶ Migrating data...
#   ✓ Migrating data (1.23s)
# ✓ DATABASE MIGRATION completed in 1.68s
# ============================================================
```

### 3. Timing Operations

Automatically log execution time with decorator:

```python
from textgraphx.logging_utils import timer_log

@timer_log("document_processing")
def process_documents(docs):
    # Your code here
    return results

# Output:
# ▶ Starting: document_processing
# ✓ Completed: document_processing (0.45s)
```

### 4. Debug Logging with Arguments

```python
from textgraphx.logging_utils import debug_log

@debug_log("extracting entities")
def extract_entities(text, lang="en"):
    # Your code here
    return entities

# Output:
# 🔍 extracting entities → extract_entities('text...', lang='en')
# 🔙 extract_entities → dict
```

### 5. Progress Tracking

Track progress through a loop:

```python
from textgraphx.logging_utils import get_logger, ProgressLogger

logger = get_logger(__name__)
documents = [...]

progress = ProgressLogger(logger, len(documents), "Processing Documents")
for doc in documents:
    process(doc)
    progress.update(message=f"Processed {doc.id}")
progress.finish()

# Output:
# Processing Documents: 0/100 (0%)
# Processing Documents: 25/100 (25%)
# Processing Documents: 50/100 (50%)
# Processing Documents: 75/100 (75%)
# Processing Documents: 100/100 (100%)
```

---

## Log Output Examples

### Ingestion Phase

```
============================================================
▶ INGESTION PHASE - GraphBasedNLP
============================================================

  ⟶ Importing GraphBasedNLP...
    ✓ Importing GraphBasedNLP (0.38s)
  
  ⟶ Processing directory: src/textgraphx/datastore/dataset...
  Found 5 documents (XML: 3, TXT: 2)
    ✓ Processing directory: ... (0.01s)
  
  ⟶ Initializing GraphBasedNLP...
    ✓ Initializing GraphBasedNLP (2.45s)
  
  ⟶ Storing corpus and extracting text...
  Extracted 5 text tuples in 0.32s
    ✓ Storing corpus and extracting text (0.32s)
  
  ⟶ Processing extracted text with NLP...
  NLP Processing: 0/5 (0%)
      Processing 1/5: Extracting entities...
  NLP Processing: 20/5 (20%)
      Processing 2/5: Creating relationships...
  NLP Processing: 100/5 (100%)
    ✓ Processing extracted text with NLP (8.45s)
  
  ⟶ Storing results in Neo4j...
    ✓ Storing results in Neo4j (0.12s)

✓ INGESTION PHASE - GraphBasedNLP completed in 11.53s
============================================================
```

### Refinement Phase

```
============================================================
▶ REFINEMENT PHASE - Entity/Relation Cleaning
============================================================

  ⟶ Importing RefinementPhase...
    ✓ Importing RefinementPhase (0.28s)
  
  ⟶ Entity multitoken head assignment...
    ✓ Completed: Entity multitoken head assignment (0.15s)
  
  ⟶ Entity single-token head assignment...
    ✓ Completed: Entity single-token head assignment (0.09s)
  
  ⟶ Antecedent multitoken head assignment...
    ✓ Completed: Antecedent multitoken head assignment (0.12s)
  
  [... more refinement steps ...]

✓ REFINEMENT PHASE - Entity/Relation Cleaning completed in 0.87s
============================================================
```

### Pipeline Execution Summary

```
============================================================
PIPELINE EXECUTION - 5 phases
============================================================

Execution ID: 550e8400-e29b-41d4-a716-446655440000
Phases to execute: ingestion, refinement, temporal, event_enrichment, tlinks

  ⟶ Phase 1/5: INGESTION...
  ✓ Phase 1/5: INGESTION (11.53s)
  
  ⟶ Phase 2/5: REFINEMENT...
  ✓ Phase 2/5: REFINEMENT (0.87s)
  
  ⟶ Phase 3/5: TEMPORAL...
  ✓ Phase 3/5: TEMPORAL (5.23s)
  
  ⟶ Phase 4/5: EVENT_ENRICHMENT...
  ✓ Phase 4/5: EVENT_ENRICHMENT (0.28s)
  
  ⟶ Phase 5/5: TLINKS...
  ✓ Phase 5/5: TLINKS (0.62s)

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

## Log Levels and Their Uses

### DEBUG
- Variable values and state changes
- Function entry/exit
- Loop iterations and progress details
- Detailed operation steps

```python
logger.debug(f"Processing document {doc_id} with {lines} lines")
```

### INFO
- Operation start/completion
- Phase transitions
- Summary statistics
- Important milestones

```python
logger.info(f"Processed {count} documents in {duration:.2f}s")
```

### WARNING
- Unexpected conditions (operation continues)
- Deprecated usage
- Missing optional resources
- Performance issues

```python
logger.warning(f"No documents found in {directory}, skipping phase")
```

### ERROR
- Failed operations that can be recovered
- Exceptions caught and handled
- Validation failures

```python
logger.error(f"Failed to connect to Neo4j: {error}")
```

### CRITICAL
- System failures that prevent continuation
- Unrecoverable errors
- Should trigger immediate attention

```python
logger.critical(f"Cannot initialize database - system halting")
```

---

## Advanced Usage

### Per-Component Logging Setup

```python
from textgraphx.logging_utils import setup_component_logging

# Setup logger with automatic file output
logger = setup_component_logging("GraphBasedNLP", level="DEBUG")

logger.info("Component initialized")
logger.debug("Processing started")
```

### Exception Logging

```python
from textgraphx.logging_utils import get_logger, log_exception

logger = get_logger(__name__)

try:
    process_data()
except Exception as e:
    log_exception(logger, e, context="data processing")
    # Exception logged with full traceback
```

### Conditional Debug Logging

```python
logger = get_logger(__name__)

if logger.isEnabledFor(logging.DEBUG):
    # Expensive operations only if debug is enabled
    debug_info = expensive_debug_computation()
    logger.debug(f"Debug info: {debug_info}")
```

---

## Viewing Logs in Real-Time

### Tail Multiple Logs

```bash
# Watch all component logs
tail -f ~/.textgraphx_logs/*.log

# Watch specific phase logs
tail -f ~/.textgraphx_logs/graphbasednlp.log ~/.textgraphx_logs/refinement.log

# Filter for errors only
grep ERROR ~/.textgraphx_logs/*.log
```

### Search Logs

```bash
# Find all errors
grep ERROR ~/.textgraphx_logs/*.log

# Find operations taking over 1 second
grep -E "(\d\d\.\d+s|\d\d\d.\d+s)" ~/.textgraphx_logs/*.log

# Find a specific execution ID
grep "550e8400-e29b-41d4-a716-446655440000" ~/.textgraphx_logs/*.log
```

### Analyze Logs with Scripts

```bash
# Count log messages per level
cat ~/.textgraphx_logs/*.log | awk '{print $2}' | sort | uniq -c

# Find slowest operations
grep "✓ Completed" ~/.textgraphx_logs/*.log | sort -t'(' -k2 -r | head -10
```

---

## JSON Logging for Log Aggregation

Enable JSON format for structured log parsing:

```bash
export TEXTGRAPHX_LOG_JSON=1
```

Each log line becomes:
```json
{
  "ts": "2026-04-03 15:30:42,123",
  "level": "INFO",
  "module": "textgraphx.orchestration.orchestrator",
  "msg": "Initialized PipelineOrchestrator (ID: abc123...)"
}
```

Use with tools like Splunk, ELK Stack, or CloudWatch:
```bash
# Pipe to ELK stack
cat ~/.textgraphx_logs/*.log | jq . | curl -X POST -d @- http://elastic:9200/_bulk
```

---

## Troubleshooting

### Logs Not Appearing

**Check 1:**  Log level too high
```bash
# Current level is WARNING, try INFO
export TEXTGRAPHX_LOG_LEVEL=INFO
```

**Check 2:** Logger not initialized
```python
# Correct
from textgraphx.logging_utils import get_logger
logger = get_logger(__name__)

# Wrong
import logging
logger = logging.getLogger(__name__)
```

**Check 3:** Missing module in TEXTGRAPHX_LOG_LEVELS
```bash
# Too restrictive
export TEXTGRAPHX_LOG_LEVELS="textgraphx.orchestration=DEBUG"

# Solution - add other modules
export TEXTGRAPHX_LOG_LEVELS="textgraphx=DEBUG"
```

### Logs Not Persisting to File

```bash
# Check if directory exists and is writable
mkdir -p ~/.textgraphx_logs
chmod 755 ~/.textgraphx_logs

# Specify file explicitly
export TEXTGRAPHX_LOG_FILE=$HOME/.textgraphx_logs/app.log
```

---

## Summary

The logging system is designed to give you **complete visibility** into every operation happening in the textgraphx pipeline. Use it to:

- ✅ Track pipeline execution with precise timing
- ✅ Debug issues with detailed context and module information
- ✅ Monitor long-running operations with progress tracking
- ✅ Persist logs for post-mortem analysis
- ✅ Integrate with log aggregation services
- ✅ Control verbosity per module for targeted debugging

**Key Entry Points to Check Logs:**
1. `~/.textgraphx_logs/orchestrator.log` - Pipeline coordination
2. `~/.textgraphx_logs/graphbasednlp.log` - Document processing
3. `~/.textgraphx_logs/refinement.log` - Data cleaning
4. `~/.textgraphx_logs/temporal.log` - Temporal extraction
5. Console output - Real-time progress during execution
