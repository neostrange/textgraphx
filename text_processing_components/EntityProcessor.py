class EntityProcessor:
    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository

    def process_entities(self, doc, text_id):
        nes = []
        i = 0
        spans = ''
        if doc.spans.get('ents_original') is not None:
            spans = list(doc.ents) + list(doc.spans['ents_original'])
        else:
            spans = list(doc.ents)
        # spans = filter_spans(spans) - just disabled it as testing dbpedia spotlight
        i += 1
        for entity in spans:
            if entity.kb_id_ != '':
                ne = {
                    'value': entity.text,
                    'type': entity.label_,
                    'start_index': entity.start_char,
                    'end_index': entity.end_char,
                    'kb_id': entity.kb_id_,
                    'url_wikidata': entity.kb_id_,
                    'score': entity._.dbpedia_raw_result['@similarityScore'],
                    'normal_term': entity.text,
                    'description': entity._.dbpedia_raw_result.get('@surfaceForm')
                }
            else:
                ne = {
                    'value': entity.text,
                    'type': entity.label_,
                    'start_index': entity.start_char,
                    'end_index': entity.end_char
                }

            nes.append(ne)
        self.store_entities(text_id, nes)
        return nes

    def store_entities(self, document_id, nes):
        ne_query = """
            UNWIND $nes as item
            MERGE (ne:NamedEntity {id: toString($documentId) + "_" + toString(item.start_index)+ "_" + toString(item.end_index)+ "_" + toString(item.type)})
            SET ne.type = item.type, ne.value = item.value, ne.index = item.start_index, ne.end_index = item.end_index,
            ne.kb_id = item.kb_id, ne.url_wikidata = item.url_wikidata, ne.score = item.score, ne.normal_term = item.normal_term, 
            ne.description = item.description
            WITH ne, item as neIndex
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
            WHERE text.id = $documentId AND tagOccurrence.index >= neIndex.start_index AND tagOccurrence.index < neIndex.end_index
            MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
        """
        self.execute_query(ne_query, {"documentId": document_id, "nes": nes})

    def execute_query(self, query, params):
        result = self.neo4j_repository.execute_query(query, params)
        return result