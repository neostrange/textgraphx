<!-- last_reviewed: 2026-04-23 | owner: core | status: draft -->

# TextGraphX Encyclopedia / Miniwiki

> Research reference layer. Versioned with code. Page content lands progressively; this index is the scaffolding.

**Gateway** · **Wiki Home** · Index

## Purpose

The encyclopedia is the long-form counterpart to the operator-facing docs in [`../README.md`](../README.md):

- A navigable reference over the linguistic, ontological, and algorithmic foundations of the system.
- Every page cross-links to the code and schema it describes.
- Every page carries metadata (`last_reviewed`, `owner`, `status`) so staleness is visible.

## Sections (populated over subsequent PRs)

- `00-foundations/` — theme, rationale, glossary, concept map, origin-paper framing.
- `10-linguistics/` — syntax, semantics, SRL, coreference, NER/NEL, temporal semantics.
- `20-pipeline/` — pipeline theory and per-stage pages.
- `30-algorithms/` — algorithm cards (purpose, inputs, outputs, limits, references).
- `40-ontology-and-schema/` — ontology, schema tiers, reasoning contracts, span contract.
- `50-evaluation-science/` — what quality means, MEANTIME bridge, metrics, limitations.
- `55-evaluation-strategy/` — contract / phase / bridge / regression tiers and how-tos.
- `60-research/` — open questions, hypotheses, related work, paper-vs-current.
- `70-datasets/` — corpora, NAF, MEANTIME, TimeBank/TempEval, TTK, PropBank/FrameNet, WordNet, coref formats.
- `80-applications/` — LLM/GenAI, symbolic AI, context engineering, linguistics research, event-centric KGs.
- `99-references/` — consolidated citations and further reading.

## Reading paths

- **New engineer** → `00-foundations/theme-and-rationale.md` → `20-pipeline/pipeline-theory.md` → `20-pipeline/stage-ingestion.md`
- **Researcher** → `00-foundations/origin-paper.md` → `60-research/paper-vs-current.md` → `60-research/open-questions.md`
- **Evaluator** → `55-evaluation-strategy/strategy-overview.md` → `50-evaluation-science/meantime-bridge.md` → `55-evaluation-strategy/metrics-catalog.md`
- **Operator** → `../RUNNING_PIPELINE.md` → `20-pipeline/pipeline-theory.md` → `50-evaluation-science/known-limitations.md`
- **Dataset integrator** → `70-datasets/datasets-overview.md` → `70-datasets/newsreader-naf.md` → `70-datasets/gold-vs-system-alignment.md`

## Page template

New pages must copy [`_TEMPLATE.md`](_TEMPLATE.md) and include the standard sections and metadata header.

## Governance

- A PR that changes behavior in `src/textgraphx/*Phase*.py`, `schema/**`, or `ontology.json` must update at least one relevant wiki page (see [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)).
- The docs-hygiene CI check (added in a later PR) enforces metadata, link integrity, and the PR-touched-files rule.
