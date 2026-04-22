import json

with open("textgraphx/schema/ontology.json", "r") as f:
    ontology = json.load(f)

allowed_pairs = ontology["relation_endpoint_contract"]["REFERS_TO"]["allowed_pairs"]
if ["Antecedent", "NamedEntity"] not in allowed_pairs:
    allowed_pairs.append(["Antecedent", "NamedEntity"])
if ["Antecedent", "EntityMention"] not in allowed_pairs:
    allowed_pairs.append(["Antecedent", "EntityMention"]) # Just in case

with open("textgraphx/schema/ontology.json", "w") as f:
    json.dump(ontology, f, indent=2)
    f.write("\n")
print("done")
