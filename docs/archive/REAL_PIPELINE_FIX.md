# TextGraphX Real Pipeline Execution Guide

## Problem Diagnosis

### Current State (Why phases take 0 seconds)
```
Streamlit UI (Python 3.13)
  ↓
Tries to import GraphBasedNLP
  ↓ 
ModuleNotFoundError: No module named '_ctypes'
  (from spacy → thinc → ctypes)
  ↓
Orchestrator catches ImportError, falls back to STUBS
  ↓
Results: 0 second execution, no Neo4j data ❌
```

### Solution: Switch to Python 3.10
Two environments available:
- `.venv` = Python 3.13 ❌ (missing _ctypes, can't import spacy)
- `.venv310` = Python 3.10 ✅ (has ctypes, can import spacy)

---

## Step 1: Update Streamlit to Use Python 3.10

### Option A: Direct command (easiest)
```bash
streamlit run textgraphx/app.py
```

### Option B: Update VS Code/scripts
Change any script that uses:
```bash
# OLD
.venv/bin/streamlit run textgraphx/app.py

# NEW  
.venv310/bin/streamlit run textgraphx/app.py
```

### Option C: Create launcher script
```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
./.venv310/bin/streamlit run textgraphx/app.py
```

---

## Step 2: Fix Import Paths in GraphBasedNLP.py

The file has mixed import styles that need standardization:

**Current inconsistent imports:**
```python
from util.SemanticRoleLabeler import SemanticRoleLabel  # ❌ relative
from textgraphx.util.GraphDbBase import GraphDBBase     # ✅ absolute
from textgraphx.TextProcessor import TextProcessor      # ✅ absolute
```

**Needs to become:**
```python
from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel    # ✅ absolute
from textgraphx.util.EntityFishingLinker import EntityFishing        # ✅ absolute
from textgraphx.util.GraphDbBase import GraphDBBase                  # ✅ absolute
from textgraphx.util.RestCaller import callAllenNlpApi               # ✅ absolute
from textgraphx.TextProcessor import TextProcessor                   # ✅ absolute
from textgraphx.TextProcessor import Neo4jRepository                 # ✅ absolute
```

### Fix Required Lines (GraphBasedNLP.py)
```python
# Line 12: Change
from util.SemanticRoleLabeler import SemanticRoleLabel
# To
from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel

# Line 13: Change
from util.EntityFishingLinker import EntityFishing
# To
from textgraphx.util.EntityFishingLinker import EntityFishing

# Line 16: Already correct
from textgraphx.util.GraphDbBase import GraphDBBase

# Line 17: Already correct
from textgraphx.TextProcessor import TextProcessor

# Line 15: Change
from util.RestCaller import callAllenNlpApi
# To
from textgraphx.util.RestCaller import callAllenNlpApi
```

---

## Step 3: Check Other Phase Components

Similarly check and fix import paths in:
- `RefinementPhase.py`
- `TemporalPhase.py`
- `EventEnrichmentPhase.py`
- `TlinksRecognizer.py`

Look for patterns like:
- `from util.` → change to `from textgraphx.util.`
- `from text_processing_components.` → change to `from textgraphx.text_processing_components.`

---

## Step 4: Test Real Imports

Once Python 3.10 is set and imports fixed:

```bash
cd "$(git rev-parse --show-toplevel)"
source .venv310/bin/activate

# Test imports
python3 -c "from textgraphx.GraphBasedNLP import GraphBasedNLP; print('✓ GraphBasedNLP OK')"
python3 -c "from textgraphx.RefinementPhase import RefinementPhase; print('✓ RefinementPhase OK')"
python3 -c "from textgraphx.TemporalPhase import TemporalPhase; print('✓ TemporalPhase OK')"
python3 -c "from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase; print('✓ EventEnrichmentPhase OK')"
python3 -c "from textgraphx.TlinksRecognizer import TlinksRecognizer; print('✓ TlinksRecognizer OK')"
```

---

## Step 5: Configure Neo4j (Optional)

Set connection credentials (if not using defaults `localhost:7687`):

### Via environment variables:
```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password
```

### Via config.ini (create if doesn't exist):
```ini
[neo4j]
uri = bolt://localhost:7687
username = neo4j
password = password
database = neo4j
```

---

## Step 6: Run the Real Pipeline

```bash
cd "$(git rev-parse --show-toplevel)"
./.venv310/bin/streamlit run textgraphx/app.py
```

Then:
1. Upload XML documents from `textgraphx/tarsqi-dataset/`
2. Select all 5 phases
3. Click "Run Pipeline"
4. **Expected results** (NO LONGER 0 seconds):
   - ✅ Ingestion: ~16s (document parsing + NLP)
   - ✅ Refinement: ~2s (deduplication)
   - ✅ Temporal: ~5s (temporal extraction)
   - ✅ Event Enrichment: ~0.23s (event enrichment)
   - ✅ TLINKs: ~0.6s (temporal link recognition)
   - **Total: ~24.8 seconds** ✓

---

## Step 7: Verify Neo4j Data

If Neo4j is running, query it to confirm data was stored:

```cypher
# Count all nodes
MATCH (n) RETURN COUNT(n) as node_count;

# Count by type
MATCH (n) RETURN DISTINCT labels(n) as type, COUNT(n) as count;

# See some entities
MATCH (e:Entity) RETURN e.name, labels(e) LIMIT 10;

# See relationships
MATCH (e:Entity)-[r]-(other) RETURN e.name, TYPE(r), other.name LIMIT 10;
```

---

## Troubleshooting

### Still getting ModuleNotFoundError after switching to Python 3.10

**Check**: Are ALL imports in GraphBasedNLP, RefinementPhase, etc. using `textgraphx.` prefix?

```bash
grep "^from util\." textgraphx/*.py
grep "^from text_processing" textgraphx/*.py
```

Fix any results with absolute imports.

### Neo4j connection fails

```python
# Test connection
from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()  # Should not raise
```

If it raises, check:
- Neo4j server is running: `neo4j start`
- Credentials in config.ini match your Neo4j installation
- No firewall blocking port 7687

### "Process directory" method not found

The real component classes may use different method names than orchestrator assumes. Check:

```bash
cd "$(git rev-parse --show-toplevel)"
./.venv310/bin/python3 -c "
from textgraphx.GraphBasedNLP import GraphBasedNLP
import inspect
print('Available methods:')
for name, method in inspect.getmembers(GraphBasedNLP, predicate=inspect.ismethod):
    if not name.startswith('_'):
        print(f'  - {name}')
"
```

Update `orchestrator.py` phase methods to call the correct method names.

---

## Quick Start (Single Command)

```bash
cd "$(git rev-parse --show-toplevel)" && \
sed -i 's/from util\./from textgraphx.util./g; s/from text_processing_components/from textgraphx.text_processing_components/g' textgraphx/GraphBasedNLP.py && \
./.venv310/bin/streamlit run textgraphx/app.py
```

This:
1. Fixes imports in GraphBasedNLP.py
2. Launches Streamlit with Python 3.10
3. Ready to run real pipeline

---

## Summary

| Issue | Solution |
|-------|----------|
| _ctypes missing | Use `.venv310` (Python 3.10 instead of 3.13) |
| Import errors | Add `textgraphx.` prefix to all relative imports |
| 0 second execution | Real components will execute with proper timing |
| No Neo4j data | Graph data will be stored when using real components |
| Fallback behavior | No more fallback to stubs, actual processing happens |
