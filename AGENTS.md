# AGENTS.md

This file exists for cross-tool portability. textgraphx uses an open standard
that is read by multiple AI coding agents (Cursor, Aider, Claude Code,
OpenAI Codex CLI, and others).

**The canonical project guidelines live in [.github/copilot-instructions.md](.github/copilot-instructions.md).**

All agents — regardless of vendor — should treat that file as authoritative.

## Quick orientation

textgraphx is an event-centric, temporally-grounded knowledge graph
construction system that transforms unstructured text into a Neo4j labelled
property graph, with token- and span-grounded provenance and MEANTIME-aligned
evaluation (M1–M10 framework).

## File map

| Concern | File |
|---------|------|
| Project-wide guidelines | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| Pipeline phase rules | [.github/instructions/pipeline-phases.instructions.md](.github/instructions/pipeline-phases.instructions.md) |
| Schema & migration rules | [.github/instructions/schema.instructions.md](.github/instructions/schema.instructions.md) |
| Cypher authoring rules | [.github/instructions/cypher.instructions.md](.github/instructions/cypher.instructions.md) |
| Test authoring rules | [.github/instructions/tests.instructions.md](.github/instructions/tests.instructions.md) |
| Evaluation framework rules | [.github/instructions/evaluation.instructions.md](.github/instructions/evaluation.instructions.md) |
| Reusable workflows | [.github/prompts/](.github/prompts/) |
| Architecture overview | [docs/architecture-overview.md](docs/architecture-overview.md) |
| Schema reference | [docs/schema.md](docs/schema.md) |
| Contribution workflow | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Build & test essentials

```bash
# Install
pip install -e .

# Fast smoke check
pytest src/textgraphx/tests -m "unit or contract" -q

# Pre-merge sweep
pytest src/textgraphx/tests -m "not slow" -q
```

## Hard rules (must not violate)

1. Use canonical import paths (`textgraphx.pipeline.*`, `textgraphx.orchestration.*`) — root-level files like `GraphBasedNLP.py` are compatibility shims only.
2. Never generate random IDs. Use deterministic hash → integer fallback.
3. Never write evaluation artifacts outside `src/textgraphx/datastore/evaluation/`.
4. Never commit secrets (Neo4j credentials, LLM API keys).
5. Schema changes require a migration in `src/textgraphx/schema/migrations/` plus an ontology + docs update in the same PR.
6. Every node and edge written by a phase carries a `source` provenance property.

For everything else, see [.github/copilot-instructions.md](.github/copilot-instructions.md).
