import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
import logging
logger = logging.getLogger(__name__)

class WordnetTokenEnricher:
    def __init__(self, neo4j_executor):
        """
        Initialize the TokenEnricher class.

        Args:
            neo4j_driver (Neo4jDriver): The Neo4j driver instance.
        """
        self.neo4j_executor = neo4j_executor
        self.wn_lemmatizer = WordNetLemmatizer()
        # Rough POS-specific reference depths for WordNet normalization.
        # Used to convert raw depth into a comparable abstraction score.
        self._pos_reference_depth = {
            "n": 20.0,
            "v": 14.0,
            "a": 10.0,
            "s": 10.0,
            "r": 8.0,
        }

    def assign_synset_info_to_tokens(self, doc_id):
        """
        Assign synset information to tokens in a document.

        Args:
            doc_id (str): The ID of the document.
        """
        # Step 1: Retrieve all Sentence nodes for the given AnnotatedText document
        query = """
        MATCH (d:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(s:Sentence)
        RETURN s.id AS sentence_id, s.text AS sentence_text
        """
        params = {"doc_id": doc_id}
        result = self.neo4j_executor.execute_query(query, params)

        for record in result:
            sentence_id = record["sentence_id"]
            sentence_text = record["sentence_text"]

            # Step 2: Retrieve the linked Token nodes for each Sentence node
            query = """
            MATCH (s:Sentence {id: $sentence_id})-[:HAS_TOKEN]->(t:TagOccurrence)
            RETURN t.id AS token_id, t.lemma AS token_lemma, t.nltkSynset AS nltkSynset, t.wnSynsetOffset AS wnSynsetOffset
            """
            params = {"sentence_id": sentence_id}
            token_result = self.neo4j_executor.execute_query(query, params)

            for token_record in token_result:
                token_id = token_record["token_id"]
                token_lemma = token_record.get("token_lemma")
                nltk_synset = token_record["nltkSynset"]

                if nltk_synset and nltk_synset != 'O':
                    try:
                        # Get synset information from WordNet
                        synset = wn.synset(nltk_synset)
                        synset_identifier = synset.name()
                        logger.debug("Found synset: %s", synset_identifier)
                        lemma, pos, sense_num = synset_identifier.split('.')
                        wn_synset_offset = synset.offset()
                        wn_synset_offset = str(wn_synset_offset) + pos
                        wn_lexname = synset.lexname()

                        # Get hypernyms, synonyms, and domain labels for the synset
                        hypernyms = self.get_all_hypernyms(synset)
                        synonyms = self.get_synonyms(synset)
                        domain_labels = self.get_domain_labels(synset)
                        derivational_forms, derivational_eventive_verbs = self.get_derivational_features(
                            synset,
                            token_lemma=token_lemma or lemma,
                        )
                        entails, causes = self.get_verb_relation_features(synset)
                        depth_min, depth_max, abstraction_level = self.get_depth_features(synset)

                        # Update the Token node in Neo4j with synset-related information
                        update_query = """
                        MATCH (t:TagOccurrence {id: $token_id})
                        SET t.hypernyms = $hypernyms, t.wn31SynsetOffset = $wn31SynsetOffset, t.synonyms = $synonyms, t.domain_labels = $domain_labels,
                            t.wnLexname = $wnLexname,
                            t.wnDerivationalForms = $wnDerivationalForms,
                            t.wnDerivationalEventiveVerbs = $wnDerivationalEventiveVerbs,
                            t.wnEntails = $wnEntails,
                            t.wnCauses = $wnCauses,
                            t.wnDepthMin = $wnDepthMin,
                            t.wnDepthMax = $wnDepthMax,
                            t.wnAbstractionLevel = $wnAbstractionLevel
                        """
                        params = {
                            "token_id": token_id,
                            "hypernyms": hypernyms,
                            "synonyms": synonyms,
                            "domain_labels": domain_labels,
                            "wn31SynsetOffset": wn_synset_offset,
                            "wnLexname": wn_lexname,
                            "wnDerivationalForms": derivational_forms,
                            "wnDerivationalEventiveVerbs": derivational_eventive_verbs,
                            "wnEntails": entails,
                            "wnCauses": causes,
                            "wnDepthMin": depth_min,
                            "wnDepthMax": depth_max,
                            "wnAbstractionLevel": abstraction_level,
                        }
                        self.neo4j_executor.execute_query(update_query, params)
                    except Exception as e:
                        logger.exception("Synset not found for token_id: %s. Skipping processing.", token_id)
                else:
                    # This is a noisy, expected condition when offsets are missing; log at DEBUG level
                    # so it can be enabled when troubleshooting without flooding INFO logs.
                    logger.debug("Synset offset 'O' or empty for token_id: %s. Skipping processing.", token_id)
    def get_all_hypernyms(self, synset):
        """
        Get all hypernyms for a given synset.

        Args:
            synset (Synset): The synset.

        Returns:
            list: A list of hypernyms.
        """
        hypernyms = []
        hypernym_synsets = synset.hypernyms()
        for hypernym_synset in hypernym_synsets:
            hypernyms.append(hypernym_synset.name())  # Store hypernym synset name
            hypernyms.extend(self.get_all_hypernyms(hypernym_synset))  # Recursive call to get hypernyms of hypernyms
        return hypernyms

    def get_synonyms(self, synset):
        """
        Get all synonyms for a given synset.

        Args:
            synset (Synset): The synset.

        Returns:
            list: A list of synonyms.
        """
        synonyms = []
        for lemma in synset.lemmas():
            synonyms.append(lemma.name())  # Store synonym
        return synonyms

    def get_domain_labels(self, synset):
        """
        Get all domain labels for a given synset.

        Args:
            synset (Synset): The synset.

        Returns:
            list: A list of domain labels.
        """
        domain_labels = []
        lexname = synset.lexname()

        # Extract the domain label from the lexical name if present
        if "." in lexname:
            domain_labels.append(lexname.split(".")[0])

        return domain_labels

    def _normalize_lemma(self, value):
        v = str(value or "").strip().lower().replace("_", " ")
        return " ".join(v.split())

    def _lemma_similarity(self, a, b):
        """Cheap lexical similarity in [0,1] for noise filtering."""
        a_n = self._normalize_lemma(a)
        b_n = self._normalize_lemma(b)
        if not a_n or not b_n:
            return 0.0
        if a_n == b_n:
            return 1.0
        if a_n in b_n or b_n in a_n:
            return 0.9

        a_parts = set(a_n.split())
        b_parts = set(b_n.split())
        overlap = len(a_parts & b_parts)
        union = len(a_parts | b_parts)
        token_jaccard = float(overlap) / float(union) if union else 0.0

        a_chars = set(a_n)
        b_chars = set(b_n)
        char_union = len(a_chars | b_chars)
        char_jaccard = float(len(a_chars & b_chars)) / float(char_union) if char_union else 0.0

        return max(token_jaccard, char_jaccard)

    def get_derivational_features(self, synset, token_lemma=""):
        """Return derivationally related forms and eventive-verb subset.

        This is useful for bridging nominal mentions to eventive verb concepts,
        which strengthens event-centric KG construction.
        """
        forms = set()
        scored_eventive_verbs = []
        token_lemma_n = self._normalize_lemma(token_lemma)

        for lemma in synset.lemmas():
            for rel in lemma.derivationally_related_forms():
                try:
                    rel_name = rel.name()
                except Exception:
                    continue
                if not rel_name:
                    continue
                forms.add(rel_name)

                try:
                    rel_synset = rel.synset()
                    if rel_synset.pos() == "v":
                        # Keep only reasonably lexical-aligned derivations.
                        rel_score = self._lemma_similarity(token_lemma_n, rel_name)
                        if rel_score >= 0.45:
                            scored_eventive_verbs.append((rel_synset.name(), rel_score))
                except Exception:
                    continue

        # Deterministic top-k to reduce noisy long tails.
        scored_eventive_verbs = sorted(
            scored_eventive_verbs,
            key=lambda x: (x[1], x[0]),
            reverse=True,
        )[:5]
        eventive_verbs = [syn_name for syn_name, _ in scored_eventive_verbs]

        return sorted(forms), eventive_verbs

    def get_verb_relation_features(self, synset):
        """Return verb entailment and causal relation synset names."""
        entails = []
        causes = []
        try:
            entails = [s.name() for s in synset.entailments()]
        except Exception:
            entails = []
        try:
            causes = [s.name() for s in synset.causes()]
        except Exception:
            causes = []
        return sorted(set(entails)), sorted(set(causes))

    def get_depth_features(self, synset):
        """Return min/max depth and an abstraction score in [0, 1].

        Higher abstraction score indicates a concept closer to the ontology
        root (more general); lower score indicates more specific concepts.
        """
        try:
            min_depth = int(synset.min_depth())
            max_depth = int(synset.max_depth())
        except Exception:
            return 0, 0, 0.0

        if max_depth <= 0:
            return min_depth, max_depth, 0.0

        pos = ""
        try:
            pos = synset.pos()
        except Exception:
            pos = ""
        ref_depth = self._pos_reference_depth.get(pos, 20.0)
        specificity = min(float(max_depth), ref_depth) / ref_depth
        abstraction = 1.0 - specificity
        abstraction = max(0.0, min(1.0, abstraction))
        return min_depth, max_depth, round(abstraction, 4)