# TLINK Case4/Case5 Per-Document Breakdown

Generated on 2026-04-20 from live Neo4j after cycle_20260420T094226Z.

## TLINK Rollup by Document

| doc_id | total_tlinks | case4 | case5 | case_rules |
|---:|---:|---:|---:|---:|
| 76437 | 187 | 19 | 4 | 0 |
| 62405 | 131 | 0 | 2 | 0 |
| 112579 | 128 | 8 | 5 | 0 |
| 82738 | 114 | 0 | 5 | 0 |
| 61327 | 94 | 0 | 13 | 0 |
| 96770 | 74 | 6 | 1 | 0 |

## Case4/Case5 by doc_id and relType

| doc_id | rule_id | relType | count |
|---:|---|---|---:|
| 61327 | case5_timex_preposition | ENDED_BY | 5 |
| 61327 | case5_timex_preposition | IS_INCLUDED | 8 |
| 62405 | case5_timex_preposition | IS_INCLUDED | 2 |
| 76437 | case4_timex_head_match | IS_INCLUDED | 19 |
| 76437 | case5_timex_preposition | IS_INCLUDED | 4 |
| 82738 | case5_timex_preposition | IS_INCLUDED | 5 |
| 96770 | case4_timex_head_match | IS_INCLUDED | 6 |
| 96770 | case5_timex_preposition | IS_INCLUDED | 1 |
| 112579 | case4_timex_head_match | IS_INCLUDED | 8 |
| 112579 | case5_timex_preposition | IS_INCLUDED | 5 |

## Strict Relation Error Hotspots (from eval_report_strict_docs.csv)

| doc_id | relation_f1 | tp | fp | fn | missing | spurious |
|---:|---:|---:|---:|---:|---:|---:|
| 61327 | 0.0000 | 0 | 22 | 11 | 10 | 21 |
| 96770 | 0.0645 | 1 | 17 | 12 | 9 | 14 |
| 112579 | 0.0870 | 2 | 30 | 12 | 12 | 30 |
| 76437 | 0.0968 | 3 | 48 | 8 | 7 | 47 |
| 62405 | 0.1053 | 2 | 24 | 10 | 9 | 23 |
| 82738 | 0.1250 | 2 | 15 | 13 | 13 | 15 |

## Notes

- No TLINK rows with rule_id=case_rules were found after rerun.
- Case4 appears in docs: 76437, 96770, 112579.
- Case5 appears in all six evaluated docs; largest concentration is doc 61327.
