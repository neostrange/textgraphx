# Deprecation Schedule

This document lists deprecated APIs, their canonical replacements, and the
planned removal timeline.

---

## Active Deprecations (current release)

### maverick-coref integration

| Item | Replacement |
|------|-------------|
| `MAVERICK_COREF_URL` env-var | Remove; use spacy-experimental-coref (no env-var needed) |
| `TEXTGRAPHX_MAVERICK_COREF_URL` env-var | Remove; same as above |

**Reason:** maverick-coref was evaluated and rejected due to CPU cost.
Setting either env-var triggers a `DeprecationWarning` at config load time.
See [docs/COREF_POLICY.md](docs/COREF_POLICY.md) for re-evaluation criteria.

**Removal target:** v1.1.0 — env-var detection code will be removed; any scripts
setting these vars will silently do nothing.

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

## Module-level shims at the package root

As part of the Phase 4 pipeline reorganization, six legacy module paths at
`textgraphx.<Name>` were replaced by canonical modules under
`textgraphx.pipeline.*`.  The legacy paths are retained as
backward-compatibility shims and are scheduled for **removal in v2.0.0**.

| Legacy import (deprecated) | Canonical replacement | Emits `DeprecationWarning` |
|----------------------------|-----------------------|----------------------------|
| `textgraphx.EventEnrichmentPhase` | `textgraphx.pipeline.phases.event_enrichment` | yes |
| `textgraphx.TemporalPhase` | `textgraphx.pipeline.phases.temporal` | yes |
| `textgraphx.TlinksRecognizer` | `textgraphx.pipeline.phases.tlinks_recognizer` | yes |
| `textgraphx.GraphBasedNLP` | `textgraphx.pipeline.ingestion.graph_based_nlp` | yes |
| `textgraphx.RefinementPhase` | `textgraphx.pipeline.phases.refinement` | yes |
| `textgraphx.TextProcessor` | `textgraphx.pipeline.ingestion.text_processor` | yes |

All in-tree callers have been migrated to the canonical paths; only legacy
external callers should encounter these warnings.

### Already-removed shims (history)

The following package-root utility shims were deleted in
commits `06373f8` and `ea58e4d` because they had no remaining callers:

`config`, `neo4j_client`, `phase_assertions`, `phase_wrappers`, `provenance`,
`run_report`, `text_normalization`, `time_utils`, plus 27 additional
shims dropped in the bulk-deletion pass.  Use the canonical subpackage
paths (`infrastructure.config`, `database.client`,
`pipeline.runtime.phase_assertions`, `pipeline.runtime.phase_wrappers`,
`reasoning.provenance`, `evaluation.reports`,
`pipeline.ingestion.text_normalization`, `reasoning.temporal.time`).

---

## Timeline

| Milestone | Action |
|-----------|--------|
| **v1.0.0** (current) | Deprecated methods and all 6 module-level shims emit `DeprecationWarning` at runtime |
| **v1.x** (next minor) | Deprecation warnings upgraded to `FutureWarning` in CI; any new caller in `main` will fail CI |
| **v2.0.0** | Deprecated methods removed; module-level shims removed; `temporal_legacy_compat.py` deleted |

The v2.0.0 target date is coordinated with the resolution of all outstanding
callers catalogued in `tests/test_item4_remediation_plan.py`.
