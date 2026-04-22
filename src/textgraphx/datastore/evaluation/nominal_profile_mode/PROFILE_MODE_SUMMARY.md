# Nominal Profile Mode Validation Summary

Date: 2026-04-04
Source: Neo4j prediction mode against local gold corpus (`1` available XML file)

## Entity-Layer Results (Micro Strict)

| Scope | Mode | Precision | Recall | F1 | Predicted Entities |
|---|---|---:|---:|---:|---:|
| baseline | all | 0.0576 | 0.4706 | 0.1026 | 139 |
| baseline | eventive | 0.0577 | 0.1765 | 0.0870 | 52 |
| baseline | salient | 0.0606 | 0.4706 | 0.1074 | 132 |
| baseline | candidate-gold | 0.0702 | 0.4706 | 0.1221 | 114 |
| baseline | background | 0.0625 | 0.1765 | 0.0923 | 48 |
| discourse_only | all | 0.0777 | 0.4706 | 0.1333 | 103 |
| discourse_only | eventive | 0.1111 | 0.1765 | 0.1364 | 27 |
| discourse_only | salient | 0.0777 | 0.4706 | 0.1333 | 103 |
| discourse_only | candidate-gold | 0.0889 | 0.4706 | 0.1495 | 90 |
| discourse_only | background | 0.1250 | 0.1765 | 0.1463 | 24 |
| discourse_plus_goldlike | all | 0.0800 | 0.4706 | 0.1368 | 100 |
| discourse_plus_goldlike | eventive | 0.0938 | 0.1765 | 0.1224 | 32 |
| discourse_plus_goldlike | salient | 0.0800 | 0.4706 | 0.1368 | 100 |
| discourse_plus_goldlike | candidate-gold | 0.0816 | 0.4706 | 0.1391 | 98 |
| discourse_plus_goldlike | background | 0.0938 | 0.1765 | 0.1224 | 32 |

## Best Mode Per Scope

- baseline: `candidate-gold` (F1 `0.1221`)
- discourse_only: `candidate-gold` (F1 `0.1495`)
- discourse_plus_goldlike: `candidate-gold` (F1 `0.1391`)

## Notes

- Winner is consistent across all evaluated scopes: `candidate-gold`.
- `eventive` and `background` give stronger pruning but lower recall.
- In this run state, projected event/timex/relation layers were zero in Neo4j prediction mode, so this summary is entity-layer focused.
- Since only one local gold document is currently available, these results are directional, not yet corpus-general.
