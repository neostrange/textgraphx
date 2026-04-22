import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp("The car bomb went off. Global warming is an issue. He set up the meeting. He let it down.")
for tok in doc:
    print(f"{tok.text} ({tok.pos_}): dep={tok.dep_}, head={tok.head.text}")
