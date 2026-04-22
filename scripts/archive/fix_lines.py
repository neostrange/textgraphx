with open("scripts/run_meantime_eval_cycle.sh", "r") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if line.strip() == "" and i > 0 and lines[i-1].strip().endswith("\\"):
        continue  # skip empty lines in the middle of a command
    new_lines.append(line)

with open("scripts/run_meantime_eval_cycle.sh", "w") as f:
    f.writelines(new_lines)
