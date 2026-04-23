<!-- last_reviewed: 2026-04-23 | owner: core | status: active -->

# TextGraphX — Documentation Gateway

Dense, link-only entry point. If you are not sure where to go, start here.

> **Origin note.** TextGraphX originated from Hur et al. (2024), *"Unifying context with labeled property graph: A pipeline-based system for comprehensive text representation in NLP"* (Expert Systems with Applications 239:122269, DOI [10.1016/j.eswa.2023.122269](https://doi.org/10.1016/j.eswa.2023.122269)). The current system substantially extends and supersedes that proposal. The paper is treated as origin/motivation, not as a specification. A dedicated "then vs now" page lands at `docs/wiki/00-foundations/origin-paper.md` in PR-3.

## Reading paths

- **New engineer** → [README.md](README.md) → [docs/architecture-overview.md](docs/architecture-overview.md) → [docs/RUNNING_PIPELINE.md](docs/RUNNING_PIPELINE.md)
- **Operator** → [docs/RUNNING_PIPELINE.md](docs/RUNNING_PIPELINE.md) → [docs/PRODUCTION_VALIDATION.md](docs/PRODUCTION_VALIDATION.md) → [docs/LOGGING_GUIDE.md](docs/LOGGING_GUIDE.md)
- **Evaluator** → [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md) → [docs/EVALUATION_ROADMAP_M1_TO_M10.md](docs/EVALUATION_ROADMAP_M1_TO_M10.md) → [docs/MILESTONE8_BRIDGE_VALIDATOR.md](docs/MILESTONE8_BRIDGE_VALIDATOR.md)
- **Researcher** → [docs/wiki/README.md](docs/wiki/README.md) (encyclopedia; scaffolds in PR-2)
- **Contributor** → [CONTRIBUTING.md](CONTRIBUTING.md) → [docs/schema.md](docs/schema.md) → [docs/schema-evolution-plan.md](docs/schema-evolution-plan.md)

## Operate

- [docs/RUNNING_PIPELINE.md](docs/RUNNING_PIPELINE.md)
- [docs/PRODUCTION_VALIDATION.md](docs/PRODUCTION_VALIDATION.md)
- [docs/PIPELINE_INTEGRATION.md](docs/PIPELINE_INTEGRATION.md)
- [docs/LOGGING_GUIDE.md](docs/LOGGING_GUIDE.md) · [docs/LOGGING_QUICKREF.md](docs/LOGGING_QUICKREF.md)

## Architecture & Schema

- [docs/architecture-overview.md](docs/architecture-overview.md)
- [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)
- [docs/schema.md](docs/schema.md) · [docs/schema-evolution-plan.md](docs/schema-evolution-plan.md)
- [docs/SCHEMA_REDESIGN_FOR_MEANTIME_PARITY.md](docs/SCHEMA_REDESIGN_FOR_MEANTIME_PARITY.md)
- Machine-readable ontology: [src/textgraphx/schema/ontology.json](src/textgraphx/schema/ontology.json)

## Evaluate

- [docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md](docs/COMPREHENSIVE_EVALUATION_FRAMEWORK.md)
- [docs/EVALUATION_ROADMAP_M1_TO_M10.md](docs/EVALUATION_ROADMAP_M1_TO_M10.md)
- [docs/MILESTONE1_UNIFIED_EVALUATION_SCHEMA.md](docs/MILESTONE1_UNIFIED_EVALUATION_SCHEMA.md)
- [docs/MILESTONES_2_7_PHASE_EVALUATORS.md](docs/MILESTONES_2_7_PHASE_EVALUATORS.md)
- [docs/MILESTONE8_BRIDGE_VALIDATOR.md](docs/MILESTONE8_BRIDGE_VALIDATOR.md)
- [docs/EVALUATION_DIAGNOSTICS.md](docs/EVALUATION_DIAGNOSTICS.md)
- [docs/MEANTIME_GAP_ANALYSIS.md](docs/MEANTIME_GAP_ANALYSIS.md)
- [docs/EVALUATION_ARTIFACT_RETENTION_POLICY.md](docs/EVALUATION_ARTIFACT_RETENTION_POLICY.md)

## Governance

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/PROVENANCE_AUTHORITY_POLICY.md](docs/PROVENANCE_AUTHORITY_POLICY.md)
- [CHANGELOG.md](CHANGELOG.md) · [DEPRECATION.md](DEPRECATION.md)
- Structure guardrails: [.github/scripts/verify_structure_hygiene.sh](.github/scripts/verify_structure_hygiene.sh)

## Encyclopedia / Miniwiki

- [docs/wiki/README.md](docs/wiki/README.md) — research reference layer (scaffolding lands in PR-2; content in PR-3 onward).

## Archive

- [docs/archive/README.md](docs/archive/README.md)

---

### Gateway discipline

- Every active doc is reachable from this page in ≤ 3 clicks.
- Removing or renaming an active doc requires updating this page in the same PR.
- Wiki (`docs/wiki/**`) pages carry `last_reviewed`, `owner`, `status` headers; this gateway does not replace those.
