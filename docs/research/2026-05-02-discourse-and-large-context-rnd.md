# Focused R&D: Missing Linguistic Components for Large-Context Text-to-KG

Date: 2026-05-02
Scope: discourse relations, inter-sentence reasoning, event/entity linking, scripts/narratives, causality, pragmatics for situational awareness.

## Executive Summary

TextGraphX already has meaningful building blocks for temporal/event-centric reasoning (TLINK pipeline, CLINK heuristics, factuality heuristics, entity coreference + optional cross-document entity fusion). However, the repository appears to lack first-class discourse parsing layers (RST and PDTB), robust inter-sentence/paragraph relation extraction, dedicated event coreference modules, and explicit pragmatics layers beyond factuality (attribution source modeling, stance, uncertainty calibration).

In practical terms, this is the key architectural gap:

- Existing graph strengths are event/entity grounding and temporal alignment.
- Missing layers are discourse structure and document-level inferential glue.
- Without those layers, situational awareness remains local and heuristic rather than discourse-aware and evidence-ranked.

## 1) Credible Source List (15)

Note: confidence is about citation fidelity (title/year/venue/URL), not paper quality.

| # | Source | Confidence | 1-line architecture implication |
|---|---|---|---|
| 1 | Mann, W.; Thompson, S. (1988). Rhetorical Structure Theory: Toward a Functional Theory of Text Organization. Text. URL: https://www.sfu.ca/rst/01intro/definitions.html | High | Introduce a discourse-tree layer with nucleus/satellite and relation labels that can anchor paragraph-level reasoning edges. |
| 2 | Carlson, L.; Marcu, D.; Okurowski, M. (2002). RST Discourse Treebank (LDC2002T07). URL: https://catalog.ldc.upenn.edu/LDC2002T07 | High | Add RST-supervised training/evaluation tracks for discourse relation nodes and EDU segmentation. |
| 3 | Prasad, R. et al. (2008). The Penn Discourse TreeBank 2.0. LREC. URL: https://catalog.ldc.upenn.edu/LDC2008T05 | High | Add PDTB explicit/implicit relation extraction stage with connective, Arg1/Arg2 span, and sense properties. |
| 4 | Webber, B. et al. (2019). The Penn Discourse Treebank 3.0 Annotation Manual / resource release. LDC. URL: https://catalog.ldc.upenn.edu/LDC2019T05 | Medium | Use PDTB3 sense hierarchy for normalized relation taxonomy and confidence-aware relation typing. |
| 5 | Ji, Y.; Eisenstein, J. (2014). Representation Learning for Text-level Discourse Parsing. ACL. URL: https://aclanthology.org/P14-1062/ | Medium | Build document-level encoder features for implicit relation classification beyond connective rules. |
| 6 | Yao, Y. et al. (2019). DocRED: A Large-Scale Document-Level Relation Extraction Dataset. ACL. URL: https://aclanthology.org/P19-1074/ | High | Add doc-level relation extraction benchmark harness and cross-sentence relation edges in KG. |
| 7 | Nan, G. et al. (2020). Reasoning with Latent Structure Refinement for Document-Level RE. ACL. URL: https://aclanthology.org/2020.acl-main.141/ | Medium | Introduce graph-refinement style message passing for inter-sentence relation inference in reasoning layer. |
| 8 | Barhom, S. et al. (2019). Revisiting Joint Modeling of Cross-document Entity and Event Coreference Resolution. ACL. URL: https://aclanthology.org/P19-1519/ | Medium | Add a joint entity+event linking module instead of separate, potentially conflicting cross-doc heuristics. |
| 9 | Cybulska, A.; Vossen, P. (2014). Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution. LREC. URL: https://aclanthology.org/L14-1728/ | Medium | Favor lexical+semantic event representation (not just string overlap) for event coreference in newswire-like corpora. |
|10| Chambers, N.; Jurafsky, D. (2008). Unsupervised Learning of Narrative Event Chains. ACL. URL: https://aclanthology.org/P08-1090/ | Medium | Add script/event-chain induction as optional enrichment edges among canonical events. |
|11| Pichotta, K.; Mooney, R. (2016). Learning Statistical Scripts with LSTM RNNs. AAAI. URL: https://arxiv.org/abs/1602.03181 | High | Introduce sequence-based script priors that score plausible next events for projection-level situational awareness. |
|12| Do, Q.X.; Chan, Y.S.; Roth, D. (2011). Minimally Supervised Event Causality Identification. EMNLP. URL: https://aclanthology.org/D11-1046/ | Medium | Add weakly supervised causality extractor to reduce dependence on handcrafted CLINK rules. |
|13| Dunietz, J.; Levin, L.; Carbonell, J. (2017). The BECauSE Corpus 2.0: Annotating Causality and Overlapping Relations. URL: https://aclanthology.org/W17-2711/ | Medium | Add causal-signal and argument-span nodes with overlap-aware relation modeling. |
|14| Sauri, R.; Pustejovsky, J. (2009). FactBank: A corpus annotated with event factuality. Language Resources and Evaluation. URL: https://link.springer.com/article/10.1007/s10579-009-9089-9 | High | Extend factuality from scalar labels to source-scoped factuality with nested attribution. |
|15| Rudinger, R. et al. (2018). Crowdsourcing Event Factuality Annotation. NAACL. URL: https://aclanthology.org/N18-2015/ | Medium | Build modern factuality calibration datasets and confidence learning for event-level uncertainty estimates. |

### Citation uncertainty notes

- #4 is listed via LDC release and associated PDTB3 resources; exact canonical paper title/venue metadata varies across references.
- #5, #7, #8, #9, #10, #12, #13, #15 URLs are high-quality archival links but exact anthology IDs should be re-checked during implementation PR prep.

## 2) Gap Matrix for TextGraphX Goals

Status terminology:
- Absent: no clear first-class component.
- Partial: some heuristic or adjacent support exists.

| Capability | Why it matters for TextGraphX goals | Current likely status | Recommended component(s) |
|---|---|---|---|
| RST discourse parsing (EDU + tree) | Enables paragraph/global coherence and discourse-grounded reasoning paths | Absent | EDU segmenter + RST parser stage; graph nodes: EDU, DiscourseRelation, nucleus/satellite edges |
| PDTB explicit relation extraction | Connective-based discourse links improve causality/contrast/condition reasoning | Absent | Connective detector + Arg1/Arg2 span linker + PDTB sense mapper |
| PDTB implicit relation extraction | Most discourse relations are implicit; needed for robust large-text reasoning | Absent | Sentence-pair classifier with document context features; confidence-thresholded relation writes |
| Inter-sentence document-level relation extraction | Entity/event relation signals often span sentences; central to situational awareness | Partial | DocRE module (DocRED-style) producing canonical cross-sentence relation edges |
| Paragraph-level aggregation and discourse state tracking | Situation assessment requires evolving context state across paragraphs | Absent | Discourse state nodes per paragraph/section + update edges with provenance/time |
| Event coreference (within-document) | Prevents event fragmentation; needed for timeline and causality consistency | Partial | Dedicated event-coref scorer over EventMention pairs + clusterer + conflict policy |
| Cross-document event linking | Required for longitudinal awareness and multi-document narrative fusion | Absent | Cross-document event linker using event arguments/time/predicate signatures |
| Cross-document entity linking confidence model | Current SAME_AS heuristics may over/under-link without calibrated confidence | Partial | Pairwise linker with type/time/context consistency + abstention policy |
| Script/event-chain induction | Supports projection (what likely happens next) and anomaly detection | Absent | Event chain induction pass writing NEXT_LIKELY / SCRIPT_ROLE edges |
| Causal signal extraction (lexical/discourse cues) | Moves CLINK from sparse rule triggers to explainable causal evidence | Partial | Signal node extractor (because/due to/therefore/as a result) + signal-to-CLINK attachment |
| Discourse signal extraction broadly (contrast, concession, condition) | Needed for robust decision support and contradiction-aware reasoning | Absent | SIGNAL and REL_SIGNAL layer tied to discourse relation edges |
| Attribution modeling (who claims what) | Critical for source reliability and intelligence-style situational awareness | Partial | AttributedClaim nodes linking source speaker -> proposition/event |
| Stance modeling | Distinguishes support/oppose/neutral toward events/claims | Absent | Stance classifier over source-target pairs linked to claim/event nodes |
| Uncertainty and epistemic calibration | Needed for confidence-aware downstream reasoning and alerting | Partial | Uncertainty classifier + calibration curves + uncertainty properties on claims/events |
| Contradiction and belief revision hooks | Large-text reasoning requires handling conflicting reports over time | Absent | Claim conflict detector + belief-state update rules with provenance priorities |

## 3) Prioritized Roadmap

### H1 (0-3 months): high-impact, low-risk

1. Add discourse signal extraction (explicit connectives + lexical cues) as a deterministic pass.
2. Add explicit PDTB-style relation extraction for connective-bearing cases only.
3. Add event coreference baseline (within-document) using deterministic + lightweight ML features.
4. Harden attribution modeling in factuality pipeline (source span, speaker entity, quote scope).
5. Add confidence schema for new discourse/event-link edges and basic calibration reports.

Expected gain: immediate jump in explainable discourse/causal coverage with minimal architecture disruption.

### H2 (3-9 months): medium complexity

1. Add implicit PDTB relation classifier for adjacent sentence/paragraph pairs.
2. Add document-level relation extraction module (DocRE-style) for inter-sentence entity/event relations.
3. Add cross-document event linking service with conservative abstention thresholds.
4. Add stance + uncertainty classifiers over attributed claims/events.
5. Add M8-aligned evaluation extensions for discourse and event-link quality gates.

Expected gain: meaningful paragraph/document reasoning and improved multi-document coherence.

### H3 (9-18 months): ambitious

1. Add RST parser integration (EDU segmentation + discourse tree persistence).
2. Add script/event-chain induction and narrative trajectory modeling.
3. Add contradiction detection + belief revision over attributed claims.
4. Add situation-state layer (per actor/org/topic) with temporal updates and forecast links.
5. Add end-to-end situational awareness benchmark suite (decision-support tasks, not only extraction F1).

Expected gain: transition from extraction-centric KG to reasoning-centric situational graph.

## 4) Minimal Viable Implementation Order (dependency logic)

Order is designed to minimize rework and maximize early utility.

1. Unified discourse/relation schema extension
   - Must come first so later modules write to stable labels/relations/properties.
2. Explicit discourse signal extraction (rule-based)
   - Lowest-risk producer of immediately useful discourse anchors.
3. Explicit PDTB relation extraction
   - Depends on signal extraction + schema; provides first discourse graph edges.
4. Attribution/source normalization for claims/events
   - Needed before stance/uncertainty and before contradiction handling.
5. Within-document event coreference baseline
   - Reduces event fragmentation before inter-sentence and cross-doc reasoning.
6. Inter-sentence DocRE module
   - Depends on cleaner event/entity canonicalization and relation schema.
7. Implicit discourse relation classifier
   - Benefits from improved sentence/paragraph representations and DocRE features.
8. Cross-document event linking
   - Should come after within-doc canonical event quality reaches acceptable precision.
9. Stance + uncertainty layer
   - Depends on attribution graph and claim/event targets.
10. RST tree integration
   - More expensive; best added after PDTB/DocRE signals already provide utility.
11. Script/event-chain induction
   - Depends on stable event coreference and cross-document linking.
12. Contradiction/belief revision
   - Depends on attribution + stance + uncertainty + event/claim linking.

## Repository-grounded status evidence

These code paths support the current-status judgments above:

- Cross-document entity fusion exists and is runtime-gated:
  - src/textgraphx/reasoning/fusion.py
  - src/textgraphx/pipeline/runtime/phase_wrappers.py
- Coreference persistence exists (entity mention oriented; no dedicated event-coref module in this file):
  - src/textgraphx/text_processing_components/CoreferenceResolver.py
- Causal links are present via SRL-driven CLINK derivation (rule-centric):
  - src/textgraphx/pipeline/phases/event_enrichment.py
- Factuality heuristics and attribution metadata fields exist (factualitySource/factualityConfidence):
  - src/textgraphx/pipeline/phases/event_enrichment.py
  - src/textgraphx/pipeline/runtime/phase_assertions.py

## Suggested low-effort uncertainty-reduction experiment (1 week)

Goal: determine whether discourse-signal extraction + explicit PDTB relations improve downstream causal/event consistency.

Recipe:
1. Add a deterministic connective/signal extractor (because, since, although, however, therefore, due to, as a result).
2. Materialize only explicit relations with confidence=high.
3. Re-run current MEANTIME cycle and compare:
   - CLINK precision/coverage,
   - factuality alignment violations,
   - event cluster consistency diagnostics.
4. Keep feature flag off by default; report deltas in latest vs baseline evaluation artifacts.

Decision rule:
- If explicit discourse edges improve at least one of CLINK precision or factuality consistency without major regressions, proceed to H1.2/H1.3.
- Otherwise, prioritize attribution/event-coref improvements before wider discourse rollout.
