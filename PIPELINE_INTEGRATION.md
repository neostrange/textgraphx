# TextGraphX Pipeline Integration Guide

## Overview

The orchestration layer now **integrates the actual Text-to-Knowledge Graph pipeline components** instead of stubs. Each phase calls the real implementation:

```
Streamlit UI (app.py)
        ↓
PipelineOrchestrator (orchestration/orchestrator.py)
        ↓
┌───────────────────────────────────────────────┐
│ Phase 1: Ingestion                            │
│ → GraphBasedNLP.py                            │
│ → Parses XML/TXT, extracts entities          │
│ → Stores in Neo4j                             │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│ Phase 2: Refinement                           │
│ → RefinementPhase.py                          │
│ → Cleans & normalizes extracted data         │
│ → Updates Neo4j graph                         │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│ Phase 3: Temporal                             │
│ → TemporalPhase.py                            │
│ → Identifies temporal entities & relations   │
│ → Adds temporal nodes to graph                │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│ Phase 4: Event Enrichment                     │
│ → EventEnrichmentPhase.py                    │
│ → Extracts & enriches events                 │
│ → Semantic enhancement                       │
└───────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────┐
│ Phase 5: TLINKs                               │
│ → TlinksRecognizer.py                         │
│ → Identifies temporal links between events   │
│ → Final graph completion                     │
└───────────────────────────────────────────────┘
        ↓
    Neo4j Knowledge Graph
```

## Real Components

### 1. **Ingestion Phase** - GraphBasedNLP
- **File**: `GraphBasedNLP.py`
- **What it does**:
  - Loads spaCy NLP model
  - Parses XML/TXT documents from dataset directory
  - Extracts entities, relations, dependencies
  - Performs Semantic Role Labeling (SRL)
  - Entity linking via external services
  - Stores graph data in Neo4j
- **Input**: XML/TXT files in dataset directory
- **Output**: Neo4j graph with initial entities and relations

### 2. **Refinement Phase** - RefinementPhase
- **File**: `RefinementPhase.py`
- **What it does**:
  - Cleans extracted entities
  - Normalizes data formats
  - Resolves duplicates
  - Validates relationships
  - Updates Neo4j graph
- **Input**: Initial Neo4j graph from Ingestion
- **Output**: Refined, deduplicated graph

### 3. **Temporal Phase** - TemporalPhase
- **File**: `TemporalPhase.py` 
- **What it does**:
  - Extracts temporal expressions
  - Identifies time anchors
  - Normalizes dates/times
  - Creates temporal nodes
  - Links events to temporal points
- **Input**: Refined graph + original documents
  - **Output**: Graph with temporal entities and links

### 4. **Event Enrichment Phase** - EventEnrichmentPhase
- **File**: `EventEnrichmentPhase.py`
- **What it does**:
  - Identifies events in sentences
  - Extracts event arguments
  - Enriches with semantic information
  - Links related events
  - Adds semantic properties
- **Input**: Graph with temporal information
- **Output**: Enriched event nodes and properties

### 5. **TLINKs Phase** - TlinksRecognizer
- **File**: `TlinksRecognizer.py`
- **What it does**:
  - Recognizes temporal links (TLINKs) between events
  - Classifies link types (BEFORE, AFTER, INCLUDES, etc.)
  - Creates typed relationships in graph
  - Validates temporal consistency
  - Completes the temporal knowledge graph
- **Input**: Graph with events and temporal info
- **Output**: Complete temporal knowledge graph with TLINKs

## Neo4j Connection

**File**: `neo4j_client.py`

The Neo4j client provides centralized connection management with configuration precedence:

1. `[py2neo]` section in `config.ini` (backward compatibility)
2. `[neo4j]` section in `config.ini`
3. Environment variables: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`

### Usage in Pipeline:

```python
from textgraphx.neo4j_client import make_graph_from_config

# Get Neo4j connection
graph = make_graph_from_config()

# Run queries
result = graph.run('MATCH (e:Entity) RETURN e').data()
```

## How to Run the Full Pipeline

### Via Streamlit UI (Recommended)

```bash
cd /home/neo/environments/textgraphx
./.venv/bin/streamlit run textgraphx/app.py
```

Then:
1. Upload XML/TXT files to dataset directory
2. Select all 5 phases
3. Click "Run Pipeline"
4. Monitor progress in real-time
5. View execution summary with actual processing times

### Via Orchestrator (Programmatic)

```python
from textgraphx.orchestration import PipelineOrchestrator

orchestrator = PipelineOrchestrator(
    directory="/path/to/dataset",
    model_name="en_core_web_trf"
)

# Run selected phases
orchestrator.run_selected([
    "ingestion",
    "refinement", 
    "temporal",
    "event_enrichment",
    "tlinks"
])

# Check results
summary = orchestrator.summary
print(f"Processed {summary.total_documents} documents")
print(f"Duration: {summary.total_duration:.2f}s")
```

## Expected Output

When running the real pipeline on actual documents:

```
📊 Execution Summary
Phases Completed: 5/5
Documents Processed: 15

✅ Ingestion - 16.12s
   - Extracted 342 entities
   - Created 1,247 relationships

✅ Refinement - 1.83s
   - Removed 23 duplicates
   - Normalized 156 keys

✅ Temporal - 4.98s
   - Extracted 87 temporal expressions
   - Created time anchors

✅ Event Enrichment - 0.23s
   - Identified 52 events
   - Enriched with semantics

✅ TLINKs - 0.62s
   - Recognized 34 temporal links
   - Graph complete
```

## Configuration

### config.ini

```ini
[neo4j]
uri = bolt://localhost:7687
username = neo4j
password = password

[nlp]
model = en_core_web_trf

[runtime]
naf_sentence_mode = auto
```

### Environment Variables

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
export TEXTGRAPHX_NAF_SENTENCE_MODE=auto
```

### Dataset-specific recommendation

- For MEANTIME NAF evaluation runs, set `TEXTGRAPHX_NAF_SENTENCE_MODE=meantime` to improve headline/date sentence boundaries.
- For unknown or mixed corpora, prefer `auto`.

## Testing the Integration

All 35 tests now validate the real component integration:

```bash
# Run tests
pytest tests/ -v

# Test specific phase
pytest tests/test_orchestration.py::TestPipelineOrchestrator -v
```

## Troubleshooting

### Phase Takes 0 Seconds

**Check**: Is the component actually being imported?

```python
from textgraphx.GraphBasedNLP import GraphBasedNLP
```

If this fails, the phase will fall back to stub mode.

### No Data in Neo4j

**Check**:
1. Is Neo4j running? `neo4j start`
2. Connection parameters in `config.ini` 
3. Dataset has files: `ls /path/to/dataset`
4. Check logs in `phase_<name>.log`

### Missing Dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_trf
```

## Next Steps

- ✅ Orchestration framework complete
- ✅ UI with phase selection working
- ✅ Execution history tracking
- ✅ Real component integration
- ⏳ Scale to larger datasets
- ⏳ Add API layer for programmatic access
- ⏳ Performance optimization for large graphs
