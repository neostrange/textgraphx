# SRL & Coreference Enhancement Plan

**Branch:** `feature/new-features-2026-05-01`
**Status:** Draft / awaiting approval
**Scope:** Full exploitation of (1) `transformer-srl` 2.4.6 verbal SRL on port 8010, (2) CogComp NomBank nominal SRL on port 8011, (3) confirmation of `spacy-experimental-coref` as the canonical coreference backend (maverick-coref discarded).

---

## 0. Executive Summary

Two new SRL services are wired into ingestion but **under-exploited and partially mis-configured**. Coreference policy must be formalized after the maverick-coref experiment. This plan sequences low-risk corrections (config / schema drift) before downstream graph-science exploitation (cross-framework frame fusion, sense-typed event subgraphs, GraphRAG-ready retrieval surfaces). Evaluation is layered: service-level → KG-level → MEANTIME end-to-end.

Guiding principle: **every new piece of evidence must be deterministic, span-grounded, confidence-tagged, and provenance-attributed** (textgraphx core invariant).

---

## 1. Multi-Dimensional Framing

### 1.1 Linguistic
- **Nominalization theory** (Chomsky 1970; Grimshaw 1990): nominal SRL recovers argument structure of *event nominals* ("destruction of the city by enemies"), bridging verbal and nominal predications of the same situation.
- **NP-external arguments**: NomBank annotates arguments outside the head NP (PPs, possessives, support-verb subjects). Our extractor must *not* assume head-internal spans.
- **Light verb / support verb constructions** ("make a decision", "give a talk"): verbal SRL underspecifies; nominal SRL provides the contentful predicate. Both must be aligned, not double-counted as separate events.
- **Control & raising**: PropBank handles long-distance subjects via implicit arguments; we should preserve these via `IS_DEPENDENT` traversal rather than inventing new edges.
- **Aspectual / temporal modifiers** (`ARGM-TMP`): on nominals these often surface as PPs ("attack on Tuesday") and are first-class anchors for the Temporal phase.

### 1.2 Computational Linguistic
- **Sense inventories**: PropBank rolesets (`attack.01`), NomBank rolesets, VerbNet classes, FrameNet frames. **SemLink** provides cross-walks. We will store native sense IDs and *defer* cross-resource projection to an enrichment pass.
- **Role-variant normalization**: `ARG1-PRD`, `C-ARG1` (continuation), `R-ARG1` (relative pronoun), `ARGM-*` modifiers. Eval scripts already normalize these; ingestion currently does **not**. Inconsistency causes false negatives in downstream argument matching.
- **Predicate disambiguation confidence**: transformer-srl returns `frame_score`; CogComp returns `sense_score`. Both should be persisted (already partial) and used for **gating**, not silent acceptance.
- **Cross-framework alignment**: the same situation may be expressed verbally and nominally in adjacent sentences. We must produce *one* canonical event with two `EventMention`s rather than two unconnected events.

### 1.3 Graph Data Science
- **Sense-typed subgraphs** enable targeted Cypher (e.g., `MATCH (f:Frame {framework:'PROPBANK', sense:'attack.01'})-[:PARTICIPANT]->(a)`). This is GraphRAG-ready retrieval.
- **Frame–Frame edges**: `ALIGNS_WITH` between PropBank and NomBank frames over the same situation supports community detection and event-cluster summarization.
- **Confidence-weighted edges**: `PARTICIPANT.confidence` drives weighted PageRank, GDS shortest-path, and probabilistic reasoning queries.
- **Densification risk**: nominal SRL roughly doubles `Frame` and `FrameArgument` counts. We need indices, dedup, and selective ingestion to avoid degrading query latency.

---

## 2. Current State (Verified)

| Area | State | Issue |
|------|-------|-------|
| `ServicesConfig.srl_url` | `http://localhost:8000/predict` | **Drift**: docs/migration claim 8010; legacy AllenNLP can be silently used |
| `ServicesConfig.nom_srl_url` | `""` (empty) | **Disabled by default**; nominal SRL silently no-ops |
| `SRLProcessor.process_nominal_srl` | Wired in `graph_based_nlp.py:417-425` | No batching; sentence-by-sentence calls |
| `Frame` ontology (`schema/ontology.json`) | `key_properties` lacks `framework`, `sense`, `sense_conf` | **Drift** vs `docs/schema.md:217` |
| Tests | 1 contract test parameterizes `framework`; **no** nominal write-path test | Coverage gap |
| Eval scripts | Service-level only (`scripts/evaluation/*`) | No KG-level / MEANTIME A/B harness |
| Coref | spacy-experimental-coref active; maverick-coref artifacts may linger | Policy not codified |
| Role normalization | Done in eval scripts only | Ingestion stores raw labels (`ARG1-PRD`, `C-ARG1`) |

---

## 3. Phased Implementation Plan

### Phase A — Correctness & Hygiene  *(P0, low risk, fast)*

1. **Config alignment**
   - `infrastructure/config.py`: change `srl_url` default to `http://localhost:8010/predict`.
   - Add `nom_srl_url = "http://localhost:8011/predict_nom"` as default; keep empty-string as the explicit "disabled" sentinel.
   - Update `config.example.toml` and `config.example.ini` with both keys, commented service expectations, and env-var names.
   - Add a startup probe (`adapters.rest_caller.health_check`) that logs `WARN` if the configured SRL URL responds with the legacy AllenNLP schema (heuristic: presence of `verbs[*].verb` but no `frame` field).

2. **Ontology / schema sync**
   - Update `schema/ontology.json` Frame node: add `framework`, `sense`, `sense_conf` to `optional_properties` (advisory tier — *not* `key_properties`, identity remains span+head-based).
   - Add migration `schema/migrations/00XX_frame_advisory_props.cypher` creating an index on `(:Frame {framework, sense})` for retrieval.
   - Cross-check `docs/schema.md` and `docs/ontology.yaml` for parity.

3. **Role-variant normalization at ingestion**
   - Add `adapters.semantic_role_labeler.normalize_role(label) -> (canonical, variant_flags)`.
   - Strip `C-`/`R-` prefixes into edge properties (`is_continuation`, `is_relative`); normalize `ARG1-PRD` → `ARG1` with `predicative=true`.
   - Store the original label as `raw_role` on the `PARTICIPANT` edge for provenance.

4. **Test coverage**
   - Add `tests/test_srl_nominal_writer.py`: mock `callNominalSrlApi`, assert `Frame{framework:'NOMBANK', sense:'attack.01'}` and `FrameArgument` edges with normalized roles + `sense_conf`.
   - Add contract test asserting role normalization preserves `raw_role`.

### Phase B — Confidence-Gated Ingestion  *(P1)*

1. **Gating policy** (advisory, configurable):
   - `ingestion.frame_confidence_min` (default 0.50): below → store frame but mark `provisional=true`; do not link in EventEnrichment.
   - `ingestion.argument_confidence_min` (default 0.40): below → drop argument (not stored); log to dropped-evidence audit.
2. Persist `dropped_arguments_count` in the phase completion marker for observability.
3. Surface `provisional` frame counts in the M2 mention-quality evaluator.

### Phase C — Cross-Framework Frame Fusion  *(P1)*

1. **Detection**: when verbal and nominal frames share lemma (or stem) within a coref chain, create `(:Frame)-[:ALIGNS_WITH {confidence}]->(:Frame)`.
2. **Canonicalization rule**: prefer the *higher-confidence* frame as the `INSTANTIATES` target for `EventMention`s in the cluster; the other becomes a *secondary* mention.
3. **Light-verb suppression**: detect `make/give/take/have + event-noun` patterns via dependency template (`dobj` head whose lemma is an event-nominal frame); demote the verbal frame to `LIGHT_VERB_HOST` and let the nominal carry the event.
4. **Determinism**: alignment key = `(min(frame_id), max(frame_id))` so repeated runs produce identical edges.

### Phase D — Downstream Phase Exploitation  *(P1–P2)*

| Phase | Enhancement |
|-------|-------------|
| **EventEnrichment** | Treat NomBank frames whose sense matches an event-nominal lexicon as `TEvent` candidates (in addition to verbal frames). |
| **Temporal** | Promote `ARGM-TMP` arguments (verbal + nominal) as TIMEX candidates *before* HeidelTime fallback; lifts recall on noun-anchored times. |
| **TLINK** | Allow nominal events as TLINK endpoints; require `frame_confidence ≥ gating threshold`. |
| **Refinement** | Use `ALIGNS_WITH` to merge mention clusters; reject coref-induced merges that contradict frame senses. |

### Phase E — Coreference Policy Codification  *(P1)*

1. **Backend selection**: `spacy-experimental-coref` is the **only** supported coref backend. maverick-coref is removed from defaults but a dormant adapter may remain behind a feature flag for future revisit.
2. **Code/config**:
   - `infrastructure/config.py`: `coref_backend = "spacy-experimental"`; remove maverick from defaults.
   - Delete or deprecate any `maverick_*` constants; add deprecation warning if env-var present.
3. **Documentation**: new `docs/COREF_POLICY.md` explaining tradeoffs (CPU cost, accuracy, mention-cluster shape), upgrade path criteria, and what would re-enable a heavier model.
4. **Hygiene**: search workspace for `maverick` references; archive old experiment scripts under `scripts/archive/`.

### Phase F — Throughput & Reliability  *(P2)*

1. **Batched nominal SRL**: replace per-sentence loop with a single multi-sentence POST (CogComp service supports list payloads). Fall back to per-sentence on 4xx.
2. **Async I/O**: convert SRL calls to `httpx.AsyncClient` inside ingestion when `services.async_io=true`.
3. **Sentence-hash cache**: SHA-256 of normalized sentence → cached SRL response; default size 5000, evictable via CLI.
4. **Timeouts and circuit breakers**: per-service breaker (5 consecutive failures → cool-down 30 s, log and continue without SRL evidence).

### Phase G — Multi-Tier Evaluation  *(P2)*

1. **Service-level (existing)**: keep `scripts/evaluation/evaluate_srl_services.py`; extend gold set toward 100 examples covering nominalization patterns (event nominals, partitives, support verbs, relational nouns).
2. **KG-level (new)**: `evaluation/srl_kg_quality.py` measuring:
   - Frame coverage / sentence
   - Argument density / event
   - Role-distribution KL-divergence vs MEANTIME
   - Confidence calibration (reliability diagram)
3. **MEANTIME end-to-end (new)**: `scripts/evaluation/run_srl_ab_matrix.py` running the full pipeline under four configurations:
   - V0: legacy AllenNLP, no nominal
   - V1: transformer-srl, no nominal
   - V2: transformer-srl + nominal (ungated)
   - V3: transformer-srl + nominal + confidence gating + cross-framework fusion
   Compare M2/M3/M5/M8 deltas; commit baseline JSON to `datastore/evaluation/baseline/srl_ab_matrix/`.

### Phase H — Documentation & Governance

1. **`.github/copilot-instructions.md`** additions (see §4).
2. **New docs**:
   - `docs/SRL_AND_COREF_ENHANCEMENT_PLAN.md` (this file).
   - `docs/COREF_POLICY.md`.
   - `docs/SRL_FRAMEWORKS.md` — PropBank vs NomBank inventories, role normalization rules, light-verb policy, SemLink roadmap.
3. **Updates**:
   - `docs/schema.md` — confirm Frame advisory props; add `ALIGNS_WITH` edge.
   - `docs/ontology.yaml` — same.
   - `docs/RUNNING_PIPELINE.md` — service ports table, health-check command, disable/enable flags.
   - `docs/architecture-overview.md` — SRL fan-out diagram including nominal path.
   - `CHANGELOG.md` — entries per merged sub-phase.
   - `DEPRECATION.md` — maverick-coref deprecation note.

---

## 4. `copilot-instructions.md` Additions (Proposed Diff)

Add a new subsection under **§5 Architectural Conventions** (or extend §3 Extraction Methodology):

```markdown
### 5.8 Semantic Role Labeling (SRL) Frameworks

textgraphx ingests evidence from two SRL frameworks. Both are first-class but
must be persisted with explicit framework attribution.

| Framework | Service | Port | Predicates | Sense field |
|-----------|---------|------|------------|-------------|
| PROPBANK  | transformer-srl 2.4.6 | 8010 | Verbal | `frame` (e.g., `attack.01`) |
| NOMBANK   | CogComp SRL-English   | 8011 | Nominal | `sense` (e.g., `attack.01`) |

Rules:
- Every `Frame` node MUST carry `framework ∈ {PROPBANK, NOMBANK}`. Default
  `PROPBANK` is allowed only for the verbal writer path.
- `sense` and `sense_conf` are advisory-tier properties; they are mandatory
  when the upstream service supplies them, otherwise omitted (never null).
- Argument labels are normalized at ingestion: `C-`/`R-` prefixes become edge
  properties (`is_continuation`, `is_relative`); `-PRD` becomes
  `predicative=true`. The raw label is preserved as `raw_role`.
- Verbal and nominal frames over the same situation are linked with
  `(:Frame)-[:ALIGNS_WITH]->(:Frame)`; the higher-confidence frame is the
  canonical `INSTANTIATES` target. Light-verb constructions demote the verbal
  frame to `LIGHT_VERB_HOST`.
- Confidence gating thresholds are declared in `infrastructure.config` and
  surfaced in phase completion markers.

### 5.9 Coreference Backend Policy

- Canonical backend: **spacy-experimental-coref**.
- maverick-coref is deprecated due to CPU cost; do not introduce new code
  paths that depend on it. See `docs/COREF_POLICY.md`.
- Coref edges (`REFERS_TO`) MUST carry `source='spacy-experimental-coref'`
  and a `cluster_id` deterministic across runs.
```

Add to **§10 Repository Hygiene → Do NOT commit** list:
- Maverick model checkpoints or any local heavy coref weights.

Add to the **port/service** table in **§2 Tech Stack** (or footnote): SRL 8010 / NomSRL 8011.

---

## 5. Ontology / Schema Patch (Sketch)

`schema/ontology.json` — Frame node:

```jsonc
{
  "label": "Frame",
  "key_properties": ["id", "headword", "headTokenIndex", "text", "startIndex", "endIndex"],
  "optional_properties": ["framework", "sense", "sense_conf", "provisional", "raw_role_count"],
  "edges_out": [
    {"type": "PARTICIPANT", "to": "FrameArgument"},
    {"type": "ALIGNS_WITH", "to": "Frame", "tier": "optional"}
  ]
}
```

Migration `schema/migrations/00XX_frame_advisory_props.cypher`:

```cypher
CREATE INDEX frame_framework_sense IF NOT EXISTS
FOR (f:Frame) ON (f.framework, f.sense);
```

---

## 6. Test Plan

| Test | Marker | Purpose |
|------|--------|---------|
| `test_srl_nominal_writer.py` | unit | Mock NomBank response → assert Frame/FrameArgument with framework=NOMBANK, sense, sense_conf |
| `test_srl_role_normalization.py` | unit | `C-ARG1` / `R-ARG0` / `ARG1-PRD` produce expected edge props |
| `test_srl_cross_framework_alignment.py` | integration | Two sentences (verbal + nominal) → one ALIGNS_WITH edge, deterministic key |
| `test_srl_confidence_gating.py` | unit | Thresholds drop / mark `provisional` correctly |
| `test_srl_config_health_check.py` | unit | Legacy schema response → warning logged |
| `test_coref_backend_policy.py` | contract | Maverick env-var triggers deprecation warning; backend resolves to spacy-experimental |
| `test_srl_kg_quality_baseline.py` | regression | Lock current frame coverage / argument density on a fixed corpus snippet |

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Nominal SRL service flaps / OOM | M | M | Circuit breaker + per-service breaker stats in completion marker |
| Frame densification slows queries | M | M | Index on `(framework, sense)`; cap arguments/frame; gating |
| Cross-framework dedup over-merges | M | H | Require coref-chain *and* lemma agreement; emit audit log |
| Role normalization hides upstream bugs | L | M | Always store `raw_role`; eval reports both raw and normalized |
| MEANTIME baselines shift due to nominal evidence | H (intended) | M | Rotate baselines per CONTRIBUTING evaluation policy; document expected delta direction |
| Coref policy regression if spacy-experimental ages out | L | H | `COREF_POLICY.md` declares re-evaluation criteria |

---

## 8. Sequencing & Acceptance Gates

| Sub-phase | Acceptance Gate |
|-----------|-----------------|
| A.1 Config | Health check + smoke test pass against both services |
| A.2 Ontology | Migration applies cleanly; contract tests green |
| A.3 Role norm | New unit tests green; existing 602-test suite still green |
| A.4 Tests | Coverage report shows nominal write path covered |
| B Gating | Phase marker contains gating stats; no contract-test regressions |
| C Fusion | Determinism test for ALIGNS_WITH passes across two runs |
| D Downstream | M2/M3/M5 do not regress vs current baseline |
| E Coref | All maverick references either removed or guarded; deprecation tests pass |
| F Throughput | p90 ingestion latency improves ≥ 30% on a 50-doc corpus |
| G Eval | A/B matrix JSON committed to baseline; MEANTIME deltas documented |
| H Docs | All linked from `DOCUMENTATION.md`; CHANGELOG updated; PR description references this plan |

---

## 9. Out of Scope (Explicitly Deferred)

- SemLink projection to VerbNet/FrameNet (logged for a future enrichment phase).
- LLM-based predicate disambiguation (T3 not justified while T2 confidences are usable).
- Maverick re-introduction (revisit only if spacy-experimental-coref recall drops below documented threshold).
- Multi-lingual SRL (current services are English-only; language gating remains the ingestion guard).

---

## 10. Open Questions for Reviewer

1. Should nominal SRL be **on by default** (Phase A) or behind a feature flag for one release window?
2. What is the acceptable maximum p95 ingestion latency increase from enabling nominal SRL on the MEANTIME corpus?
3. Confidence gating defaults: 0.50 / 0.40 — empirical or held until calibration plot from §G.2?
4. Do we want `ALIGNS_WITH` as a graph edge or as a derived view (Cypher pattern only)?
5. Coref `cluster_id` namespacing — per-document or globally hashed (cross-document coref candidate)?
