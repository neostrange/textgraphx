import json
path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)
    print(list(data.keys()))
    if 'documents' in data:
        doc = data['documents'][0]
        print("Doc keys:", list(doc.keys()))
        if 'layers' in doc:
            layers = doc['layers']
            print("Layers keys:", list(layers.keys()))
            if 'entity' in layers:
                entity = layers['entity']
                print("Entity keys:", list(entity.keys()))
                if 'false_positives' in entity and len(entity['false_positives']) > 0:
                    print("Example FP:", entity['false_positives'][0])
                if 'false_negatives' in entity and len(entity['false_negatives']) > 0:
                    print("Example FN:", entity['false_negatives'][0])
