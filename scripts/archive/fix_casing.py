with open('textgraphx/RefinementPhase.py', 'r') as f:
    text = f.read()
text = text.replace("['pro', 'nom']", "['PRO', 'NOM', 'pro', 'nom']")
with open('textgraphx/RefinementPhase.py', 'w') as f:
    f.write(text)
