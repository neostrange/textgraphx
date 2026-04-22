# Deprecation Schedule

This document lists deprecated APIs, their canonical replacements, and the
planned removal timeline.

---

## v2.0.0 Removals (scheduled)

The following methods emit `DeprecationWarning` at runtime as of the current
release.  They will be **removed** in v2.0.0.  Callers must migrate before
upgrading.

### `TemporalPhase` legacy methods

These methods were created when TLINK creation and `EventMention` materialization
were incorrectly owned by `TemporalPhase`.  Phase ownership has since been
corrected: TLINK creation belongs to `TlinksRecognizer` and `EventMention`
materialization belongs to `EventEnrichmentPhase`.

| Deprecated method | Canonical replacement | Module |
|-------------------|-----------------------|--------|
| `TemporalPhase.create_tevents2(doc_id)` | `TemporalPhase.materialize_tevents(doc_id)` | `TemporalPhase.py` |
| `TemporalPhase.create_timexes2(doc_id)` | `TemporalPhase.materialize_timexes(doc_id)` | `TemporalPhase.py` |
| `TemporalPhase.create_signals2(doc_id)` | `TemporalPhase.materialize_signals(doc_id)` | `TemporalPhase.py` |
| `TemporalPhase.create_tlinks_e2e(doc_id)` | `TlinksRecognizer.create_tlinks_e2e(doc_id)` | `TlinksRecognizer.py` |
| `TemporalPhase.create_tlinks_e2t(doc_id)` | `TlinksRecognizer.create_tlinks_e2t(doc_id)` | `TlinksRecognizer.py` |
| `TemporalPhase.create_event_mentions2(doc_id)` | `EventEnrichmentPhase.create_event_mentions(doc_id)` | `EventEnrichmentPhase.py` |

**Migration example – before:**

```python
from textgraphx.TemporalPhase import TemporalPhase

phase = TemporalPhase(cfg)
phase.create_tevents2(doc_id)
phase.create_timexes2(doc_id)
phase.create_signals2(doc_id)
phase.create_tlinks_e2e(doc_id)
phase.create_tlinks_e2t(doc_id)
phase.create_event_mentions2(doc_id)
```

**After:**

```python
from textgraphx.TemporalPhase import TemporalPhase
from textgraphx.TlinksRecognizer import TlinksRecognizer
from textgraphx.EventEnrichmentPhase import EventEnrichmentPhase

temporal = TemporalPhase(cfg)
temporal.materialize_tevents(doc_id)
temporal.materialize_timexes(doc_id)
temporal.materialize_signals(doc_id)

recognizer = TlinksRecognizer(cfg)
recognizer.create_tlinks_e2e(doc_id)
recognizer.create_tlinks_e2t(doc_id)

enrichment = EventEnrichmentPhase(cfg)
enrichment.create_event_mentions(doc_id)
```

Or, more concisely, use the canonical orchestrator which handles phase ordering
automatically:

```python
from textgraphx.orchestration.orchestrator import PipelineOrchestrator

orchestrator = PipelineOrchestrator(cfg)
orchestrator.run_for_review(doc_ids)
```

---

## Suppressing deprecation warnings during migration

Individual callers that cannot migrate immediately may suppress the warning
for a bounded scope:

```python
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    phase.create_tevents2(doc_id)
```

Do not suppress warnings globally — that hides other deprecation signals you
may care about.

---

## How to find deprecated callers

```bash
grep -rn \
    "create_tevents2\|create_timexes2\|create_signals2\|create_tlinks_e2e\|create_tlinks_e2t\|create_event_mentions2" \
    --include="*.py" \
    .
```

Exclude `tests/` and `temporal_legacy_compat.py` from the count; those are
expected callers during the migration window.

---

## Timeline

| Milestone | Action |
|-----------|--------|
| **v1.0.0** (current) | Deprecated methods emit `DeprecationWarning` at runtime |
| **v1.x** (next minor) | Deprecation warnings upgraded to `FutureWarning` in CI; any new caller in `main` will fail CI |
| **v2.0.0** | Deprecated methods removed; `temporal_legacy_compat.py` deleted |

The v2.0.0 target date is coordinated with the resolution of all outstanding
callers catalogued in `tests/test_item4_remediation_plan.py`.
