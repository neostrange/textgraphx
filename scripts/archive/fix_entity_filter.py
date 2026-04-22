import re

with open('textgraphx/RefinementPhase.py', 'r') as f:
    text = f.read()

text = re.sub(r"\[\'pro\', \'nom\'\]", "['pro', 'nom', 'NOMINAL', 'PRONOUN']", text)

with open('textgraphx/RefinementPhase.py', 'w') as f:
    f.write(text)
