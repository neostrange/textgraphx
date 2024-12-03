
class TagOccurrenceCreator:
    def __init__(self, nlp):
        self.nlp = nlp
        pass


    def create_tag_occurrences2(self, sentence, text_id, sentence_id):

        tag_occurrences = []
        for token in sentence:
            lexeme = self.nlp.vocab[token.text]
            # edited: included the punctuation as possible token candidates.
            #if not lexeme.is_punct and not lexeme.is_space:
            if not lexeme.is_space:
                tag_occurrence_id = str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx)
                tag_occurrence = {"id": tag_occurrence_id,
                                    "index": token.idx,
                                    "end_index": (len(token.text)+token.idx),
                                    "text": token.text,
                                    "lemma": token.lemma_,
                                    "pos": token.tag_,
                                    "upos": token.pos_,
                                    "tok_index_doc": token.i,
                                    "tok_index_sent": (token.i - sentence.start),
                                    "is_stop": (lexeme.is_stop or lexeme.is_punct or lexeme.is_space)}
                tag_occurrences.append(tag_occurrence)
        return tag_occurrences

    def create_tag_occurrences(self, sentence, text_id, sentence_id):
        tag_occurrences = []
        for token in sentence:
            lexeme = self.nlp.vocab[token.text]
            # edited: included the punctuation as possible token candidates.
            #if not lexeme.is_punct and not lexeme.is_space:
            if not lexeme.is_space:
                tag_occurrence_id = str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx)
                morph_features = {}
                for morph in token.morph:
                    key, value = morph.split("=")
                    morph_features[key] = value
                tag_occurrence = {
                    "id": tag_occurrence_id,
                    "index": token.idx,
                    "end_index": (len(token.text)+token.idx),
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.tag_,
                    "upos": token.pos_,
                    "tok_index_doc": token.i,
                    "tok_index_sent": (token.i - sentence.start),
                    "is_stop": (lexeme.is_stop or lexeme.is_punct or lexeme.is_space),
                }
                # Add morphological features as separate properties
                for key, value in morph_features.items():
                    tag_occurrence[key] = value
                tag_occurrences.append(tag_occurrence)
        return tag_occurrences