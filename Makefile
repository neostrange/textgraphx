.PHONY: review strict-gate baseline quality-gate participant-benchmark nominal-filter-ab uid-preflight uid-smoke

PYTHON310 ?= /home/neo/environments/textgraphx/.venv310/bin/python
UID_DOCS ?= 112579

review:
	bash scripts/run_review_profile.sh

strict-gate: review

# Capture a fresh quality baseline (requires live Neo4j + .venv310).
baseline:
	bash scripts/run_quality_baseline.sh

# Compare the most recent evaluation run against the committed baseline.
# Run `make baseline` first to produce out/evaluation/baseline/kg_quality_report.json,
# then run `make quality-gate` after a new evaluation to check for regression.
quality-gate:
	python -m textgraphx.tools.check_quality_gate \
		--baseline out/evaluation/baseline/kg_quality_report.json \
		--current  out/evaluation/kg_quality_report.json \
		--tolerance 0.02 \
		--max-participation-in-frame-missing-increase 0 \
		--max-participation-in-mention-missing-increase 0 \
		--max-participation-in-frame-missing 0 \
		--max-participation-in-mention-missing 0 \
		--verbose

# Run 3-way participant-scope benchmark:
#   core-only vs constrained non-core (ARG0/ARG1) vs full non-core.
participant-benchmark:
	$(PYTHON310) scripts/run_participant_scope_benchmark.py --python-bin $(PYTHON310)

# Run 2-way ENH-NOM-04 benchmark:
#   legacy noun-chunk filter vs strict ENH-NOM-04 filter.
nominal-filter-ab:
	PYTHONPATH=src $(PYTHON310) scripts/run_nominal_filter_ab.py --python-bin $(PYTHON310)

uid-preflight:
	$(PYTHON310) -m textgraphx.tools.uid_smoke_preflight --preflight-only

uid-smoke:
	$(PYTHON310) -m textgraphx.tools.uid_smoke_preflight --docs $(UID_DOCS) --run-smoke --cleanup
