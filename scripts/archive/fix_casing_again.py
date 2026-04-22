with open('textgraphx/RefinementPhase.py', 'r') as f:
    text = f.read()
text = text.replace("['PRO', 'NOM', 'pro', 'nom']", "['PRO', 'NOM', 'pro', 'nom', 'NOMINAL', 'PRONOUN']")
with open('textgraphx/RefinementPhase.py', 'w') as f:
    f.write(text)
