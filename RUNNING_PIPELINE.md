# Running the TextGraphX Pipeline

Two convenient ways to run the complete pipeline:

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
```

**Features:**
- Auto-creates/activates `.venv310` if missing
- Auto-installs dependencies and spaCy model
- Sets PYTHONPATH automatically
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

**"Virtual environment not found"**
- Run `./run.sh` once to auto-create and initialize `.venv310`

**"No module named textgraphx"**
- Ensure PYTHONPATH is set: `export PYTHONPATH=/home/neo/environments/textgraphx:$PYTHONPATH`

**"spaCy model not found"**
- Auto-installed by `./run.sh`
- Manual: `python -m spacy download en_core_web_sm`

**Neo4j connection errors**
- Verify Neo4j is running: `neo4j status`
- Check credentials in `config.ini`

## Example Full Run

```bash
# Complete pipeline on default dataset (~30 seconds)
./run.sh

# With progress output
./run.sh --dataset textgraphx/datastore/dataset
```

Expected output:
```
======================================================================
TextGraphX Pipeline Runner
Start time: 2026-04-03T14:45:00.123456
Dataset: /path/to/dataset
spaCy Model: en_core_web_sm
======================================================================
Running all phases in canonical order
...
======================================================================
Pipeline completed successfully
End time: 2026-04-03T14:45:32.654321
======================================================================
```

## Files

- `run.sh` - Bash wrapper script (environment + execution)
- `run_pipeline.py` - Python orchestrator entry point
- `textgraphx/PipelineOrchestrator.py` - Core pipeline logic
