# Running the TextGraphX Pipeline

## Quick Start (Most Users)

```bash
# Check that everything is set up correctly
./run.sh --check

# Run the full pipeline
./run.sh
```

## Diagnostic Mode

Before running the pipeline, verify your setup:

```bash
# Run health checks without executing pipeline
python run_pipeline.py --check
# OR
./run.sh --check
```

This checks for:
- ✅ Python packages installed (spacy, neo4j)
- ✅ Dataset directory exists and is readable
- ✅ spaCy model available
- ✅ Neo4j database accessible

**Need help?** If checks fail, the output includes fixes:
```
✗ Neo4j not running on bolt://localhost:7687
  Fix: Start Neo4j server
```

## Option 1: Bash Wrapper (Simplest)

The `run.sh` script automatically handles environment setup and execution:

```bash
# Full pipeline with default dataset
./run.sh

# Full pipeline with custom dataset
./run.sh --dataset /path/to/dataset

# Run only specific phases
./run.sh --phases ingestion,refinement

# Run with different spaCy model
./run.sh --model en_core_web_trf

# Check setup before running
./run.sh --check
```

**Features:**
- Auto-creates/activates `.venv310` if missing
- Auto-installs dependencies and spaCy model
- Sets PYTHONPATH automatically
- Runs health checks before execution
- Deactivates venv when done

## Option 2: Direct Python Execution


```bash
# Activate venv310 (if not using run.sh)
source .venv310/bin/activate
export PYTHONPATH=/path/to/textgraphx:$PYTHONPATH

# Run with python directly
python run_pipeline.py
python run_pipeline.py --dataset textgraphx/datastore/dataset
python run_pipeline.py --phases temporal,event_enrichment
```

## Available Phases

Run any combination of these phases in order:
- `ingestion` - Load and parse documents into graph structure
- `refinement` - Refine named entities and relationships
- `temporal` - Extract and link temporal relations
- `event_enrichment` - Enrich events with semantic details
- `tlinks` - Create temporal links between events

## Environment Requirements

- Python 3.10+ (tested with 3.10.x)
- Neo4j database running on `localhost:7687`
- Credentials: neo4j / neo4j (default)

## Troubleshooting

### Clear Error Messages

The pipeline now provides actionable error messages:

```
❌ Error: Dataset directory not found
   Path: /nonexistent/path
   Hint: Use --dataset to specify a valid dataset directory
   Example: python run_pipeline.py --dataset datastore/dataset

💡 Run 'python run_pipeline.py --check' to diagnose issues.
```

### Common Issues

**"Dataset directory not found"**
- Check the dataset path is correct
- Use absolute path or relative path from where you're running
- Example: `./run.sh --dataset /home/user/data`

**"Neo4j not running on bolt://localhost:7687"**
- Start Neo4j: `neo4j start` or use Neo4j Desktop
- Verify it's running: `neo4j status`
- Check credentials in `config.ini`

**"spaCy model not found"**
- The `./run.sh` script auto-installs it
- Manual install: `python -m spacy download en_core_web_sm`

**"Virtual environment not found"**
- Run `./run.sh` once to auto-create `.venv310`
- Or manually: `python3.10 -m venv .venv310`

**"No module named textgraphx"**
- Ensure PYTHONPATH is set if running directly
- The `./run.sh` script handles this automatically

**Phase fails mid-execution**
- Pipeline logs show which step failed
- Check Neo4j is still running
- Review the detailed error message in logs
- Logs are printed to stdout/stderr

## Example Full Run

```bash
# Complete pipeline on default dataset (~30 seconds)
./run.sh

# With health check first
./run.sh --check && ./run.sh

# With progress output
./run.sh --dataset datastore/dataset
```

Expected output when health checks pass:
```
======================================================================
🚀 TextGraphX Pipeline Runner
======================================================================
Start time:  2026-04-03T14:45:00.123456
Dataset:     /path/to/dataset
spaCy Model: en_core_web_sm
======================================================================

Running all phases in canonical order:

...
======================================================================
✅ Pipeline completed successfully
End time: 2026-04-03T14:45:32.654321
======================================================================
```

## Implementation Details

### Health Checks (`health_check.py`)
Validates setup before execution:
- Neo4j database connectivity
- Dataset directory exists and is readable
- spaCy model availability
- Required Python packages installed

Use with `--check` flag to diagnose issues without running pipeline.

### Error Handling
Enhanced error messages provide:
- Clear error description
- Location/path information
- Specific fix suggestions
- Recovery hints

### Files

- `run.sh` - Bash wrapper (environment setup + execution)
- `run_pipeline.py` - Python orchestrator entry point with health checks
- `health_check.py` - Pre-flight validation module
- `PipelineOrchestrator.py` - Core pipeline logic with error context
- `RUNNING_PIPELINE.md` - This guide

## Files

- `run.sh` - Bash wrapper script (environment + execution)
- `run_pipeline.py` - Python orchestrator entry point
- `textgraphx/PipelineOrchestrator.py` - Core pipeline logic
