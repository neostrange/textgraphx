with open("scripts/run_meantime_eval_cycle.sh", "r") as f:
    text = f.read()

text = text.replace('--out-json "$OUT_DIR/eval_report_strict.json" \\ \\', '--out-json "$OUT_DIR/eval_report_strict.json" \\')
text = text.replace('eval_report_strict.json" \\).read_text(encoding="utf-8"))', 'eval_report_strict.json").read_text(encoding="utf-8"))')

text = text.replace('--output "$OUT_DIR/eval_report_strict.json"\n  --normalize-nominal-boundaries', '--output "$OUT_DIR/eval_report_strict.json" \\\n  --normalize-nominal-boundaries')
text = text.replace('--output "$OUT_DIR/eval_report_relaxed.json"\n  --normalize-nominal-boundaries', '--output "$OUT_DIR/eval_report_relaxed.json" \\\n  --normalize-nominal-boundaries')

with open("scripts/run_meantime_eval_cycle.sh", "w") as f:
    f.write(text)
