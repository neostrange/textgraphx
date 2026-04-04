# text2graphs (textgraphx)

A comprehensive, domain-agnostic NLP pipeline that transforms unstructured text documents into rich knowledge graphs stored in Neo4j, enabling advanced information extraction, question answering, and temporal reasoning capabilities.

## Business Context

### Problem Statement

Organizations dealing with large volumes of unstructured text data face significant challenges in extracting actionable insights, understanding temporal relationships, and connecting entities across documents. Traditional NLP approaches often produce flat annotations that lack the structural richness needed for complex analytical tasks.

### Solution Overview

text2graphs implements a sophisticated pipeline-based system that converts raw text into a strongly-typed knowledge graph representation. The system is specifically designed for the Australian innovation ecosystem but maintains domain-agnostic architecture, making it applicable to various domains including:

- **Innovation & Technology**: Tracking startup activities, funding events, technology deployments
- **Policy Analysis**: Government announcements, regulatory changes, policy impacts
- **Economic Intelligence**: Market trends, industry developments, economic indicators
- **Research & Development**: Academic collaborations, publication tracking, research funding
- **Corporate Intelligence**: Business partnerships, mergers, market expansions

### Key Business Value

1. **Enhanced Information Discovery**: Graph-based queries enable complex relationship traversals
2. **Temporal Intelligence**: Rich temporal modeling for understanding event sequences and causality
3. **Entity Resolution**: Advanced disambiguation and linking across knowledge bases
# text2graphs (textgraphx)

An opinionated, modular NLP pipeline that converts unstructured text into a richly-typed knowledge graph in Neo4j.

This README is intended as a single, practical knowledge base for different audiences (developers, architects, researchers, maintainers, product teams and domain specialists). It documents system goals, architecture, data model, per-phase behavior, operational commands, validation and troubleshooting guidance.

Table of contents
- Overview & value proposition
- Quick start (how to run locally)
- Architecture & components (developer view)
- Data model / semantic model (nodes, relationships, id conventions)
- Phase → graph population mapping (component-by-component)
- Diagnostics, validation & testing (how to check the graph)
- Operational notes & best practices (performance, idempotency, brittle rules)
- Audience-specific guidance (developers, researchers, product)
- Next steps and extensions
 - Generated docs (human-friendly): `textgraphx/docs/ontology.html`

## Overview & value proposition

text2graphs turns raw documents into a connected knowledge graph representing tokens, mentions, events, temporal expressions and canonical entities. By combining modern NLP components (spaCy for tokenization/parse, SRL, coreference, external entity linking and temporal extractors) with conservative, idempotent Cypher writing patterns, the system provides:

- A reproducible graph ontology for downstream analytics and QA
- Temporal reasoning primitives (events, timex, TLINKs)
- Entity linking & canonicalization (NamedEntity → Entity)
- Heuristics for argument-head detection and participant wiring for events
- Instrumentation and diagnostics to detect brittle rule matches (POS/dependency mismatches)

Primary uses: research experiments, information extraction for product analytics, temporal/event pipelines, entity-centric graph exploration and downstream KG-driven apps.

## Quick start

Prerequisites
- Python 3.10+ (project uses a venv in `venv/` in this workspace)
- Neo4j accessible via Bolt (URI, user, password) — you can use a local or remote instance

Configuration
- The centralized Neo4j helper reads `textgraphx/config.ini` (sections `[py2neo]` or `[neo4j]`) or environment variables `NEO4J_URI`, `NEO4J_USER`/`NEO4J_USERNAME`, `NEO4J_PASSWORD`.
- See `textgraphx/neo4j_client.py` for the exact precedence and compatibility wrapper used by the codebase.

Centralized configuration
- New: a single config loader is available at `textgraphx.config.load_config()` / `textgraphx.config.get_config()`.
- The loader supports INI or TOML formats and environment variable overrides. The recommended example files are provided as
  `textgraphx/config.example.toml` and `textgraphx/config.example.ini`.
- Precedence: explicit path -> $TEXTGRAPHX_CONFIG -> repo `textgraphx/config.ini` -> user `~/.textgraphx/config.ini` -> built-in defaults. Environment variables (e.g. `NEO4J_URI`, `TEXTGRAPHX_LOG_JSON`) override file values.
- Common env vars mapped by the loader:
  - NEO4J_URI, NEO4J_USER / NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
  - TEXTGRAPHX_LOG_LEVEL, TEXTGRAPHX_LOG_JSON, TEXTGRAPHX_LOG_FILE
  - SPACY_MODEL, SPACY_USE_GPU
  - TEXTGRAPHX_DATA_DIR, TEXTGRAPHX_OUTPUT_DIR, TEXTGRAPHX_TMP_DIR
  - TEXTGRAPHX_RUNTIME_MODE, TEXTGRAPHX_STRICT_TRANSITION_GATE

Runtime transition gate policy
- Config key: `[runtime] strict_transition_gate = auto|true|false`.
- Env override: `TEXTGRAPHX_STRICT_TRANSITION_GATE=auto|true|false`.
- `auto` behavior: enabled in testing mode, disabled in production mode.
- Recommended values:
  - CI/review pipelines: `true` (fail fast on legacy-dominance assertion failures)
  - Local development: `auto` (strict in testing runs, relaxed in production runs)

Review profile (local)
- Run the local review profile that mirrors CI strict settings:

```bash
bash scripts/run_review_profile.sh
```

- This script sets:
  - `TEXTGRAPHX_RUNTIME_MODE=testing`
  - `TEXTGRAPHX_STRICT_TRANSITION_GATE=true`
- and executes the strict regression suite (`phase_assertions`, `orchestration`, `regression_phases`).

CI enforcement
- GitHub Actions workflow: `.github/workflows/strict-transition-gate.yml`
- The workflow runs the same strict suite under testing mode with strict gate enabled.

Pull request requirement
- PRs should pass the `strict-transition-gate` workflow before merge.
- Local preflight command:

```bash
make review
```

Usage example (programmatic):

```python
from textgraphx.config import get_config
cfg = get_config()
print(cfg.neo4j.uri)
```

If you'd like to adopt TOML for repository config, copy `textgraphx/config.example.toml` to `textgraphx/config.toml` or set `TEXTGRAPHX_CONFIG` to point at your custom config file.

Run a simple diagnostic (local)

1. Activate venv

```bash
source venv/bin/activate
```

2. Run the schema validation diagnostics (prints node/rel counts)

```bash
python -m textgraphx.tools.schema_validation
```

If you prefer a config file: `python -m textgraphx.tools.schema_validation path/to/config.ini`

Note: The validation script uses the same compatibility wrapper as the rest of the code so it behaves like the application when opening sessions.

Evaluation reports

- The MEANTIME evaluation CLI writes generated reports to `textgraphx/datastore/evaluation/` by default.
- Default artifacts:
  - `eval_report.json`
  - `eval_report.md`
  - `eval_report_docs.csv`
  - `eval_report_summary.csv`
- This keeps `textgraphx/datastore/annotated/` reserved for annotated source files only.
- You can still override output locations with `--out-json`, `--out-markdown`, and `--export-csv-prefix`.

Example:

```bash
python -m textgraphx.tools.evaluate_meantime \
  --gold-dir textgraphx/datastore/annotated \
  --pred-xml-dir textgraphx/datastore/annotated
```

Dataset locations (source vs gold)
----------------------------------

- Source dataset directory used by pipeline runs in this workspace:
  - /home/neo/environments/textgraphx/textgraphx/datastore/dataset
  - Source files in this directory are NAF files (.naf).
- Gold-standard dataset directory used for evaluation:
  - textgraphx/datastore/annotated
  - Gold files in this directory are XML files (.xml).

This means the operational flow is:
1. Run pipeline ingestion/extraction from the source NAF dataset directory.
2. Run evaluator with gold XML files from the annotated directory.

Quick CLI extras
----------------

Two small runtime conveniences were added to make local and CI runs faster and more predictable:

- `TEXTGRAPHX_FAST=1` — when set in the environment, core scripts (including `GraphBasedNLP.py`) will prefer the lightweight spaCy model `en_core_web_sm` to speed tokenization and parsing. This is useful in CI or local smoke tests where transformer accuracy is not needed.

- `--require-neo4j` — a CLI flag available in `GraphBasedNLP.py` that performs an early Neo4j connectivity check and will fail fast if the database is unreachable. Useful for CI jobs that must verify DB accessibility before proceeding.

Example (fast, no-neo4j required):

```bash
TEXTGRAPHX_FAST=1 python -m textgraphx.GraphBasedNLP --dir data/sample_docs --model sm
```

Example (fail fast if Neo4j unreachable):

```bash
python -m textgraphx.GraphBasedNLP --require-neo4j
```

Pipeline runner and cleanup policy
----------------------------------

Use `textgraphx/run_pipeline.py` as the canonical entrypoint for local runs.
It now delegates to the architecture-level orchestrator in
`textgraphx/orchestration/orchestrator.py` and supports an explicit Neo4j
cleanup policy for repeatable test runs on the same document.

```bash
python textgraphx/run_pipeline.py \
  --dataset textgraphx/datastore/dataset \
  --cleanup auto
```

Cleanup modes:
- `auto` (recommended for testing): detect whether dataset documents already
  exist in Neo4j and clear stale graph state before rerun when runtime mode is
  `testing`.
- `none`: never clear graph state automatically.
- `full`: wipe all nodes in Neo4j before running selected phases.

This prevents duplicate graph materialization during iterative
development/evaluation loops while keeping production behavior guarded by
runtime mode.

## Logging

The project provides a small helper to configure logging consistently across scripts and interactive runs:

```python
from textgraphx.logging_config import configure_logging

# set a global logging level for the process (INFO, DEBUG, WARN, ERROR)
configure_logging("DEBUG")

# now import and run any textgraphx module — logs will include module names and timestamps
import textgraphx.tools.schema_validation as sv
sv.main(None)
```

Quick one-liner to run a module with debug logging from the shell:

```bash
python -c "from textgraphx.logging_config import configure_logging; configure_logging('DEBUG'); import textgraphx.tools.schema_validation as sv; sv.main(None)"
```

Tip: add `configure_logging()` at the top of short scripts that import `textgraphx` modules to get consistent, timestamped logs. The default format includes timestamp, level and module name which helps when debugging multi-step pipelines.

## Architecture & components (developer view)

Top-level layout (key files / folders)
- `textgraphx/` — primary pipeline and phase modules
  - `TextProcessor.py` — orchestration helpers, example relationship-extraction logic
  - `neo4j_client.py` — centralized Neo4j bolt driver helper + py2neo-compatible wrapper
  - `RefinementPhase.py` — idempotent refinement rules (head-finding, FA→Entity linking)
  - `TemporalPhase.py` — TIMEX/TEvent creation and TLINK wiring
  - `EventEnrichmentPhase.py` — frame → event linking and participant creation
- `textgraphx/text_processing_components/` — token-level writers and per-component Cypher generators
  - `textgraphx/text_processing_components/TagOccurrenceCreator.py` / `textgraphx/text_processing_components/TagOccurrenceQueryExecutor.py` — token → TagOccurrence writes and HAS_NEXT linking
  - `textgraphx/text_processing_components/SRLProcessor.py` — Frame and FrameArgument creation, PARTICIPANT wiring
  - `textgraphx/text_processing_components/EntityProcessor.py` / `textgraphx/text_processing_components/EntityDisambiguator.py` — NamedEntity creation and optional KB linking to Entity
  - `textgraphx/text_processing_components/CoreferenceResolver.py` — Antecedent/CorefMention creation and COREF edges
- `textgraphx/schema/ontology.json` — machine-readable ontology (nodes/relations + diagnostics)
- `textgraphx/tools/schema_validation.py` — runs diagnostics defined in the ontology against Neo4j

Design notes
- Centralized DB access: `textgraphx/neo4j_client.py` implements `make_graph_from_config()` and `BoltGraphCompat` to keep code that expects py2neo-like `.run(...).data()` working with the official bolt driver.
- Idempotency: phases write using MERGE with deterministic document-scoped ids to make repeated runs safe.
- Phases are intentionally decoupled — you can run only tokenization, or run refinement/temporal phases against an existing graph.

## Data model / semantic model (canonical)

This project uses a strongly-typed graph model. The machine-readable form is available at `textgraphx/schema/ontology.json`; below is a developer-friendly summary.

Node labels (short reference)
- AnnotatedText — document node: id, text, creationtime, metadata
- Sentence — sentence container: id (commonly `<doc>_<sent_index>`), text
- TagOccurrence — token node: id, text, lemma, pos, upos, tok_index_doc, tok_index_sent, is_stop, etc.
- Tag — lemma grouping node
- NamedEntity — mention: id `<doc>_<start>_<end>_<type>`, type, value, kb_id, score
  - New (migration): `token_id` — a token-index canonical id (format: `<doc>_<tok_start>_<tok_end>_<type>`)
    - Purpose: many downstream phases and deterministic MERGE operations prefer token-index ids because token boundaries are stable across most annotation passes. The project now stores a non-destructive `token_id` property on `NamedEntity` nodes alongside the original `id` (which may be char-offset based) to support a migration path.
    - Migration: a helper script `textgraphx/tools/migrate_namedentity_token_ids.py` computes token-index mappings for existing `NamedEntity` nodes (dry-run mode) and can apply them (`--apply`) to add `token_id`, `token_start` and `token_end` properties to nodes. The script is intentionally non-destructive: it does not change the original `id` property.
    - To inspect mappings without writing to the database:

      python -m textgraphx.tools.migrate_namedentity_token_ids --dry-run

    - To apply computed mappings to the DB (make a backup first):

      python -m textgraphx.tools.migrate_namedentity_token_ids --apply

    - A lightweight migration file that creates a uniqueness constraint for `NamedEntity.token_id` is available at `textgraphx/schema/migrations/0002_create_namedentity_tokenid_constraint.cypher`. Use the migrations runner `textgraphx/tools/run_migrations.py` to apply migrations in order.
- Entity — canonical kb-backed entity: id, kb_id, type
- Frame — SRL predicate: id `frame_<doc>_<start>_<end>`, headTokenIndex, text
- FrameArgument — SRL argument: id `fa_<doc>_<start>_<end>_<type>`, syntacticType, headTokenIndex, complementFullText
- Antecedent / CorefMention — coreference cluster head and mention
- TIMEX / TEvent — temporal nodes with tid/eiid and doc-scoped ids
- NUMERIC — numeric literal nodes (MONEY, QUANTITY etc.)
- Evidence / Relationship — mention-level relation provenance (created by `TextProcessor.py` relationship extraction)

Primary relationships
- CONTAINS_SENTENCE: AnnotatedText -> Sentence
- HAS_TOKEN: Sentence -> TagOccurrence
- HAS_NEXT: TagOccurrence -> TagOccurrence (sentence-ordered chain; property `sentence`)
- PARTICIPATES_IN: TagOccurrence -> (NamedEntity | Frame | FrameArgument | Antecedent | CorefMention | NounChunk)
- PARTIPICANT / PARTICIPANT: FrameArgument -> Frame (role typed)
- IS_DEPENDENT: TagOccurrence -> TagOccurrence (dependency edges with `type` property)
- TRIGGERS: TagOccurrence -> TIMEX|TEvent
- DESCRIBES: Frame -> TEvent
- TLINK: TEvent/TIMEX -> TEvent/TIMEX (temporal relations with `relType` / `id`)
- REFERS_TO: NamedEntity -> Entity and also TagOccurrence -> Tag
- IS_RELATED_TO: NamedEntity -> NamedEntity (mention-level relation, properties `root`, `type`)
- Evidence provenance edges: SOURCE / DESTINATION, and Relationship node attached with FROM / TO and HAS_EVIDENCE

Id patterns (conventions used by components)
- Frame: `frame_<doc>_<start>_<end>`
- FrameArgument: `fa_<doc>_<start>_<end>_<argtype>`
- NamedEntity: `<doc>_<start>_<end>_<type>`
- TagOccurrence: `<doc>_<sent>_<token_idx>` or similar document-scoped token id

These conventions appear in the SRL and NER components (see `SRLProcessor.py` and `EntityProcessor.py`) and are relied upon by later phases for deterministic MERGE operations.

## Phase → Graph population mapping (detailed)

This section gives a per-phase, fine-grained list of the graph elements created or updated and references to code locations. Use this to plan runs or write small integration tests.

- Document import (first contact)
  - Writes: `AnnotatedText` nodes (id, text, metadata)
  - Files: `textgraphx/text_processing_components/DocumentImporter.py`, `textgraphx/TextProcessor.py` (import examples)

- Tokenization & TagOccurrence creation (spaCy)
  - Writes: `Sentence`, `TagOccurrence` nodes and token chaining
  - Edges: `AnnotatedText` -[:CONTAINS_SENTENCE]-> `Sentence`, `Sentence` -[:HAS_TOKEN]-> `TagOccurrence`, `TagOccurrence` -[:HAS_NEXT]-> `TagOccurrence`
  - Files: `textgraphx/text_processing_components/TagOccurrenceCreator.py`, `textgraphx/text_processing_components/TagOccurrenceQueryExecutor.py`
  - Notes: tokens include `tok_index_doc` (global index) used for deterministic linking across phases

- Named Entity Recognition (NER)
  - Writes: `NamedEntity` nodes (surface mentions)
  - Edges: `TagOccurrence` -[:PARTICIPATES_IN]-> `NamedEntity`
  - Files: `textgraphx/text_processing_components/EntityProcessor.py`, `textgraphx/text_processing_components/EntityExtractor.py`

- Entity Linking / Disambiguation (NEL)
  - Writes: `Entity` nodes (canonical), sets `NamedEntity.kb_id` and `NamedEntity.url_wikidata`
  - Edges: `NamedEntity` -[:REFERS_TO {type:'evoke'}]-> `Entity`
  - Files: `textgraphx/text_processing_components/EntityDisambiguator.py`

- Semantic Role Labeling (SRL)
  - Writes: `Frame` and `FrameArgument` nodes
  - Edges: `TagOccurrence` -[:PARTICIPATES_IN]-> `Frame`/`FrameArgument`, `FrameArgument` -[:PARTICIPANT]-> `Frame`
  - Files: `textgraphx/text_processing_components/SRLProcessor.py`

- Coreference resolution
  - Writes: `Antecedent` and `CorefMention` nodes; `COREF` edges point from mentions to antecedents
  - Edges: `TagOccurrence` -[:PARTICIPATES_IN]-> `Antecedent|CorefMention`; `CorefMention` -[:COREF]-> `Antecedent`
  - Files: `textgraphx/text_processing_components/CoreferenceResolver.py`

- RefinementPhase (head-finding, FA→Entity linking, canonicalization)
  - Updates: `FrameArgument` headTokenIndex/head/headPos/syntacticType; sets `FrameArgument` -[:REFERS_TO]-> `NamedEntity|Entity|NUMERIC` when a referent is found
  - Writes: may create `Entity` nodes for fusions and set `NamedEntity.kb_id` via coref propagation
  - Files: `textgraphx/RefinementPhase.py` (the most query-rich phase; use its instrumentation for diagnostics)
  - Notes: many heuristics rely on POS and `IS_DEPENDENT.type`; keep instrumentation on during tuning

- TemporalPhase (TIMEX & TEvent creation)
  - Writes: `TIMEX` and `TEvent` nodes and `TLINK` relationships
  - Edges: `TagOccurrence` -[:TRIGGERS]-> (`TIMEX`|`TEvent`)
  - Files: `textgraphx/TemporalPhase.py` and `textgraphx/TlinksRecognizer.py`

- EventEnrichmentPhase (frame → event linking)
  - Writes: `DESCRIBES` edges `Frame` -> `TEvent` and event `PARTICIPANT` relationships from `Entity`/`NUMERIC` to `TEvent`
  - Files: `textgraphx/EventEnrichmentPhase.py`

- Relationship extraction (mention-level relations → canonical relationships)
  - Writes: `NamedEntity` -[:IS_RELATED_TO]-> `NamedEntity` (mention-level), `Evidence` and `Relationship` nodes with provenance edges SOURCE/DESTINATION, and `Relationship` -[:FROM]->Entity / -[:TO]->Entity
  - Files: `textgraphx/TextProcessor.py` (the example `extract_relationships` implementation)

## Diagnostics, validation & testing

Machine-readable ontology
- `textgraphx/schema/ontology.json` contains the node/relationship inventory and diagnostic Cypher queries used by the validation tool.

Validation script
- `textgraphx/tools/schema_validation.py` runs a set of COUNT diagnostics against Neo4j and prints the results. It uses the same connection logic as the pipeline and is the recommended starting point when onboarding a new dataset or environment.

How to add more diagnostics
- Add an entry to `schema/ontology.json` under `diagnostics` with a `name` and a Cypher `query` that returns a single-row count (alias `cnt`) or any map you prefer; the script will print the first value returned.

Example diagnostic queries (taken from `RefinementPhase.py`):

```cypher
MATCH (n:TagOccurrence) RETURN count(n) AS cnt
MATCH (n:NamedEntity) RETURN count(n) AS cnt
MATCH ()-[r:IS_DEPENDENT]-() RETURN count(r) AS cnt
MATCH ()-[r:PARTICIPATES_IN]-() RETURN count(r) AS cnt
```

## Operational notes & best practices

Idempotency
- The code uses `MERGE` with deterministic, document-scoped ids to make writes safe for repeated runs. This lets you run tokenization, then SRL, then refinement independently and re-run phases without creating duplicate nodes.

Brittle rules and debugging
- Many refinement rules and event enrichment patterns rely on exact POS tags and dependency labels (e.g., `IS_DEPENDENT.type = 'pobj'`). If your spaCy model or upstream parser uses slightly different labels or tokenization boundaries, the Cypher patterns may return zero matches.
- Use the built-in instrumentation (logging + counts in `RefinementPhase`) and the `schema_validation.py` diagnostics to detect when queries execute but match zero rows.

Performance and batching
- Token writes use UNWIND / FOREACH patterns in Cypher to batch node/relationship creation. Where possible, use parameterized UNWINDs instead of per-token single MERGE calls.
- For very large corpora, consider chunking by document and running phases in parallel workers with transaction-scoped drivers (the bolt driver supports concurrent sessions). Monitor memory usage in bulk UNWIND operations.

Data quality & best practices
- Use a consistent spaCy model across runs. Record the model version in document metadata when importing.
- Keep `tok_index_doc` stable: many downstream MERGE operations assume consistent global token indexing.
- When tuning refinement heuristics, enable detailed logging and run diagnostics before/after changes to validate their effect on node/relationship counts.

## Audience-specific guidance (short)

Developers
- Files to start: `textgraphx/neo4j_client.py`, `textgraphx/text_processing_components/TagOccurrenceQueryExecutor.py`, `textgraphx/text_processing_components/SRLProcessor.py`, `textgraphx/RefinementPhase.py`.
- Add unit tests that run small sample documents through each phase and validate expected nodes/rel counts using `schema_validation.py`.

Researchers
- Use the graph to run experiments on event co-occurrence, temporal patterns, and entity network centrality. The Frame/FrameArgument primitives let you test diverse SRL-driven hypotheses.

Product / business teams
- The graph is well-suited for building entity-centric dashboards, tracking events (fundings, launches) and temporal chains (policy→impact). Use the `Entity` canonicalization outputs for cross-document linking.

Maintainers / Operators
- Automate diagnostics in CI: run `schema_validation.py` and ensure counts are above thresholds after pipeline runs.
- Keep Neo4j backups before running large refactorings. The pipeline writes are idempotent, but transformations that change id schemes or drop properties are destructive.

## Troubleshooting (common issues)

- No matches for refinement rules
  - Likely cause: different POS tags or dependency labels. Solution: run diagnostics, sample failing docs, print token properties and adapt Cypher filters.

- Duplicate nodes after re-run
  - Likely cause: upstream id conventions were changed or not applied. Solution: check id generation (TagOccurrence id and NamedEntity id conventions) and re-run phases that set ids.

- Slow UNWINDs or transaction timeouts
  - Reduce UNWIND sizes, run in smaller batches, or increase transaction timeout in Neo4j configuration.

## Next steps & optional extras I can add

- Generate a human-friendly YAML or HTML version of `schema/ontology.json`.
- Create a `tools/schema_asserts.py` that checks threshold counts and returns non-zero exit codes for CI.
- Produce a CSV mapping of exact Cypher statements to file path and approximate line numbers for per-query traceability.

If you'd like any of the above (or want me to wire CI checks), tell me which and I will implement it next.

Documentation & CI
------------------
- A human-friendly HTML/YAML view of the machine-readable ontology is generated into `textgraphx/docs/ontology.html` and `textgraphx/docs/ontology.yaml`.
- A GitHub Actions workflow `.github/workflows/schema_asserts.yml` is included which starts a disposable Neo4j service and runs `textgraphx/tools/schema_asserts.py` using the diagnostics in `schema/ontology.json`. The workflow expects the repository's Python requirements to be installable; adjust `textgraphx/requirements.txt` in CI as needed.

---

License: See `textgraphx/LICENSE` (the project includes a license file)


            - Many refinement Cypher rules rely on POS (`pos`/`upos`) and dependency `IS_DEPENDENT.type` labels; small differences in upstream tokenization or dependency labels may lead to no matches. Instrumentation (query logging & diagnostic counts) helps determine whether a query ran but matched zero rows.
            - The code uses a compatibility wrapper around the Neo4j bolt driver to present a py2neo-like .run(...).data() surface — centralize DB config in `textgraphx/neo4j_client.py`.
            - Use MERGE and stable ids where possible when writing nodes so subsequent runs remain idempotent.

            ---

            ## Where to look in the code (useful files)

            - `textgraphx/text_processing_components/TagOccurrenceCreator.py` — token → TagOccurrence creation and properties
            - `textgraphx/text_processing_components/EntityProcessor.py` — NamedEntity creation and linking
            - `textgraphx/text_processing_components/SRLProcessor.py` — Frame and FrameArgument creation
            - `textgraphx/text_processing_components/CoreferenceResolver.py` — Antecedent / CorefMention creation and COREF linking
            - `textgraphx/RefinementPhase.py` — head-finding & FA→Entity linking rules (contains many Cypher rules and instrumentation)
            - `textgraphx/TemporalPhase.py` — TIMEX / TEvent creation and TLINK wiring
            - `textgraphx/EventEnrichmentPhase.py` — event ↔ frame ↔ participant wiring
            - `textgraphx/neo4j_client.py` — centralized bolt-driver helper and compatibility wrapper

            ---

            ## Phase → Graph population mapping

            The table below describes the typical pipeline order (from text processing to enrichment) and itemizes, for each phase or component, which graph elements it creates or updates, plus the primary code files that implement the work. Use this as a quick reference for how the knowledge graph is populated step-by-step.

            - Document import (first contact)
                - Creates/updates: `AnnotatedText` nodes (id, text, metadata)
                - Relationships: none by default (importers sometimes add metadata relationships)
                - Files: `textgraphx/TextProcessor.py`, `textgraphx/text_processing_components/DocumentImporter.py` (Meantime/XML importer variations)
                - Notes: must run before tokenization; importer sets the document id used as the namespace for deterministic ids.

            - Tokenization & TagOccurrence creation (spaCy pipeline)
                - Creates/updates: `Sentence`, `TagOccurrence` nodes (token-level properties: text, lemma, pos, upos, tok_index_doc, tok_index_sent, index, is_stop, morphological features)
                - Relationships: `AnnotatedText` -[:CONTAINS_SENTENCE]-> `Sentence`, `Sentence` -[:HAS_TOKEN]-> `TagOccurrence`, `TagOccurrence` -[:HAS_NEXT]-> `TagOccurrence`, `TagOccurrence` -[:REFERS_TO]-> `Tag` (lemma grouping)
                - Files: `textgraphx/text_processing_components/TagOccurrenceCreator.py`, `textgraphx/text_processing_components/TagOccurrenceQueryExecutor.py`
                - Notes: provides the token indices (`tok_index_doc`) that downstream phases use to MERGE PARTICIPATES_IN links deterministically.

            - Named Entity Recognition (NER) & initial mentions
                - Creates/updates: `NamedEntity` nodes (id convention: `<doc>_<start>_<end>_<type>`, properties: type, value, index, end_index, optionally kb_id/url_wikidata)
                - Relationships: `TagOccurrence` -[:PARTICIPATES_IN]-> `NamedEntity`
                - Files: `textgraphx/text_processing_components/EntityProcessor.py`
                - Notes: NER outputs are surface mentions; disambiguation to canonical `Entity` happens in later phases.

            - Entity Linking / Disambiguation (NEL)
                - Creates/updates: `Entity` nodes (canonical KB-backed nodes), sets `NamedEntity.kb_id`, `NamedEntity.url_wikidata`, `Entity` properties
                - Relationships: `NamedEntity` -[:REFERS_TO {type:'evoke'}]-> `Entity`
                - Files: `textgraphx/text_processing_components/EntityDisambiguator.py`, `textgraphx/text_processing_components/EntityProcessor.py`
                - Notes: this phase may be optional depending on external KB availability; code is conservative and idempotent (MERGE by canonical id).

            - Semantic Role Labeling (SRL)
                - Creates/updates: `Frame` (predicate) and `FrameArgument` nodes (argument spans). `Frame` properties include id, headword, headTokenIndex, text, startIndex, endIndex. `FrameArgument` properties include id, type (ARG0/ARG1/ARGM-*), startIndex, endIndex, head, headTokenIndex, syntacticType, complement fields.
                - Relationships: `TagOccurrence` -[:PARTICIPATES_IN]-> `Frame` and `FrameArgument`; `FrameArgument` -[:PARTICIPANT]-> `Frame`
                - Files: `textgraphx/text_processing_components/SRLProcessor.py`
                - Notes: FrameArgument nodes are the primary inputs for event enrichment and often later get REFERS_TO links to `NamedEntity` or `Entity`.

            - Coreference resolution
                - Creates/updates: `Antecedent` and `CorefMention` nodes (cluster heads and mentions), sets text/startIndex/endIndex
                - Relationships: `TagOccurrence` -[:PARTICIPATES_IN]-> (`Antecedent` | `CorefMention`), `CorefMention` -[:COREF]-> `Antecedent`
                - Files: `textgraphx/text_processing_components/CoreferenceResolver.py`
                - Notes: coref clusters are used by Refinement to propagate KB ids and to identify canonical heads for entity mentions.

            - RefinementPhase (head-finding, argument → entity linking, canonicalization)
                - Creates/updates: sets/updates properties on `FrameArgument`, `NamedEntity`, `Frame` (headTokenIndex, head, headPos, syntacticType, complement, complementFullText); may create `Entity` when fusing; updates `NamedEntity.kb_id` by propagation from coref clusters or direct matches
                - Relationships: `FrameArgument` -[:REFERS_TO]-> (`NamedEntity` | `Entity` | `NUMERIC`), `NamedEntity` -[:REFERS_TO]-> `Entity` (if canonicalized)
                - Files: `textgraphx/RefinementPhase.py`
                - Notes: Many Cypher rules run here. Instrumentation logs query text and returned counts so you can detect brittle patterns (POS or dependency filters that return zero matches). This phase is idempotent but relies on upstream annotations like `pos` and dependency edges.

            - TemporalPhase (TIMEX & TEvent creation)
                - Creates/updates: `TIMEX` nodes (temporal expressions) and `TEvent` nodes (temporalized events); sets properties such as `value`, `tid`, `eiid`, doc_id, start/end indices
                - Relationships: `TagOccurrence` -[:TRIGGERS]-> (`TIMEX` | `TEvent`), `TEvent`/`TIMEX` -[:TLINK]-> `TEvent`/`TIMEX` for temporal relations
                - Files: `textgraphx/TemporalPhase.py`
                - Notes: TIMEX extraction often relies on external tools (Heideltime/TTK); code MERGEs nodes by tid/eiid to preserve idempotency.

            - EventEnrichmentPhase (frame → event linking, participants)
                - Creates/updates: `DESCRIBES` edges from `Frame` to `TEvent`; creates event `PARTICIPANT` relationships between `Entity`/`NUMERIC` and `TEvent`; sets `FrameArgument.argumentType` when mapped to event roles
                - Relationships: `Frame` -[:DESCRIBES]-> `TEvent`, `Entity` -[:PARTICIPANT {type, prep?}]-> `TEvent`
                - Files: `textgraphx/EventEnrichmentPhase.py`, `textgraphx/text_processing_components/SRLProcessor.py` (argument role mapping)
                - Notes: argument `prep` is set on the PARTICIPANT relationship when the FrameArgument syntacticType indicates a prepositional complement.

            - TLINK Recognition / Temporal reasoning
                - Creates/updates: additional `TLINK` edges between events and time expressions, possibly with a `relType` property (BEFORE/AFTER/SIMULTANEOUS)
                - Files: `textgraphx/TlinksRecognizer.py`, `textgraphx/TemporalPhase.py`

            - Indexing / Constraints / Maintenance
                - Creates/updates: indexes/constraints (if configured) and lightweight summary nodes or caches
                - Files: `textgraphx/neo4j_client.py` (connection/setup helpers) and project-level migration scripts (if present)

            ### How to read the mapping

            - The mapping is ordered to reflect the most common execution order in the processing pipeline. Individual deployments may skip or reorder phases (for example, when only performing NER or only running temporal analysis over an existing graph).
            - Most writes are idempotent because code uses `MERGE` with deterministic string ids; however, refinement rules often assume exact POS/dependency labels — if your upstream tokenization or parser differs, some refinement queries may return zero matches.
            - For a query-by-query mapping (very granular), see `textgraphx/RefinementPhase.py`, `textgraphx/TemporalPhase.py`, and `textgraphx/EventEnrichmentPhase.py` — these files contain the explicit Cypher used to create or update graph elements.

            ---

            If you'd like, I can:

            - Generate a machine-readable ontology (YAML/JSON) of the nodes/relationships for programmatic validation
            - Add a small `schema_validation.py` script that runs quick COUNT checks (the same diagnostics used in `RefinementPhase`) against a live Neo4j instance
            - Produce per-phase pre-flight checks that skip heavy updates if no input nodes are present

            Tell me which of those you'd prefer next.
