"""MEANTIME-oriented evaluation utilities.

This module normalizes gold annotations and pipeline outputs into a shared
representation, then computes precision/recall/F1 with strict and relaxed span
matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
import hashlib
import logging
import re


from typing import Dict, Any, List, Tuple, Optional, Sequence
import spacy
try:
    _eval_nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
except Exception:
    _eval_nlp = None


import xml.etree.ElementTree as ET

from textgraphx.evaluation.metrics import precision_recall_f1

try:
    from nltk.corpus import wordnet as _wn  # type: ignore
except Exception:
    _wn = None


TokenSpan = Tuple[int, ...]

LOGGER = logging.getLogger(__name__)

_AUXILIARY_EVENT_LEMMAS = frozenset(
    {
        "be",
        "am",
        "is",
        "are",
        "was",
        "were",
        "been",
        "being",
        "do",
        "does",
        "did",
        "done",
        "have",
        "has",
        "had",
        "will",
        "would",
        "shall",
        "should",
        "can",
        "could",
        "may",
        "might",
        "must",
    }
)


@dataclass(frozen=True)
class Mention:
    """Normalized mention with token-anchored span and selected attributes."""

    kind: str
    span: TokenSpan
    attrs: Tuple[Tuple[str, str], ...] = ()

    def with_attrs(self, keys: Iterable[str]) -> "Mention":
        keep = set(keys)
        return Mention(
            kind=self.kind,
            span=self.span,
            attrs=tuple(sorted((k, v) for k, v in self.attrs if k in keep)),
        )


@dataclass(frozen=True)
class Relation:
    """Normalized binary relation between two mention-like endpoints."""

    kind: str
    source_kind: str
    source_span: TokenSpan
    target_kind: str
    target_span: TokenSpan
    attrs: Tuple[Tuple[str, str], ...] = ()


@dataclass
class NormalizedDocument:
    """Schema-neutral document used for scoring."""

    doc_id: str
    entity_mentions: Set[Mention] = field(default_factory=set)
    event_mentions: Set[Mention] = field(default_factory=set)
    timex_mentions: Set[Mention] = field(default_factory=set)
    relations: Set[Relation] = field(default_factory=set)
    token_sequence: Tuple[Tuple[int, str], ...] = ()

    def layer(self, name: str) -> Set[Mention]:
        if name == "entity":
            return self.entity_mentions
        if name == "event":
            return self.event_mentions
        if name == "timex":
            return self.timex_mentions
        raise ValueError(f"Unknown layer: {name}")


@dataclass(frozen=True)
class EvaluationMapping:
    """Configurable mapping for schema-tolerant evaluation behavior."""

    mention_attr_keys: Dict[str, Tuple[str, ...]] = field(
        default_factory=lambda: {
            # Keep entity strict matching focused on comparable MEANTIME fields.
            # `ent_class` is an internal/enrichment attribute and is often absent in gold.
            "entity": ("syntactic_type",),
            # external_ref is a transport/internal identifier and is intentionally
            # excluded from scoring keys to avoid strict-mode false mismatches.
            "event": ("pos", "tense", "aspect", "certainty", "polarity", "time", "pred"),
            # `functionInDocument` is often inconsistent between DCT inference paths
            # and in-text mentions; keep strict matching centered on stable timex identity.
            "timex": ("type", "value"),
        }
    )
    relation_attr_keys: Dict[str, Tuple[str, ...]] = field(
        default_factory=lambda: {
            "tlink": ("reltype",),
            "glink": ("reltype",),
            "has_participant": ("sem_role",),
        }
    )


def _sorted_span(raw: Iterable[int]) -> TokenSpan:
    vals = sorted({int(v) for v in raw})
    return tuple(vals)


def _attrs_from_element(el: ET.Element, keys: Iterable[str]) -> Tuple[Tuple[str, str], ...]:
    out = []
    for k in keys:
        v = (el.get(k) or "").strip()
        if v:
            out.append((k, v))
    return tuple(sorted(out))


def _span_from_element(el: ET.Element) -> TokenSpan:
    anchors = [a.get("t_id") for a in el.findall("token_anchor")]
    tok_ids = [int(a) for a in anchors if a and str(a).isdigit()]
    return _sorted_span(tok_ids)


def parse_meantime_xml(xml_path: str) -> NormalizedDocument:
    """Parse a MEANTIME-style annotation XML into a normalized document."""
    root = ET.parse(xml_path).getroot()
    doc_id = str(root.get("doc_id") or "")

    token_sequence: list[Tuple[int, str]] = []
    for tok in root.findall("token"):
        raw_id = (tok.get("t_id") or "").strip()
        if not raw_id.isdigit():
            continue
        token_sequence.append((int(raw_id), (tok.text or "").strip()))

    doc = NormalizedDocument(doc_id=doc_id, token_sequence=tuple(token_sequence))
    mention_by_id: Dict[str, Mention] = {}

    markables = root.find("Markables")
    if markables is None:
        return doc

    for el in markables:
        tag = el.tag
        m_id = (el.get("m_id") or "").strip()
        span = _span_from_element(el)
        if not m_id or not span:
            continue

        if tag == "ENTITY_MENTION":
            mention = Mention(
                kind="entity",
                span=span,
                attrs=_attrs_from_element(el, ("syntactic_type", "ent_class")),
            )
            doc.entity_mentions.add(mention)
            mention_by_id[m_id] = mention
        elif tag == "EVENT_MENTION":
            mention = Mention(
                kind="event",
                span=span,
                attrs=_attrs_from_element(
                    el,
                    ("pos", "tense", "aspect", "certainty", "polarity", "time", "factuality", "pred", "external_ref"),
                ),
            )
            doc.event_mentions.add(mention)
            mention_by_id[m_id] = mention
        elif tag == "TIMEX3":
            mention = Mention(
                kind="timex",
                span=span,
                attrs=_canonicalize_timex_attrs(
                    {
                        "type": el.get("type"),
                        "value": el.get("value"),
                        "functionInDocument": el.get("functionInDocument"),
                        "anchorTimeID": el.get("anchorTimeID"),
                        "beginPoint": el.get("beginPoint"),
                        "endPoint": el.get("endPoint"),
                    }
                ),
            )
            doc.timex_mentions.add(mention)
            mention_by_id[m_id] = mention

    relations = root.find("Relations")
    if relations is None:
        return doc

    for rel in relations:
        if rel.tag not in {"TLINK", "GLINK", "CLINK", "SLINK", "HAS_PARTICIPANT"}:
            continue

        sources = [s.get("m_id") for s in rel.findall("source") if s.get("m_id")]
        targets = [t.get("m_id") for t in rel.findall("target") if t.get("m_id")]
        if not sources or not targets:
            continue

        relation_attrs: Tuple[Tuple[str, str], ...] = ()
        if rel.tag == "TLINK":
            relation_attrs = _attrs_from_element(rel, ("reltype",))
        elif rel.tag == "GLINK":
            relation_attrs = _attrs_from_element(rel, ("reltype",))
        elif rel.tag == "CLINK":
            relation_attrs = _attrs_from_element(rel, ("reltype", "source"))
        elif rel.tag == "SLINK":
            relation_attrs = _attrs_from_element(rel, ("reltype", "source"))
        elif rel.tag == "HAS_PARTICIPANT":
            relation_attrs = _attrs_from_element(rel, ("sem_role",))

        for src_id in sources:
            src = mention_by_id.get(str(src_id))
            if src is None:
                continue
            for tgt_id in targets:
                tgt = mention_by_id.get(str(tgt_id))
                if tgt is None:
                    continue
                doc.relations.add(
                    Relation(
                        kind=rel.tag.lower(),
                        source_kind=src.kind,
                        source_span=src.span,
                        target_kind=tgt.kind,
                        target_span=tgt.span,
                        attrs=relation_attrs,
                    )
                )

    return doc


def _mention_attrs_map(m: Mention) -> Dict[str, str]:
    return {str(k): str(v) for k, v in m.attrs}


def _mention_syntactic_type(attrs: Dict[str, str]) -> str:
    return str(attrs.get("syntactic_type") or attrs.get("syntacticType") or "").strip().upper()


def apply_nominal_precision_filters(doc: NormalizedDocument) -> NormalizedDocument:
    """Apply precision-first nominal filters to predicted entity mentions.

    Rules:
    1) Pronoun leak: pronouns must be PRO, never NOM.
    2) Salience gate: NOM must be event-participant or coref/refers-connected.
    3) Abstract noun drop: remove NOM with generic abstract wn lexname classes.
    """

    pron_pos_tags = {"PRP", "PRP$", "WP", "WDT"}
    pronoun_words = {
        "i", "me", "my", "mine", "we", "us", "our", "ours",
        "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
        "it", "its", "they", "them", "their", "theirs",
        "who", "whom", "whose", "which", "that", "this", "these", "those",
    }
    abstract_lexnames = {"noun.quantity", "noun.attribute", "noun.relation"}

    token_lookup = {int(tid): _normalize_token_text(text) for tid, text in (doc.token_sequence or ())}

    participant_entity_spans: Set[TokenSpan] = set()
    coref_or_refers_entity_spans: Set[TokenSpan] = set()
    for rel in doc.relations:
        kind = str(rel.kind or "").strip().lower()
        if kind == "has_participant" and rel.target_kind == "entity":
            participant_entity_spans.add(rel.target_span)
        if kind in {"coref", "refers_to"}:
            if rel.source_kind == "entity":
                coref_or_refers_entity_spans.add(rel.source_span)
            if rel.target_kind == "entity":
                coref_or_refers_entity_spans.add(rel.target_span)

    filtered: Set[Mention] = set()
    for mention in doc.entity_mentions:
        attrs = _mention_attrs_map(mention)
        syntactic_type = _mention_syntactic_type(attrs)

        # Keep non-nominals untouched (except pronoun leak correction for NOM).
        if syntactic_type not in {"NOM", "NOMINAL"}:
            filtered.add(mention)
            continue

        # Rule 1: pronoun leak guard.
        head_pos = str(attrs.get("head_pos") or attrs.get("pos") or "").strip().upper()
        upos = str(attrs.get("upos") or "").strip().upper()
        span_tokens = [token_lookup.get(int(i), "") for i in mention.span]
        alpha_tokens = [t for t in span_tokens if t]
        looks_pronoun = bool(alpha_tokens) and all(t in pronoun_words for t in alpha_tokens)
        if head_pos in pron_pos_tags or upos == "PRON" or looks_pronoun:
            continue

        # Rule 2: salience gate (must participate in event structure or discourse linkage).
        salient = (mention.span in participant_entity_spans) or (mention.span in coref_or_refers_entity_spans)
        if not salient:
            continue

        # Rule 3: abstract noun drop.
        wn_lexname = str(attrs.get("head_wn_lexname") or attrs.get("wn_lexname") or "").strip().lower()
        if wn_lexname in abstract_lexnames:
            continue

        filtered.add(mention)

    doc.entity_mentions = filtered
    return doc


def build_document_from_neo4j(
    graph: Any,
    doc_id: int | str,
    gold_token_sequence: Optional[Tuple[Tuple[int, str], ...]] = None,
    discourse_only: bool = False,
    normalize_nominal_boundaries: bool = True,
    gold_like_nominal_filter: bool = False,
    nominal_profile_mode: str = "all",
    include_non_core_participants: bool = False,
    non_core_participant_roles: Optional[Sequence[str]] = None,
) -> NormalizedDocument:
    """Extract mention/relation projections for a document from Neo4j.

    When ``discourse_only=True`` the entity projection is restricted to
    :DiscourseEntity-labelled NamedEntity nodes stamped by
    ``tag_discourse_relevant_entities``. This produces an evaluation scope
    closer to MEANTIME's entity annotation policy. Event projection remains
    unchanged in discourse-only mode.

    The :DiscourseEntity labels are stamped by RefinementPhase rule
    ``tag_discourse_relevant_entities``.  Running with ``discourse_only=True``
    on a graph where that rule has not yet executed will return an empty entity
    set; re-run the pipeline first.

    Participant relation projection is core-only by default (``is_core=true``).
    Set ``include_non_core_participants=True`` to include non-core participant
    links for aggressive recall-oriented analysis.

    Optionally provide ``non_core_participant_roles`` to constrain non-core
    links to a role allowlist (for example ``["ARG0", "ARG1"]``). Core links
    are always retained.
    """
    doc_id_int = _resolve_graph_doc_id(graph, doc_id)
    profile_mode = str(nominal_profile_mode or "all").strip().lower()
    allowed_profile_modes = {"all", "eventive", "salient", "candidate-gold", "background"}
    if profile_mode not in allowed_profile_modes:
        raise ValueError(
            f"Unsupported nominal_profile_mode: {nominal_profile_mode}. "
            f"Expected one of: {sorted(allowed_profile_modes)}"
        )

    non_core_role_allowlist = tuple(
        sorted({str(role).strip().upper() for role in (non_core_participant_roles or ()) if str(role).strip()})
    )

    doc = NormalizedDocument(doc_id=str(doc_id))
    token_index_alignment = _build_token_index_alignment(
        graph=graph,
        doc_id=doc_id_int,
        gold_token_sequence=gold_token_sequence,
    )
    gold_token_lookup = {
        int(tid): _normalize_token_text(text)
        for tid, text in (gold_token_sequence or ())
    }

    _entity_discourse_clause = (
        "AND m:DiscourseEntity"
        if discourse_only
        else ""
    )
    entity_rows = graph.run(
        f"""
        MATCH (:AnnotatedText {{id: $doc_id}})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
        MATCH (tok)-[:IN_MENTION|PARTICIPATES_IN]->(m)
        WHERE (m:EntityMention OR m:NamedEntity OR m:NominalMention OR m:CorefMention OR m:Entity OR m:Concept) {_entity_discourse_clause}
           AND NOT coalesce(m.stale, false)
           WITH m,
               min(tok.tok_index_doc) AS start_tok,
               max(tok.tok_index_doc) AS end_tok,
               head(collect(tok)) AS head_tok
        RETURN DISTINCT start_tok, end_tok,
             elementId(m) AS node_id,
             coalesce(m.syntactic_type, m.syntacticType) AS syntactic_type,
                            CASE WHEN m:NominalMention OR m:CorefMention THEN true ELSE false END AS is_nominal_mention,
                            coalesce(m.nominalEvalStartTok, m.start_tok) AS eval_start_tok,
                            coalesce(m.nominalEvalEndTok, m.end_tok) AS eval_end_tok,
               coalesce(m.ent_class, m.entClass) AS ent_class,
             coalesce(m.nominalSemanticHeadTokenIndex, m.headTokenIndex, end_tok) AS head_token_index,
               coalesce(m.nominalHeadPos, head_tok.pos, '') AS head_pos,
               coalesce(head_tok.upos, '') AS upos,
               coalesce(m.nominalHeadWnLexname, head_tok.wnLexname, '') AS wn_lexname
        ORDER BY start_tok, end_tok
        """,
        {"doc_id": doc_id_int},
    ).data()
    
    extracted_entity_spans = set()
    for row in entity_rows:
        span_range = tuple(range(int(row["start_tok"]), int(row["end_tok"]) + 1))
        extracted_entity_spans.add(span_range)

    doc._extracted_entity_spans = extracted_entity_spans

    for row in entity_rows:
        span = _span_from_bounds(int(row["start_tok"]), int(row["end_tok"]), token_index_alignment)
        head_pos = str(row.get("head_pos") or "").strip().upper()
        upos = str(row.get("upos") or "").strip().upper()
        syntactic_type = str(row.get("syntactic_type") or "")
        if not syntactic_type:
            if head_pos in {"PRP", "PRP$", "WP", "WP$"} or upos == "PRON":
                syntactic_type = "PRO"
            elif head_pos in {"NNP", "NNPS"}:
                syntactic_type = "NAM"
            elif head_pos in {"NN", "NNS"}:
                syntactic_type = "NOM"
        if syntactic_type.upper() == "NOMINAL":
            syntactic_type = "NOM"

        # Evaluation projection hygiene: keep only MEANTIME-target entity syntactic classes.
        syntactic_type_upper = syntactic_type.upper().strip()
        if syntactic_type_upper == "NOMINAL":
            syntactic_type_upper = "NOM"
            syntactic_type = "NOM"
        if syntactic_type_upper not in {"NAM", "NOM", "PRO", "APP", "PRE.NOM"}:
            continue

        # Strict NOM alignment: only project NOM mentions from explicit mention-layer nominals.
        # TEMPORARILY DISABLED: if syntactic_type.upper() in {"NOM", "NOMINAL"} and not bool(row.get("is_nominal_mention", False)): continue

        head_token_index = row.get("head_token_index")
        head_idx = _int_or_none(head_token_index)
        # Compute gold-space aligned head index for all entity types.
        # head_token_index is in Neo4j token space; token_index_alignment maps it to gold space.
        aligned_head_idx = token_index_alignment.get(head_idx, head_idx) if head_idx is not None else None
        is_nominal = syntactic_type.upper() in {"NOM", "NOMINAL"}
        nominal_features: Dict[str, Any] = {}

        if is_nominal:
            eval_start = _int_or_none(row.get("eval_start_tok"))
            eval_end = _int_or_none(row.get("eval_end_tok"))
            if eval_start is not None and eval_end is not None and eval_start <= eval_end:
                span = _span_from_bounds(eval_start, eval_end, token_index_alignment)

            nominal_original_span = span

            nominal_features = _nominal_projection_features(
                graph=graph,
                doc_id=doc_id_int,
                node_id=row.get("node_id"),
                fallback_head_idx=head_idx if head_idx is not None else int(row["end_tok"]),
            )
            # Priority 1: anchor NOM projection around semantic head (fallback: surface head).
            span = _project_nominal_span_around_head(
                span=span,
                aligned_head_idx=aligned_head_idx,
                gold_token_lookup=gold_token_lookup,
            )
            if normalize_nominal_boundaries:
                span = _normalize_nominal_entity_span_for_eval(span, gold_token_lookup)

            # Guard against over-collapsing candidate-gold nominals to head-only spans.
            nominal_wider_span = nominal_original_span
            if normalize_nominal_boundaries:
                nominal_wider_span = _normalize_nominal_entity_span_for_eval(nominal_wider_span, gold_token_lookup)
            if _should_restore_wider_nominal_span(
                projected_span=span,
                original_span=nominal_wider_span,
                features=nominal_features,
                gold_token_lookup=gold_token_lookup,
            ):
                span = nominal_wider_span

            if not span:
                continue
            # Priority 2: drop background/temporal/quantified nominal noise at projection-time.
            if _is_obvious_nominal_projection_noise(span, nominal_features, gold_token_lookup):
                continue

        if gold_like_nominal_filter and is_nominal:
            if nominal_features.get("eventive_head", False) or _is_wordnet_eventive_noun(nominal_features):
                continue
            if _looks_like_proper_name_span(span, gold_token_lookup) or str(nominal_features.get("head_pos") or "") in {"NNP", "NNPS"}:
                syntactic_type = "NAM"
            else:
                cluster_size = int(nominal_features.get("mention_cluster_size", 0))
                has_named_link = bool(nominal_features.get("has_named_link", False))
                has_core_argument = bool(nominal_features.get("has_core_argument", False))
                if cluster_size <= 1 and not has_named_link and not has_core_argument:
                    continue

        if profile_mode != "all" and is_nominal:
            eval_profile = str(nominal_features.get("nominal_eval_profile") or "").strip().lower()
            candidate_gold = bool(nominal_features.get("nominal_eval_candidate_gold", False))
            eventive = bool(nominal_features.get("eventive_head", False)) or _is_wordnet_eventive_noun(nominal_features)
            salient = bool(nominal_features.get("is_salient_nominal", False))
            if not salient:
                salient = bool(nominal_features.get("has_named_link", False)) or (
                    bool(nominal_features.get("has_core_argument", False))
                    and float(nominal_features.get("nominal_eventive_confidence", 0.0)) >= 0.40
                )
            include_nominal = True
            if profile_mode == "eventive":
                include_nominal = eventive or eval_profile == "eventive_nominal"
            elif profile_mode == "salient":
                include_nominal = salient or eval_profile == "salient_nominal"
            elif profile_mode == "candidate-gold":
                include_nominal = candidate_gold
            elif profile_mode == "background":
                include_nominal = (eval_profile == "background_nominal") and not eventive
            if not include_nominal:
                continue

        attrs = ()
        ent_class = str(row.get("ent_class") or "").strip().upper()
        wn_lexname = str(row.get("wn_lexname") or "").strip().lower()
        attrs_list = []
        if syntactic_type:
            attrs_list.append(("syntactic_type", syntactic_type))
        if ent_class:
            attrs_list.append(("ent_class", ent_class))
        if head_pos:
            attrs_list.append(("head_pos", head_pos))
        if upos:
            attrs_list.append(("upos", upos))
        if wn_lexname:
            attrs_list.append(("wn_lexname", wn_lexname))
        # Store gold-space (aligned) head token index so _head_span_match comparisons
        # work correctly against gold spans (which are also in gold token space).
        if aligned_head_idx is not None:
            attrs_list.append(("head_token_index", str(aligned_head_idx)))
        elif head_token_index is not None:
            attrs_list.append(("head_token_index", str(head_token_index)))
        if attrs_list:
            attrs = tuple(sorted(attrs_list))
            
        priority = 0
        if syntactic_type == "NAM":
            priority = 2 if not bool(row.get("is_nominal_mention")) else 1
        elif syntactic_type == "NOM":
            priority = 2 if bool(row.get("is_nominal_mention")) else 1
            
        # Temporarily store to deduplicate after loop
        if not hasattr(doc, "_temp_entity_list"):
            doc._temp_entity_list = []
        doc._temp_entity_list.append((priority, len(span), Mention(kind="entity", span=span, attrs=attrs)))

    # Deduplicate overlapping entity mentions (choose highest priority, then shortest span)
    if hasattr(doc, "_temp_entity_list"):
        doc._temp_entity_list.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        seen_tokens = set()
        for _, _, mention in doc._temp_entity_list:
            span_tokens = set(mention.span)
            if not span_tokens.intersection(seen_tokens):
                doc.entity_mentions.add(mention)
                seen_tokens.update(span_tokens)
        delattr(doc, "_temp_entity_list")

    event_rows = graph.run(
        """
         CALL {
             WITH $doc_id AS doc_id
             MATCH (m:EventMention)
                         OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(m_tok:TagOccurrence)-[:IN_MENTION]->(m)
             WITH m, doc_id, count(m_tok) > 0 AS token_scoped
             WHERE (m.doc_id = doc_id OR token_scoped)
               AND m.start_tok IS NOT NULL AND m.end_tok IS NOT NULL
               AND coalesce(m.low_confidence, false) = false
               
             OPTIONAL MATCH (m)<-[:IN_MENTION]-(head_tok:TagOccurrence)
             WITH m, head_tok, doc_id
             ORDER BY case when toLower(head_tok.lemma) = toLower(m.pred) then 1 else 2 end, head_tok.tok_index_doc ASC
             WITH m, doc_id, head(collect(head_tok)) AS best_head
             RETURN DISTINCT coalesce(best_head.tok_index_doc, m.start_tok) AS start_tok,
                 coalesce(best_head.tok_index_doc, m.end_tok) AS end_tok,
                 m.pos AS pos, m.tense AS tense, m.aspect AS aspect,
                 m.certainty AS certainty, m.polarity AS polarity,
                 m.time AS time, m.factuality AS factuality, m.pred AS pred,
                 coalesce(m.external_ref, m.externalRef) AS external_ref,
                 2 AS source_priority
             UNION
             WITH $doc_id AS doc_id
             MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:TRIGGERS]->(m:TEvent)
                         WHERE coalesce(m.low_confidence, false) = false
                             
                             AND NOT EXISTS {
                                     MATCH (em:EventMention)-[:REFERS_TO]->(m)
                                                                         WHERE (em.doc_id = doc_id OR EXISTS {
                                                                                         MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:IN_MENTION]->(em)
                                                                                     })
                                                                                 AND em.start_tok IS NOT NULL
                                         AND em.end_tok IS NOT NULL
                                         AND coalesce(em.low_confidence, false) = false
                             }
             OPTIONAL MATCH (f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(m)
             WITH m, min(tok.tok_index_doc) AS trig_start, max(tok.tok_index_doc) AS trig_end, head(collect(f.headword)) AS pred
             RETURN DISTINCT coalesce(m.start_tok, trig_start) AS start_tok,
                 coalesce(m.end_tok, trig_end) AS end_tok,
                 m.pos AS pos, m.tense AS tense, m.aspect AS aspect,
                 m.certainty AS certainty, m.polarity AS polarity,
                 m.time AS time, m.factuality AS factuality, pred AS pred,
                 coalesce(m.external_ref, m.externalRef, m.eid, m.eiid) AS external_ref,
                 1 AS source_priority
                         UNION
                         WITH $doc_id AS doc_id
                         MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(f:Frame)
                         WITH DISTINCT f
                         WHERE f.start_tok IS NOT NULL AND f.end_tok IS NOT NULL
                             AND NOT EXISTS {
                                     MATCH (ev:TEvent)
                                     WHERE ev.start_tok = f.start_tok
                                         AND ev.end_tok = f.end_tok
                             }
                         RETURN DISTINCT f.start_tok AS start_tok,
                                 f.end_tok AS end_tok,
                                 'VERB' AS pos,
                                 '' AS tense,
                                 '' AS aspect,
                                 '' AS certainty,
                                 '' AS polarity,
                                 '' AS time,
                                 '' AS factuality,
                                 f.headword AS pred,
                                 '' AS external_ref,
                                 0 AS source_priority
         }
         WITH start_tok, end_tok, pos, tense, aspect, certainty, polarity, time, factuality, pred, external_ref, source_priority
         WHERE start_tok IS NOT NULL AND end_tok IS NOT NULL
         RETURN DISTINCT start_tok, end_tok, pos, tense, aspect, certainty, polarity, time, factuality, pred, external_ref, source_priority
         ORDER BY start_tok, end_tok, source_priority DESC
        """,
        {"doc_id": doc_id_int},
    ).data()

    # Prefer mention-layer rows over canonical fallbacks when both map to the same span.
    # This avoids duplicate-span projections that inflate spurious event mentions.
    event_by_span: Dict[TokenSpan, Tuple[int, Mention]] = {}
    for row in event_rows:
        span = _span_from_bounds(int(row["start_tok"]), int(row["end_tok"]), token_index_alignment)
        attrs = _canonicalize_event_attrs(row)
        pred = dict(attrs).get("pred", "").lower()
        if not _should_project_event(attrs):
            continue
            
        if len(span) > 1 and pred:
            best_idx = span[-1]
            for idx in span:
                tok_text = gold_token_lookup.get(int(idx), "").lower()
                tok_lemma = _eval_nlp(tok_text)[0].lemma_.lower() if _eval_nlp else tok_text
                if tok_text == pred or tok_lemma == pred:
                    best_idx = idx
                    break
            span = (best_idx,)
            
        mention = Mention(kind="event", span=span, attrs=attrs)
        priority = int(row.get("source_priority") or 0)
        current = event_by_span.get(span)
        if current is None or (priority, len(attrs)) > (current[0], len(current[1].attrs)):
            event_by_span[span] = (priority, mention)

    doc.event_mentions.update(m for _, m in event_by_span.values())
    projected_event_spans = frozenset(m.span for m in doc.event_mentions)

    timex_rows = graph.run(
        """
        MATCH (m:TIMEX)
        WHERE m.doc_id = $doc_id
           OR EXISTS {
               MATCH (tm:TimexMention)-[:REFERS_TO]->(m)
               WHERE tm.doc_id = $doc_id
           }
           OR EXISTS {
               MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(:TimexMention)-[:REFERS_TO]->(m)
           }
           OR EXISTS {
               MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(m)
           }
        OPTIONAL MATCH (tm:TimexMention)-[:REFERS_TO]->(m)
        WHERE tm.doc_id = $doc_id
        OPTIONAL MATCH (tok:TagOccurrence)-[:TRIGGERS]->(tm)
        WITH m, tm, min(tok.tok_index_doc) AS trig_start, max(tok.tok_index_doc) AS trig_end
        OPTIONAL MATCH (a:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok2:TagOccurrence)
                WHERE coalesce(tm.start_char, tm.start_index, tm.begin, m.start_char, m.start_index, m.begin) IS NOT NULL
                    AND coalesce(tm.end_char, tm.end_index, tm.end, m.end_char, m.end_index, m.end) IS NOT NULL
                    AND toInteger(tok2.index) >= toInteger(coalesce(tm.start_char, tm.start_index, tm.begin, m.start_char, m.start_index, m.begin))
                    AND toInteger(tok2.end_index) <= toInteger(coalesce(tm.end_char, tm.end_index, tm.end, m.end_char, m.end_index, m.end))
        WITH m,
             tm,
             trig_start,
             trig_end,
             min(tok2.tok_index_doc) AS span_start,
             max(tok2.tok_index_doc) AS span_end
        WITH coalesce(tm.start_tok, trig_start, span_start, m.start_tok) AS start_tok,
             coalesce(tm.end_tok, trig_end, span_end, m.end_tok) AS end_tok,
             m,
             tm
        WHERE start_tok IS NOT NULL AND end_tok IS NOT NULL
        RETURN DISTINCT start_tok, end_tok,
             coalesce(tm.type, m.type) AS type,
             coalesce(tm.value, m.value) AS value,
             coalesce(tm.functionInDocument, m.functionInDocument) AS functionInDocument,
             coalesce(tm.anchorTimeID, m.anchorTimeID) AS anchorTimeID,
             coalesce(tm.beginPoint, m.beginPoint) AS beginPoint,
             coalesce(tm.endPoint, m.endPoint) AS endPoint
        ORDER BY start_tok, end_tok
        """,
        {"doc_id": doc_id_int},
    ).data()
    for row in timex_rows:
        span = _span_from_bounds(int(row["start_tok"]), int(row["end_tok"]), token_index_alignment)
        attrs = _canonicalize_timex_attrs(
            {
                "type": row.get("type"),
                "value": row.get("value"),
                "functionInDocument": row.get("functionInDocument"),
                "anchorTimeID": row.get("anchorTimeID"),
                "beginPoint": row.get("beginPoint"),
                "endPoint": row.get("endPoint"),
            }
        )
        doc.timex_mentions.add(Mention(kind="timex", span=span, attrs=attrs))

    tlink_rows = graph.run(
        """
            MATCH (a)-[r:TLINK]->(b)
                WHERE (a.doc_id = toInteger($doc_id) OR a.id STARTS WITH $doc_id + '_' OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION|IN_FRAME|FRAME_DESCRIBES_EVENT|DESCRIBES*0..2]-(a)
                            })
                    AND (b.doc_id = toInteger($doc_id) OR b.id STARTS WITH $doc_id + '_' OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION|IN_FRAME|FRAME_DESCRIBES_EVENT|DESCRIBES*0..2]-(b)
                            })
              OPTIONAL MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(a_tok:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION|IN_FRAME|FRAME_DESCRIBES_EVENT|DESCRIBES*0..2]-(a)
              OPTIONAL MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(b_tok:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION|IN_FRAME|FRAME_DESCRIBES_EVENT|DESCRIBES*0..2]-(b)
              WITH a, b, r,
                  min(a_tok.tok_index_doc) AS a_tok_start,
                  max(a_tok.tok_index_doc) AS a_tok_end,
                  min(b_tok.tok_index_doc) AS b_tok_start,
                  max(b_tok.tok_index_doc) AS b_tok_end
              WITH labels(a) AS source_labels,
                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,
                  r
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
        RETURN source_labels,
                a_start AS a_start, a_end AS a_end,
                target_labels,
                b_start AS b_start, b_end AS b_end,
               r.relType AS reltype
        """,
        {"doc_id": doc_id_int},
    ).data()
    LOGGER.debug("doc %s tlink_rows count: %s", doc_id, len(tlink_rows))
    for row in tlink_rows:
        src_kind = _node_kind_from_labels(row.get("source_labels", []))
        tgt_kind = _node_kind_from_labels(row.get("target_labels", []))

        if src_kind is None or tgt_kind is None:
            LOGGER.debug("TLINK skip src/tgt kind None: src=%s tgt=%s", src_kind, tgt_kind)
            continue
        src_span = _span_from_bounds(int(row["a_start"]), int(row["a_end"]), token_index_alignment)
        tgt_span = _span_from_bounds(int(row["b_start"]), int(row["b_end"]), token_index_alignment)

        if src_kind == "event":
            src_span = _align_relation_event_span(src_span, doc.event_mentions)
        if tgt_kind == "event":
            tgt_span = _align_relation_event_span(tgt_span, doc.event_mentions)
        if src_kind == "timex":
            src_span = _align_relation_timex_span(src_span, doc.timex_mentions)
        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)

        if (src_kind == "event" and src_span not in projected_event_spans) or (tgt_kind == "event" and tgt_span not in projected_event_spans):
            continue

        LOGGER.debug(
            "ADDING TLINK: src=%s:%s tgt=%s:%s rel=%s",
            src_kind,
            src_span,
            tgt_kind,
            tgt_span,
            row.get("reltype"),
        )
        doc.relations.add(
            Relation(
                kind="tlink",
                source_kind=src_kind,
                source_span=src_span,
                target_kind=tgt_kind,
                target_span=tgt_span,
                attrs=(("reltype", str(row.get("reltype") or "")),),
            )
        )

    glink_rows = graph.run(
        """
            MATCH (a)-[r:GLINK]->(b)
                WHERE (a.doc_id = $doc_id OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(a)
                            })
                    AND (b.doc_id = $doc_id OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(b)
                            })
              OPTIONAL MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(a_tok:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(a)
              OPTIONAL MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(b_tok:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(b)
              WITH a, b, r,
                  min(a_tok.tok_index_doc) AS a_tok_start,
                  max(a_tok.tok_index_doc) AS a_tok_end,
                  min(b_tok.tok_index_doc) AS b_tok_start,
                  max(b_tok.tok_index_doc) AS b_tok_end
              WITH labels(a) AS source_labels,
                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,
                  r
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
           RETURN source_labels,
                a_start, a_end,
                target_labels,
                b_start, b_end,
               r.relType AS reltype
        """,
        {"doc_id": doc_id_int},
    ).data()
    for row in glink_rows:
        src_kind = _node_kind_from_labels(row.get("source_labels", []))
        tgt_kind = _node_kind_from_labels(row.get("target_labels", []))
        if src_kind is None or tgt_kind is None:
            continue
        src_span = _span_from_bounds(int(row["a_start"]), int(row["a_end"]), token_index_alignment)
        tgt_span = _span_from_bounds(int(row["b_start"]), int(row["b_end"]), token_index_alignment)
        if src_kind == "event":
            src_span = _align_relation_event_span(src_span, doc.event_mentions)
            pass
        if tgt_kind == "event":
            tgt_span = _align_relation_event_span(tgt_span, doc.event_mentions)
            pass
        if src_kind == "timex":
            src_span = _align_relation_timex_span(src_span, doc.timex_mentions)
            pass
        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
            pass
        if (src_kind == "event" and src_span not in projected_event_spans) or (tgt_kind == "event" and tgt_span not in projected_event_spans):
            continue
        doc.relations.add(
            Relation(
                kind="glink",
                source_kind=src_kind,
                source_span=src_span,
                target_kind=tgt_kind,
                target_span=tgt_span,
                attrs=(('reltype', str(row.get('reltype') or '')),),
            )
        )

    clink_slink_rows = graph.run(
        """
            MATCH (a)-[r:CLINK|SLINK]->(b)
                WHERE (a.doc_id = $doc_id OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(a)
                            })
                    AND (b.doc_id = $doc_id OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(b)
                            })
              OPTIONAL MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(a_tok:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(a)
              OPTIONAL MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(b_tok:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN|IN_MENTION]->(b)
              WITH a, b, r,
                  min(a_tok.tok_index_doc) AS a_tok_start,
                  max(a_tok.tok_index_doc) AS a_tok_end,
                  min(b_tok.tok_index_doc) AS b_tok_start,
                  max(b_tok.tok_index_doc) AS b_tok_end
              WITH labels(a) AS source_labels,
                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,
                  r
              WHERE a_start IS NOT NULL AND a_end IS NOT NULL
                AND b_start IS NOT NULL AND b_end IS NOT NULL
        RETURN type(r) AS rel_kind,
                source_labels,
                a_start, a_end,
                target_labels,
                b_start, b_end,
               coalesce(r.relType, '') AS reltype,
               coalesce(r.source, '') AS source
        """,
        {"doc_id": doc_id_int},
    ).data()
    for row in clink_slink_rows:
        src_kind = _node_kind_from_labels(row.get("source_labels", []))
        tgt_kind = _node_kind_from_labels(row.get("target_labels", []))
        if src_kind is None or tgt_kind is None:
            continue
        src_span = _span_from_bounds(int(row["a_start"]), int(row["a_end"]), token_index_alignment)
        tgt_span = _span_from_bounds(int(row["b_start"]), int(row["b_end"]), token_index_alignment)
        if src_kind == "event":
            src_span = _align_relation_event_span(src_span, doc.event_mentions)
        if tgt_kind == "event":
            tgt_span = _align_relation_event_span(tgt_span, doc.event_mentions)
        if src_kind == "timex":
            src_span = _align_relation_timex_span(src_span, doc.timex_mentions)
        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
        if (src_kind == "event" or tgt_kind == "event") and not projected_event_spans:
            continue
        rel_kind = str(row.get("rel_kind") or "").strip().lower()
        attrs = []
        reltype = str(row.get("reltype") or "").strip()
        source = str(row.get("source") or "").strip()
        if reltype:
            attrs.append(("reltype", reltype))
        if source:
            attrs.append(("source", source))
        doc.relations.add(
            Relation(
                kind=rel_kind,
                source_kind=src_kind,
                source_span=src_span,
                target_kind=tgt_kind,
                target_span=tgt_span,
                attrs=tuple(attrs),
            )
        )

    participant_rows = graph.run(
        """
        CALL {
            WITH $doc_id AS doc_id
            MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt)
              WHERE (evt:TEvent OR evt:EventMention)
                AND (
                    coalesce(r.is_core, true) = true
                    OR (
                        $include_non_core_participants
                        AND (
                            $non_core_role_filter_empty
                            OR toUpper(coalesce(r.type, '')) IN $non_core_participant_roles
                        )
                    )
                )
                AND (evt.doc_id = doc_id
               OR EXISTS {
                   MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|IN_MENTION]->(evt)
               })
            WITH src AS endpoint, evt, r, doc_id
            OPTIONAL MATCH (evt_m:EventMention)-[:REFERS_TO]->(evt)
            WITH endpoint, evt, r, doc_id, coalesce(evt_m, evt) as evt_m
            OPTIONAL MATCH (evt_m)<-[:IN_MENTION|TRIGGERS]-(evt_head_tok:TagOccurrence)
            WITH endpoint, evt, r, doc_id, evt_m, evt_head_tok
            ORDER BY case when toLower(evt_head_tok.lemma) = toLower(evt_m.pred) then 1 else 2 end, evt_head_tok.tok_index_doc ASC
            WITH endpoint, evt, r, doc_id, evt_m, head(collect(evt_head_tok)) AS best_evt_head
            WITH endpoint, evt, r, doc_id, coalesce(best_evt_head.tok_index_doc, evt_m.start_tok, evt.start_tok) AS evt_tok_start, coalesce(best_evt_head.tok_index_doc, evt_m.end_tok, evt.end_tok) AS evt_tok_end
            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN|IN_MENTION]->(endpoint)
            WITH endpoint, evt, r,
                 coalesce(endpoint.start_tok, min(src_tok.tok_index_doc)) AS src_start,
                 coalesce(endpoint.end_tok, max(src_tok.tok_index_doc)) AS src_end,
                  evt_tok_start,
                  evt_tok_end,
                 labels(endpoint) AS source_labels
              WITH source_labels, src_start, src_end,
                  coalesce(evt.start_tok, evt_tok_start) AS evt_start,
                  coalesce(evt.end_tok, evt_tok_end) AS evt_end,
                  r, endpoint
              WHERE src_start IS NOT NULL AND src_end IS NOT NULL
                AND evt_start IS NOT NULL AND evt_end IS NOT NULL
              RETURN DISTINCT src_start, src_end, evt_start, evt_end,
                   coalesce(r.type, '') AS sem_role,
                   source_labels, elementId(endpoint) AS endpoint_id
        }
        RETURN DISTINCT src_start, src_end, evt_start, evt_end, sem_role, source_labels, endpoint_id
        ORDER BY evt_start, src_start
        """,
        {
            "doc_id": doc_id_int,
            "include_non_core_participants": bool(include_non_core_participants),
            "non_core_participant_roles": list(non_core_role_allowlist),
            "non_core_role_filter_empty": len(non_core_role_allowlist) == 0,
        },
    ).data()
    LOGGER.debug("doc %s participant_rows count: %s", doc_id, len(participant_rows))
    for row in participant_rows:
        src_kind = _node_kind_from_labels(row.get("source_labels", []))
        if src_kind != "entity":
            LOGGER.debug("Skipping participant (src_kind != entity): labels=%s -> %s", row.get("source_labels"), src_kind)
            continue
        evt_span = _span_from_bounds(int(row["evt_start"]), int(row["evt_end"]), token_index_alignment)
        evt_span = _align_relation_event_span(evt_span, doc.event_mentions)
        if evt_span not in projected_event_spans:
            LOGGER.debug(
                "Skipping participant (evt_span not projected): original=%s-%s aligned=%s",
                row["evt_start"],
                row["evt_end"],
                evt_span,
            )
            continue
        entity_span = _span_from_bounds(int(row["src_start"]), int(row["src_end"]), token_index_alignment)
        entity_span = _align_relation_entity_span(entity_span, doc.entity_mentions)
        sem_role = _normalize_sem_role(row.get("sem_role"))
        LOGGER.debug("ADDING has_participant: event=%s entity=%s role=%s", evt_span, entity_span, sem_role)
        doc.relations.add(
            Relation(
                kind="has_participant",
                source_kind="event",
                source_span=evt_span,
                target_kind="entity",
                target_span=entity_span,
                attrs=(("sem_role", sem_role),),
            )
        )

    return doc


def _node_kind_from_labels(labels: Iterable[str]) -> Optional[str]:
    s = set(labels)
    if "TIMEX" in s or "TimexMention" in s:
        return "timex"
    if "EventMention" in s or "TEvent" in s:
        return "event"
    if "EntityMention" in s or "NamedEntity" in s or "NominalMention" in s or "CorefMention" in s or "Entity" in s or "Concept" in s:
        return "entity"
    return None


def _normalize_event_pos(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    if raw in {"VERB", "NOUN", "OTHER"}:
        return raw
    if raw.startswith("VB"):
        return "VERB"
    if raw.startswith("NN"):
        return "NOUN"
    return "OTHER"


def _canonicalize_event_attrs(row: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
    """Normalize event attrs toward MEANTIME strict comparison semantics."""
    pos = _normalize_event_pos(row.get("pos"))
    raw_pred = str(row.get("pred") or "").strip().lower()
    
    # Use spaCy for robust evaluation lemmatization matching the MEANTIME root forms
    pred = raw_pred
    if _eval_nlp and pred:
        pred = _eval_nlp(pred)[0].lemma_
        if pred == "-PRON-":
            pred = raw_pred
        
    tense = str(row.get("tense") or "").strip().upper() or "NONE"
    aspect = str(row.get("aspect") or "").strip().upper() or "NONE"
    
    if tense == "PASTPART":
        tense = "PAST"
        
    if raw_pred.endswith("ing") and tense == "NONE" and pos == "VERB":
        tense = "PRESPART"

    certainty = str(row.get("certainty") or "").strip().upper() or "CERTAIN"
    factuality = str(row.get("factuality") or "").strip().upper()
    external_ref = str(row.get("external_ref") or "").strip()
    polarity = str(row.get("polarity") or "").strip().upper() or "POS"
    time = str(row.get("time") or "").strip().upper() or "NON_FUTURE"

    # MEANTIME convention: INFINITIVE-tense events are projected to
    # certainty=POSSIBLE / time=FUTURE regardless of the raw stored values.
    if tense == "INFINITIVE":
        certainty = "POSSIBLE"
        time = "FUTURE"

    attrs_map: Dict[str, str] = {}
    if pos:
        attrs_map["pos"] = pos
    if pred:
        attrs_map["pred"] = pred

    if pos == "NOUN":
        # Gold nouns almost never have tense/aspect in MEANTIME (unless explicitly expressed).
        # To avoid penalizing correctly bounded Noun Events simply because they lack 'NONE' explicitly:
        pass  # Omit tense and aspect for Noun Events entirely.
    else:
        if tense and tense != "O":
            attrs_map["tense"] = tense
        if aspect and aspect != "O":
            attrs_map["aspect"] = aspect

    attrs_map["certainty"] = certainty
    attrs_map["polarity"] = polarity
    if time and time != "O":
        attrs_map["time"] = time
        
    if factuality:
        attrs_map["factuality"] = factuality
    if external_ref:
        attrs_map["external_ref"] = external_ref
        
    return tuple(sorted(attrs_map.items()))




def _should_project_event(attrs: Tuple[Tuple[str, str], ...]) -> bool:
    for k, v in attrs:
        if k == "pred" and v in _AUXILIARY_EVENT_LEMMAS:
            return False
    return True
    
def _canonicalize_timex_attrs(row: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
    """Normalize TIMEX attrs toward MEANTIME strict comparison semantics."""
    typ = str(row.get("type") or "").strip().upper()
    value = str(row.get("value") or "").strip()
    function_in_document = str(row.get("functionInDocument") or "").strip() or "NONE"
    anchor_time_id = str(row.get("anchorTimeID") or "").strip()
    begin_point = str(row.get("beginPoint") or "").strip()
    end_point = str(row.get("endPoint") or "").strip()

    if typ == "DATE":
        value = _normalize_timex_date_value(value)

    attrs_map: Dict[str, str] = {}
    if typ:
        attrs_map["type"] = typ
    if value:
        attrs_map["value"] = value
    if function_in_document:
        attrs_map["functionInDocument"] = function_in_document
    if anchor_time_id:
        attrs_map["anchorTimeID"] = anchor_time_id
    if begin_point:
        attrs_map["beginPoint"] = begin_point
    if end_point:
        attrs_map["endPoint"] = end_point
    return tuple(sorted(attrs_map.items()))


def _resolve_graph_doc_id(graph: Any, doc_id: int | str) -> int | str:
    doc_str = str(doc_id).strip()
    try:
        doc_int = int(doc_id)
    except (TypeError, ValueError):
        doc_int = None

    rows = graph.run(
        """
        MATCH (a:AnnotatedText)
        WHERE ($doc_int IS NOT NULL AND a.id = $doc_int)
           OR toString(a.id) = $doc_str
           OR toString(a.publicId) = $doc_str
        RETURN a.id AS id
        ORDER BY CASE WHEN toString(a.publicId) = $doc_str THEN 0 ELSE 1 END,
                 CASE WHEN toString(a.id) = $doc_str THEN 0 ELSE 1 END
        LIMIT 1
        """,
        {"doc_int": doc_int, "doc_str": doc_str},
    ).data()
    if rows:
        return rows[0].get("id")
    return doc_int if doc_int is not None else doc_id


def _normalize_token_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_timex_date_value(value: str) -> str:
    """Normalize common textual date formats to ISO-like strings when possible."""
    v = str(value or "").strip()
    if not v:
        return ""

    if len(v) == 8 and v.isdigit():
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    if len(v) == 6 and v.isdigit():
        return f"{v[0:4]}-{v[4:6]}"
    if len(v) == 7 and v.isdigit():
        return f"{v[0:4]}-{v[4:6]}-{v[6]}"

    month_map = {
        "january": "01", "jan": "01",
        "february": "02", "feb": "02",
        "march": "03", "mar": "03",
        "april": "04", "apr": "04",
        "may": "05",
        "june": "06", "jun": "06",
        "july": "07", "jul": "07",
        "august": "08", "aug": "08",
        "september": "09", "sep": "09", "sept": "09",
        "october": "10", "oct": "10",
        "november": "11", "nov": "11",
        "december": "12", "dec": "12",
    }

    compact = re.sub(r"\s+", " ", v.replace(",", " ")).strip()

    # Month Day Year, e.g. "August 10 2007".
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2})\s+(\d{4})", compact)
    if m:
        mon = month_map.get(m.group(1).lower())
        if mon:
            day = int(m.group(2))
            year = m.group(3)
            return f"{year}-{mon}-{day:02d}"

    # Day Month Year, e.g. "10 August 2007".
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", compact)
    if m:
        mon = month_map.get(m.group(2).lower())
        if mon:
            day = int(m.group(1))
            year = m.group(3)
            return f"{year}-{mon}-{day:02d}"

    # Month Year, e.g. "August 2007".
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{4})", compact)
    if m:
        mon = month_map.get(m.group(1).lower())
        if mon:
            year = m.group(2)
            return f"{year}-{mon}"

    # Year Month, e.g. "2007 August".
    m = re.fullmatch(r"(\d{4})\s+([A-Za-z]+)", compact)
    if m:
        mon = month_map.get(m.group(2).lower())
        if mon:
            year = m.group(1)
            return f"{year}-{mon}"

    return v


def _normalize_nominal_entity_span_for_eval(
    span: TokenSpan,
    gold_token_lookup: Dict[int, str],
) -> TokenSpan:
    """Trim leading determiners and trailing punctuation for nominal eval.

    This normalization is applied only in evaluator projection and does not
    mutate graph data.
    """
    if not span:
        return span

    leading_determiners = {
        "the", "a", "an", "this", "that", "these", "those",
    }
    trailing_punct = {
        ".", ",", ":", ";", "'", '"', "`", "''", "``", "!", "?",
    }

    items = list(span)
    while items:
        first = gold_token_lookup.get(int(items[0]), "").lower()
        if first in leading_determiners:
            items.pop(0)
            continue
        break

    while items:
        last = gold_token_lookup.get(int(items[-1]), "").lower()
        if last in trailing_punct:
            items.pop()
            continue
        break

    return tuple(items)


def _project_nominal_span_around_head(
    span: TokenSpan,
    aligned_head_idx: Optional[int],
    gold_token_lookup: Dict[int, str],
) -> TokenSpan:
    """Project NOM mentions to the immediate noun phrase around the semantic head."""
    if not span:
        return span

    tokens = sorted(int(i) for i in span)
    if not tokens:
        return span

    if aligned_head_idx is None:
        head_idx = tokens[-1]
    elif aligned_head_idx in tokens:
        head_idx = int(aligned_head_idx)
    else:
        head_idx = min(tokens, key=lambda t: abs(int(t) - int(aligned_head_idx)))

    punct = {".", ",", ":", ";", "'", '"', "`", "''", "``", "!", "?", "(", ")", "[", "]", "{", "}"}
    hard_left = {
        "that", "which", "who", "whom", "whose",
        "because", "if", "when", "while", "although", "though", "but", "and", "or",
        "to", "of", "in", "on", "at", "for", "from", "by", "with", "as", "than", "into", "onto",
    }
    trailing_pp_prep = {"of", "in", "on", "at", "for", "from", "by", "to", "into", "onto", "over", "under", "across"}
    weak_heads = {
        "the", "a", "an", "this", "that", "these", "those",
        "my", "your", "his", "her", "its", "our", "their",
        "i", "we", "you", "he", "she", "it", "they", "me", "us", "him", "them",
    }
    leading_drop = {
        "the", "a", "an", "this", "that", "these", "those",
        "any", "some", "many", "much", "few", "several", "both", "either", "neither", "another", "other",
    }

    head_pos = tokens.index(head_idx)
    head_word = gold_token_lookup.get(head_idx, "").lower()
    if head_word in weak_heads:
        for t in tokens[head_pos + 1:]:
            w = gold_token_lookup.get(t, "").lower()
            if w and w not in weak_heads and w not in punct and w not in trailing_pp_prep:
                head_idx = t
                head_pos = tokens.index(head_idx)
                break

    left = head_pos
    right = head_pos

    while left - 1 >= 0:
        w = gold_token_lookup.get(tokens[left - 1], "").lower()
        if not w or w in punct or w in hard_left:
            break
        left -= 1

    while right + 1 < len(tokens):
        w = gold_token_lookup.get(tokens[right + 1], "").lower()
        if not w or w in punct or w in hard_left:
            break
        right += 1

    projected = tokens[left:right + 1]

    # MEANTIME strict NOM spans usually exclude trailing PP tails.
    if len(projected) > 2:
        hp = projected.index(head_idx)
        cut = None
        for i in range(hp + 1, len(projected)):
            if gold_token_lookup.get(projected[i], "").lower() in trailing_pp_prep:
                cut = i
                break
        if cut is not None and cut > hp:
            projected = projected[:cut]

    while projected and gold_token_lookup.get(projected[0], "").lower() in leading_drop and projected[0] != head_idx:
        projected.pop(0)

    return tuple(projected) if projected else (head_idx,)


def _is_obvious_nominal_projection_noise(
    span: TokenSpan,
    features: Dict[str, Any],
    gold_token_lookup: Dict[int, str],
) -> bool:
    """Drop non-entity NOM noise (temporal/quantified/background low-salience)."""
    eval_profile = str(features.get("nominal_eval_profile") or "").strip().lower()
    candidate_gold = bool(features.get("nominal_eval_candidate_gold", False))
    salient = bool(features.get("has_named_link", False)) or bool(features.get("has_core_argument", False)) or int(features.get("mention_cluster_size", 0)) > 1
    eventive = bool(features.get("eventive_head", False)) or _is_wordnet_eventive_noun(features)

    toks = [gold_token_lookup.get(int(i), "") for i in span]
    text = " ".join(t for t in toks if t)
    if not text:
        return False

    temporal_words = {
        "today", "yesterday", "tomorrow", "tonight", "morning", "afternoon", "evening",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "week", "month", "year", "day", "hour", "minute", "second",
    }
    lowered = {t.lower() for t in toks if t}
    temporal_like = bool(lowered & temporal_words)
    quantified_like = any(ch.isdigit() for ch in text) or any(sym in text for sym in ["$", "€", "£", "¥", "%"])

    if temporal_like or quantified_like:
        return True

    # Keep background discourse nominals; only suppress clearly eventive noise.
    if eventive and not candidate_gold and not salient and eval_profile != "salient_nominal":
        return True

    return False


def _should_restore_wider_nominal_span(
    projected_span: TokenSpan,
    original_span: TokenSpan,
    features: Dict[str, Any],
    gold_token_lookup: Dict[int, str],
) -> bool:
    """Restore wider nominal span when head-projection is clearly over-collapsed."""
    if not projected_span or not original_span:
        return False
    if len(original_span) <= len(projected_span):
        return False
    if len(projected_span) > 2 or len(original_span) < 4:
        return False
    if not bool(features.get("nominal_eval_candidate_gold", False)):
        return False

    support = bool(features.get("has_core_argument", False)) or bool(features.get("has_named_link", False))
    if not support:
        return False

    # Do not widen across obvious punctuation breaks.
    punct = {".", ",", ":", ";", "!", "?", "(", ")", "[", "]", "{", "}"}
    tokens = [gold_token_lookup.get(int(i), "") for i in original_span]
    if any(t in punct for t in tokens if t):
        return False
    return True


def _looks_like_proper_name_span(span: TokenSpan, gold_token_lookup: Dict[int, str]) -> bool:
    words = [gold_token_lookup.get(int(i), "") for i in span]
    words = [w for w in words if w and any(ch.isalpha() for ch in w)]
    if not words:
        return False
    if len(words) == 1:
        return False
    titled = sum(1 for w in words if w[:1].isupper())
    return (titled / len(words)) >= 0.8


def _nominal_projection_features(
    graph: Any,
    doc_id: int | str,
    node_id: str,
    fallback_head_idx: int,
) -> Dict[str, Any]:
    rows = graph.run(
        """
        MATCH (m)
        WHERE elementId(m) = $node_id
        OPTIONAL MATCH (ht:TagOccurrence)-[:IN_MENTION]->(m)
                WHERE ht.tok_index_doc = coalesce(m.nominalSemanticHeadTokenIndex, m.headTokenIndex, $fallback_head_idx)
        WITH m, head(collect(ht)) AS head_tok
                WITH m, head_tok,
                         size([(head_tok)-[:TRIGGERS]->(:TEvent {doc_id: $doc_id}) | 1]) > 0 AS trigger_eventive
        OPTIONAL MATCH (m)-[:REFERS_TO]->(e:Entity)<-[:REFERS_TO]-(other:EntityMention)
        WHERE other <> m
                WITH m, head_tok, trigger_eventive, count(DISTINCT other) AS mention_cluster_size
         OPTIONAL MATCH (arg_tok:TagOccurrence)-[:IN_MENTION]->(m)
         OPTIONAL MATCH (arg_tok)-[:IN_FRAME]->(fa:FrameArgument)
                 WITH m, head_tok, trigger_eventive, mention_cluster_size,
              count(DISTINCT CASE WHEN fa.type IN ['ARG0', 'ARG1', 'ARG2'] THEN fa END) AS core_arg_hits
         OPTIONAL MATCH (m)-[:REFERS_TO]->(e2:Entity)<-[:REFERS_TO]-(ne:NamedEntity)
                     RETURN coalesce(m.nominalHeadPos, head_tok.pos, '') AS head_pos,
                             coalesce(m.nominalHeadNltkSynset, head_tok.nltkSynset, '') AS head_nltk_synset,
                             coalesce(m.nominalHeadHypernyms, head_tok.hypernyms, []) AS head_hypernyms,
                             coalesce(m.nominalHeadWnLexname, head_tok.wnLexname, '') AS head_wn_lexname,
                             (coalesce(m.nominalEventiveHead, false)
                                OR coalesce(m.nominalEventiveByWordNet, false)
                                OR coalesce(m.nominalEventiveByTrigger, false)
                                OR coalesce(m.nominalEventiveByArgumentStructure, false)
                                OR coalesce(m.nominalEventiveByMorphology, false)
                                OR trigger_eventive) AS eventive_head,
                             mention_cluster_size AS mention_cluster_size,
             count(DISTINCT ne) > 0 AS has_named_link,
                         core_arg_hits > 0 AS has_core_argument,
                         coalesce(m.nominalEvalProfile, '') AS nominal_eval_profile,
                         coalesce(m.nominalEvalCandidateGold, false) AS nominal_eval_candidate_gold,
                         coalesce(m.nominalEventiveConfidence, 0.0) AS nominal_eventive_confidence,
                         coalesce(m.isSalientNominal, false) AS is_salient_nominal
        """,
        {
            "node_id": node_id,
            "doc_id": doc_id,
            "fallback_head_idx": fallback_head_idx,
        },
    ).data()
    if not rows:
        return {
            "head_pos": "",
            "head_nltk_synset": "",
            "head_hypernyms": [],
            "head_wn_lexname": "",
            "eventive_head": False,
            "mention_cluster_size": 0,
            "has_named_link": False,
            "has_core_argument": False,
            "nominal_eval_profile": "",
            "nominal_eval_candidate_gold": False,
            "nominal_eventive_confidence": 0.0,
        }
    return rows[0]


@lru_cache(maxsize=4096)
def _wordnet_lexname(nltk_synset: str) -> str:
    if not nltk_synset or nltk_synset == "O" or _wn is None:
        return ""
    try:
        return str(_wn.synset(nltk_synset).lexname() or "")
    except Exception:
        return ""


def _is_wordnet_eventive_noun(features: Dict[str, Any]) -> bool:
    """Return True when head token WordNet metadata indicates eventive noun."""
    target_lex = {
        "noun.act",
        "noun.event",
        "noun.process",
        "noun.phenomenon",
        "noun.state",
    }

    lexname = str(features.get("head_wn_lexname") or "").strip()
    synset = str(features.get("head_nltk_synset") or "").strip()
    if not lexname:
        lexname = _wordnet_lexname(synset)
    if lexname in target_lex:
        return True

    # Fallback: use persisted hypernyms if synset cannot be resolved at runtime.
    eventive_hypernym_roots = ("event.n.", "act.n.", "process.n.")
    hypernyms = features.get("head_hypernyms") or []
    for h in hypernyms:
        hs = str(h or "").strip().lower()
        if hs.startswith(eventive_hypernym_roots):
            return True
    return False


def _build_token_index_alignment(
    graph: Any,
    doc_id: int | str,
    gold_token_sequence: Optional[Tuple[Tuple[int, str], ...]],
) -> Dict[int, int]:
    if not gold_token_sequence:
        return {}

    pred_rows = graph.run(
        """
        MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
        RETURN tok.tok_index_doc AS idx, tok.text AS text
        ORDER BY idx
        """,
        {"doc_id": doc_id},
    ).data()
    if not pred_rows:
        return {}

    pred_seq = [(_normalize_token_text(str(r.get("text") or "")), int(r.get("idx"))) for r in pred_rows if r.get("idx") is not None]
    gold_seq = [(_normalize_token_text(text), int(tid)) for tid, text in gold_token_sequence]
    if not pred_seq or not gold_seq:
        return {}

    pred_norm = [t for t, _ in pred_seq]
    gold_norm = [t for t, _ in gold_seq]
    sm = SequenceMatcher(a=pred_norm, b=gold_norm, autojunk=False)

    mapping: Dict[int, int] = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            continue
        for offset in range(i2 - i1):
            pred_idx = pred_seq[i1 + offset][1]
            gold_tid = gold_seq[j1 + offset][1]
            mapping[pred_idx] = gold_tid
    return mapping


def _span_from_bounds(start_tok: int, end_tok: int, alignment: Dict[int, int]) -> TokenSpan:
    mapped = [alignment.get(i) for i in range(start_tok, end_tok + 1) if alignment.get(i) is not None]
    if mapped:
        return _sorted_span(range(min(mapped), max(mapped) + 1))
    return _sorted_span(range(start_tok, end_tok + 1))


def _align_relation_event_span(span: TokenSpan, mentions: Set[Mention]) -> TokenSpan:
    if not span or not mentions: return span
    mention_spans = [m.span for m in mentions if m.kind == "event"]
    if not mention_spans: return span
    if span in mention_spans: return span
    overlapping = [s for s in mention_spans if set(span).intersection(s)]
    if overlapping: return max(overlapping, key=lambda s: len(set(span).intersection(s)))
    return span

def _align_relation_entity_span(span: TokenSpan, mentions: Set[Mention]) -> TokenSpan:
    if not span or not mentions: return span
    mention_spans = [m.span for m in mentions if m.kind == "entity"]
    if not mention_spans: return span
    if span in mention_spans: return span
    overlapping = [s for s in mention_spans if set(span).intersection(s)]
    if overlapping: return max(overlapping, key=lambda s: len(set(span).intersection(s)))
    return span

def _align_relation_timex_span(span: TokenSpan, mentions: Set[Mention]) -> TokenSpan:
    if not span or not mentions: return span
    mention_spans = [m.span for m in mentions if m.kind in {"timex", "timex3"}]
    if not mention_spans: return span
    if span in mention_spans: return span
    overlapping = [s for s in mention_spans if set(span).intersection(s)]
    if overlapping: return max(overlapping, key=lambda s: len(set(span).intersection(s)))
    return span


def _normalize_sem_role(raw: Any) -> str:
    """Normalize PropBank-like role strings to gold-comparable casing."""
    value = str(raw or "").strip()
    if not value:
        return ""

    upper = value.upper()
    if upper.startswith("ARGM-"):
        return "Argm-" + upper[5:]
    if upper.startswith("ARG"):
        return "Arg" + upper[3:]
    return value


def _span_iou(a: TokenSpan, b: TokenSpan) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return float(len(sa & sb)) / float(len(sa | sb)) if (sa or sb) else 0.0


def _mention_attrs_dict(m: Mention) -> Dict[str, str]:
    return {str(k): str(v) for k, v in m.attrs}


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    sval = str(value).strip()
    if not sval:
        return None
    try:
        return int(sval)
    except ValueError:
        return None


def _mention_head_indices(m: Mention) -> Set[int]:
    attrs = _mention_attrs_dict(m)
    indices: Set[int] = set()
    for key in (
        "nominalSemanticHeadTokenIndex",
        "nominal_semantic_head_token_index",
        "headTokenIndex",
        "head_token_index",
    ):
        parsed = _int_or_none(attrs.get(key))
        if parsed is not None:
            indices.add(parsed)
    if not indices and m.span:
        # Gold mentions rarely carry explicit head index; use right edge as fallback.
        indices.add(int(max(m.span)))
    return indices


def _is_nominal_mention(m: Mention) -> bool:
    """Return True for NOM/NOMINAL or APP mentions — both benefit from head-span relaxation."""
    attrs = _mention_attrs_dict(m)
    stype = str(attrs.get("syntactic_type") or attrs.get("syntacticType") or "").strip().upper()
    return stype in {"NOM", "NOMINAL", "APP"}


def _is_conj_mention(m: Mention) -> bool:
    """Return True for CONJ (conjunction) entity mentions."""
    attrs = _mention_attrs_dict(m)
    stype = str(attrs.get("syntactic_type") or attrs.get("syntacticType") or "").strip().upper()
    return stype == "CONJ"


def _apply_conj_virtual_merge(
    matched: Set[Tuple["Mention", "Mention"]],
    unmatched_gold: Set["Mention"],
    coverage_threshold: float = 0.5,
) -> Set["Mention"]:
    """Remove unmatched CONJ gold mentions whose token span is already covered.

    MEANTIME CONJ mentions (e.g. "India, China and Britain") span all conjuncts.
    The pipeline generates individual conjunct predictions (NAM/NOM per conjunct).
    Those individual predictions match the gold NAM/NOM sub-mentions, leaving the
    parent CONJ gold unmatched as a False Negative.  This function removes those
    CONJ gold mentions from the unmatched set when ``coverage_threshold`` fraction
    of their token span is already covered by the matched predicted mentions.
    """
    if not unmatched_gold:
        return unmatched_gold

    # Tokens already covered by matched predictions.
    covered_tokens: Set[int] = set()
    for _, pred in matched:
        covered_tokens.update(pred.span)

    virtually_matched: Set["Mention"] = set()
    for g in unmatched_gold:
        if not _is_conj_mention(g):
            continue
        if not g.span:
            continue
        overlap = len(set(g.span) & covered_tokens)
        if overlap / len(g.span) >= coverage_threshold:
            virtually_matched.add(g)

    return unmatched_gold - virtually_matched


def _head_span_match(g: Mention, p: Mention) -> bool:
    gold_heads = _mention_head_indices(g)
    pred_heads = _mention_head_indices(p)
    if any(idx in set(g.span) for idx in pred_heads):
        return True
    if any(idx in set(p.span) for idx in gold_heads):
        return True
    return False


def _pair_mentions(
    gold: Set[Mention],
    pred: Set[Mention],
    mode: str,
    overlap_threshold: float,
) -> Tuple[Set[Tuple[Mention, Mention]], Set[Mention], Set[Mention]]:
    matched: Set[Tuple[Mention, Mention]] = set()
    used_gold: Set[Mention] = set()
    used_pred: Set[Mention] = set()

    if mode == "strict":
        for g in sorted(gold, key=lambda x: (x.kind, x.span, x.attrs)):
            candidates = [p for p in pred if p not in used_pred and g == p]
            if candidates:
                best = candidates[0]
                matched.add((g, best))
                used_gold.add(g)
                used_pred.add(best)
    else:
        # Relaxed mode: priority-based global assignment (avoids greedy prediction stealing).
        #
        # Tier 3 — exact span+attrs equality (= strict TPs)
        # Tier 2 — IoU >= overlap_threshold (descending IoU)
        # Tier 1 — containment: pred ⊆ gold OR gold ⊆ pred, for non-CONJ entity golds
        #           sorted by descending containment-IoU then ascending gold span size
        #
        # Processing higher tiers first ensures IoU-based matches are never displaced
        # by containment-based matches.

        def _tier_and_score(g: Mention, p: Mention) -> Optional[Tuple]:
            if g.kind != p.kind:
                return None
            iou = _span_iou(g.span, p.span)
            if g == p:
                return (3, iou, 0)
            if iou >= overlap_threshold:
                return (2, iou, 0)
            # Containment for non-CONJ entities (pred ⊆ gold OR gold ⊆ pred).
            if g.kind == "entity" and not _is_conj_mention(g):
                g_set = set(g.span)
                p_set = set(p.span)
                if p_set <= g_set or g_set <= p_set:
                    # Sort by containment IoU descending, then smallest gold span first.
                    return (1, iou, -len(g_set))
            return None

        # Build all candidate pairs with scores.
        candidates: List[Tuple[Tuple, Mention, Mention]] = []
        for g in gold:
            for p in pred:
                score = _tier_and_score(g, p)
                if score is not None:
                    candidates.append((score, g, p))

        # Assign in descending priority order (highest tier + score first).
        candidates.sort(key=lambda x: x[0], reverse=True)
        for _, g, p in candidates:
            if g in used_gold or p in used_pred:
                continue
            matched.add((g, p))
            used_gold.add(g)
            used_pred.add(p)

    unmatched_gold = {g for g in gold if g not in used_gold}
    unmatched_pred = {p for p in pred if p not in used_pred}
    return matched, unmatched_gold, unmatched_pred



def projection_signature(doc: NormalizedDocument) -> str:
    """Return a deterministic content signature for a projected document."""
    payload = (
        doc.doc_id,
        tuple(sorted((m.kind, m.span, tuple(sorted(m.attrs))) for m in doc.entity_mentions)),
        tuple(sorted((m.kind, m.span, tuple(sorted(m.attrs))) for m in doc.event_mentions)),
        tuple(sorted((m.kind, m.span, tuple(sorted(m.attrs))) for m in doc.timex_mentions)),
        tuple(
            sorted(
                (
                    r.kind,
                    r.source_kind,
                    r.source_span,
                    r.target_kind,
                    r.target_span,
                    tuple(sorted(r.attrs)),
                )
                for r in doc.relations
            )
        ),
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def check_projection_determinism(
    graph: Any,
    doc_id: int | str,
    runs: int = 2,
    **projection_kwargs: Any,
) -> Dict[str, Any]:
    """Build projection repeatedly and report determinism signal.

    Deterministic means all projection runs produce the same content signature.
    """
    run_count = max(2, int(runs))
    signatures: list[str] = []
    for _ in range(run_count):
        doc = build_document_from_neo4j(graph=graph, doc_id=doc_id, **projection_kwargs)
        signatures.append(projection_signature(doc))

    baseline = signatures[0]
    mismatch_runs = [i for i, sig in enumerate(signatures) if sig != baseline]
    return {
        "doc_id": str(doc_id),
        "runs": run_count,
        "deterministic": len(mismatch_runs) == 0,
        "baseline_signature": baseline,
        "mismatch_runs": mismatch_runs,
    }


def _bucket_mention_errors(
    unmatched_gold: Set[Mention],
    unmatched_pred: Set[Mention],
) -> Dict[str, int]:
    """Classify unmatched mentions into stable error buckets."""
    remaining_pred = set(unmatched_pred)
    boundary_mismatch = 0
    type_mismatch = 0

    for g in sorted(unmatched_gold, key=lambda x: (x.kind, x.span, x.attrs)):
        same_span = [p for p in remaining_pred if p.kind == g.kind and p.span == g.span]
        if same_span:
            type_mismatch += 1
            remaining_pred.remove(same_span[0])
            continue

        overlap = [p for p in remaining_pred if p.kind == g.kind and _span_iou(g.span, p.span) > 0.0]
        if overlap:
            boundary_mismatch += 1
            remaining_pred.remove(overlap[0])

    missing = max(0, len(unmatched_gold) - type_mismatch - boundary_mismatch)
    spurious = max(0, len(unmatched_pred) - type_mismatch - boundary_mismatch)
    return {
        "boundary_mismatch": int(boundary_mismatch),
        "type_mismatch": int(type_mismatch),
        "missing": int(missing),
        "spurious": int(spurious),
    }


def _mention_to_dict(m: Mention) -> Dict[str, Any]:
    return {
        "kind": m.kind,
        "span": list(m.span),
        "attrs": {k: v for k, v in m.attrs},
    }


def _collect_mention_examples(
    unmatched_gold: Set[Mention],
    unmatched_pred: Set[Mention],
    max_examples: int,
) -> Dict[str, list[Dict[str, Any]]]:
    """Collect concrete examples of mention-level failures for debugging."""
    remaining_pred = set(unmatched_pred)
    boundary_examples: list[Dict[str, Any]] = []
    type_examples: list[Dict[str, Any]] = []
    used_gold: Set[Mention] = set()

    for g in sorted(unmatched_gold, key=lambda x: (x.kind, x.span, x.attrs)):
        if len(boundary_examples) >= max_examples and len(type_examples) >= max_examples:
            break

        same_span = [p for p in remaining_pred if p.kind == g.kind and p.span == g.span]
        if same_span and len(type_examples) < max_examples:
            p = same_span[0]
            type_examples.append({"gold": _mention_to_dict(g), "predicted": _mention_to_dict(p)})
            remaining_pred.remove(p)
            used_gold.add(g)
            continue

        overlap = [p for p in remaining_pred if p.kind == g.kind and _span_iou(g.span, p.span) > 0.0]
        if overlap and len(boundary_examples) < max_examples:
            p = overlap[0]
            boundary_examples.append({"gold": _mention_to_dict(g), "predicted": _mention_to_dict(p)})
            remaining_pred.remove(p)
            used_gold.add(g)

    missing_mentions = [m for m in sorted(unmatched_gold, key=lambda x: (x.kind, x.span, x.attrs)) if m not in used_gold]
    spurious_mentions = sorted(remaining_pred, key=lambda x: (x.kind, x.span, x.attrs))

    return {
        "boundary_mismatch": boundary_examples,
        "type_mismatch": type_examples,
        "missing": [{"gold": _mention_to_dict(m)} for m in missing_mentions],
        "spurious": [{"predicted": _mention_to_dict(m)} for m in spurious_mentions],
    }


def score_mention_layer(
    gold_mentions: Set[Mention],
    predicted_mentions: Set[Mention],
    mode: str = "strict",
    overlap_threshold: float = 0.5,
    attr_keys: Tuple[str, ...] = (),
    max_examples: int = 5,
) -> Dict[str, Any]:
    """Compute TP/FP/FN + precision/recall/F1 for one mention layer."""
    if attr_keys:
        gold_mentions = {m.with_attrs(attr_keys) for m in gold_mentions}
        predicted_mentions = {m.with_attrs(attr_keys) for m in predicted_mentions}

    matched, unmatched_gold, unmatched_pred = _pair_mentions(
        gold_mentions,
        predicted_mentions,
        mode=mode,
        overlap_threshold=overlap_threshold,
    )

    # In relaxed mode, CONJ gold mentions whose conjuncts were already matched
    # individually are treated as virtually matched rather than False Negatives.
    if mode == "relaxed":
        unmatched_gold = _apply_conj_virtual_merge(matched, unmatched_gold)

    m = precision_recall_f1(tp=len(matched), fp=len(unmatched_pred), fn=len(unmatched_gold))
    m["mode"] = mode
    m["matched_pairs"] = len(matched)
    m["errors"] = _bucket_mention_errors(unmatched_gold, unmatched_pred)
    m["examples"] = _collect_mention_examples(unmatched_gold, unmatched_pred, max_examples=max_examples)
    return m


def _relation_key(rel: Relation, mode: str) -> Tuple[Any, ...]:
    src_kind = rel.source_kind
    tgt_kind = rel.target_kind
    src = rel.source_span
    tgt = rel.target_span

    attrs_map = {str(k): str(v) for k, v in rel.attrs}
    reltype = str(attrs_map.get("reltype") or "").strip().upper()

    if rel.kind == "tlink":
        inverse_reltype = {
            "BEFORE": "AFTER",
            "AFTER": "BEFORE",
            "IBEFORE": "IAFTER",
            "IAFTER": "IBEFORE",
            "INCLUDES": "IS_INCLUDED",
            "IS_INCLUDED": "INCLUDES",
            "BEGINS": "BEGUN_BY",
            "BEGUN_BY": "BEGINS",
            "ENDS": "ENDED_BY",
            "ENDED_BY": "ENDS",
            "DURING": "DURING_INV",
            "DURING_INV": "DURING",
        }

        def _invert(rt: str) -> str:
            return inverse_reltype.get(rt, rt)

        # Canonicalize mixed event/timex links as event -> timex.
        if src_kind == "timex" and tgt_kind == "event":
            src_kind, tgt_kind = tgt_kind, src_kind
            src, tgt = tgt, src
            reltype = _invert(reltype)

        # Canonicalize same-kind links by span order.
        elif src_kind == tgt_kind and src > tgt:
            src, tgt = tgt, src
            reltype = _invert(reltype)

        if reltype:
            attrs_map["reltype"] = reltype

    if mode == "strict":
        attrs = tuple(sorted((k, v) for k, v in attrs_map.items()))
    else:
        attrs = tuple(sorted((k, v) for k, v in attrs_map.items() if k == "reltype"))

    return (rel.kind, src_kind, src, tgt_kind, tgt, attrs)


def _relation_span_overlap(a: TokenSpan, b: TokenSpan) -> bool:
    return _span_iou(a, b) > 0.0


def _bucket_relation_errors(gold_keys: Set[Tuple[Any, ...]], pred_keys: Set[Tuple[Any, ...]]) -> Dict[str, int]:
    remaining_pred = set(pred_keys)
    endpoint_mismatch = 0
    type_mismatch = 0
    tp_count = 0

    for g in gold_keys:
        # Skip exact matches (TPs) — they don't need error categorization.
        if g in remaining_pred:
            remaining_pred.discard(g)
            tp_count += 1
            continue

        same_endpoint = [
            p
            for p in remaining_pred
            if p[1] == g[1] and p[2] == g[2] and p[3] == g[3] and p[4] == g[4] and (p[0] != g[0] or p[5] != g[5])
        ]
        if same_endpoint:
            type_mismatch += 1
            remaining_pred.remove(same_endpoint[0])
            continue

        overlap_endpoint = [
            p
            for p in remaining_pred
            if p[0] == g[0]
            and p[1] == g[1]
            and p[3] == g[3]
            and _relation_span_overlap(g[2], p[2])
            and _relation_span_overlap(g[4], p[4])
        ]
        if overlap_endpoint:
            endpoint_mismatch += 1
            remaining_pred.remove(overlap_endpoint[0])

    missing = max(0, len(gold_keys) - tp_count - type_mismatch - endpoint_mismatch)
    spurious = max(0, len(pred_keys) - tp_count - type_mismatch - endpoint_mismatch)
    return {
        "endpoint_mismatch": int(endpoint_mismatch),
        "type_mismatch": int(type_mismatch),
        "missing": int(missing),
        "spurious": int(spurious),
    }


def _collect_relation_examples(
    gold_keys: Set[Tuple[Any, ...]],
    pred_keys: Set[Tuple[Any, ...]],
    max_examples: int,
) -> Dict[str, list[Dict[str, Any]]]:
    remaining_pred = set(pred_keys)
    endpoint_examples: list[Dict[str, Any]] = []
    type_examples: list[Dict[str, Any]] = []
    used_gold: Set[Tuple[Any, ...]] = set()

    for g in sorted(gold_keys, key=lambda x: str(x)):
        if len(endpoint_examples) >= max_examples and len(type_examples) >= max_examples:
            break

        # Skip exact matches (TPs) — they don't belong in error examples.
        if g in remaining_pred:
            remaining_pred.discard(g)
            used_gold.add(g)
            continue

        same_endpoint = [
            p
            for p in remaining_pred
            if p[1] == g[1] and p[2] == g[2] and p[3] == g[3] and p[4] == g[4] and (p[0] != g[0] or p[5] != g[5])
        ]
        if same_endpoint and len(type_examples) < max_examples:
            p = same_endpoint[0]
            type_examples.append({"gold": str(g), "predicted": str(p)})
            remaining_pred.remove(p)
            used_gold.add(g)
            continue

        overlap_endpoint = [
            p
            for p in remaining_pred
            if p[0] == g[0]
            and p[1] == g[1]
            and p[3] == g[3]
            and _relation_span_overlap(g[2], p[2])
            and _relation_span_overlap(g[4], p[4])
        ]
        if overlap_endpoint and len(endpoint_examples) < max_examples:
            p = overlap_endpoint[0]
            endpoint_examples.append({"gold": str(g), "predicted": str(p)})
            remaining_pred.remove(p)
            used_gold.add(g)

    missing = [k for k in sorted(gold_keys, key=lambda x: str(x)) if k not in used_gold]
    spurious = sorted(remaining_pred, key=lambda x: str(x))
    return {
        "endpoint_mismatch": endpoint_examples,
        "type_mismatch": type_examples,
        "missing": [{"gold": str(k)} for k in missing],
        "spurious": [{"predicted": str(k)} for k in spurious],
    }


def score_relation_layer(
    gold_relations: Set[Relation],
    predicted_relations: Set[Relation],
    mode: str = "strict",
    attr_keys: Dict[str, Tuple[str, ...]] | Tuple[str, ...] = (),
    max_examples: int = 5,
) -> Dict[str, Any]:
    """Compute TP/FP/FN + precision/recall/F1 for relation layer."""
    if attr_keys:
        def _attrs_for_relation(rel: Relation) -> Tuple[Tuple[str, str], ...]:
            if isinstance(attr_keys, dict):
                keep = set(attr_keys.get(rel.kind, ()))
            else:
                keep = set(attr_keys)
            if not keep:
                return ()
            return tuple(sorted((k, v) for k, v in rel.attrs if k in keep))

        gold_relations = {
            Relation(
                kind=r.kind,
                source_kind=r.source_kind,
                source_span=r.source_span,
                target_kind=r.target_kind,
                target_span=r.target_span,
                attrs=_attrs_for_relation(r),
            )
            for r in gold_relations
        }
        predicted_relations = {
            Relation(
                kind=r.kind,
                source_kind=r.source_kind,
                source_span=r.source_span,
                target_kind=r.target_kind,
                target_span=r.target_span,
                attrs=_attrs_for_relation(r),
            )
            for r in predicted_relations
        }

    if mode == "strict":
        gold_keys = {_relation_key(r, "strict"): r for r in gold_relations}
        pred_keys = {_relation_key(r, "strict"): r for r in predicted_relations}
        
        tp_keys = set(gold_keys.keys()) & set(pred_keys.keys())
        tp = len(tp_keys)
        fp = len(pred_keys) - tp
        fn = len(gold_keys) - tp
        
        out = precision_recall_f1(tp=tp, fp=fp, fn=fn)
        out["mode"] = "strict"
        out["errors"] = _bucket_relation_errors(set(gold_keys.keys()), set(pred_keys.keys()))
        out["examples"] = _collect_relation_examples(set(gold_keys.keys()), set(pred_keys.keys()), max_examples=max_examples)
        return out
        
    else:  # Relaxed mode
        # Relaxed relation matching must use TLINK-canonicalized direction semantics
        # (same as strict keys) and deterministic candidate ordering.
        def _relaxed_view(rel: Relation) -> Tuple[str, str, TokenSpan, str, TokenSpan, str]:
            kind, src_kind, src_span, tgt_kind, tgt_span, attrs = _relation_key(rel, "relaxed")
            attrs_map = dict(attrs)
            return (
                str(kind),
                str(src_kind),
                tuple(src_span),
                str(tgt_kind),
                tuple(tgt_span),
                str(attrs_map.get("reltype") or ""),
            )

        gold_ordered = sorted(gold_relations, key=lambda r: str(_relation_key(r, "strict")))
        pred_ordered = sorted(predicted_relations, key=lambda r: str(_relation_key(r, "strict")))
        gold_view = [_relaxed_view(r) for r in gold_ordered]
        pred_view = [_relaxed_view(r) for r in pred_ordered]

        # Candidate match score: maximize endpoint overlap while preserving deterministic ties.
        candidates: List[Tuple[float, float, str, str, int, int]] = []
        for gi, gv in enumerate(gold_view):
            g_kind, g_src_kind, g_src_span, g_tgt_kind, g_tgt_span, g_reltype = gv
            for pi, pv in enumerate(pred_view):
                p_kind, p_src_kind, p_src_span, p_tgt_kind, p_tgt_span, p_reltype = pv

                if g_kind != p_kind:
                    continue
                if g_src_kind != p_src_kind or g_tgt_kind != p_tgt_kind:
                    continue
                if g_reltype != p_reltype:
                    continue

                src_iou = _span_iou(g_src_span, p_src_span)
                tgt_iou = _span_iou(g_tgt_span, p_tgt_span)
                if src_iou == 0.0 or tgt_iou == 0.0:
                    continue

                # Score high overlap first, then deterministic key order.
                candidates.append(
                    (
                        src_iou + tgt_iou,
                        min(src_iou, tgt_iou),
                        str(_relation_key(gold_ordered[gi], "strict")),
                        str(_relation_key(pred_ordered[pi], "strict")),
                        gi,
                        pi,
                    )
                )

        candidates.sort(key=lambda c: (-c[0], -c[1], c[2], c[3]))

        used_gold_idx: Set[int] = set()
        used_pred_idx: Set[int] = set()
        tp_pairs: List[Dict[str, str]] = []
        for _, _, gk, pk, gi, pi in candidates:
            if gi in used_gold_idx or pi in used_pred_idx:
                continue
            used_gold_idx.add(gi)
            used_pred_idx.add(pi)
            tp_pairs.append({"gold": gk, "predicted": pk})

        tp = len(used_gold_idx)
        fp = len(pred_ordered) - tp
        fn = len(gold_ordered) - tp

        unmatched_gold = [
            str(_relation_key(gold_ordered[gi], "strict"))
            for gi in range(len(gold_ordered))
            if gi not in used_gold_idx
        ]
        unmatched_pred = [
            str(_relation_key(pred_ordered[pi], "strict"))
            for pi in range(len(pred_ordered))
            if pi not in used_pred_idx
        ]

        if max_examples:
            shown_tp_pairs = tp_pairs[:max_examples]
            shown_missing = unmatched_gold[:max_examples]
            shown_spurious = unmatched_pred[:max_examples]
        else:
            shown_tp_pairs = tp_pairs
            shown_missing = unmatched_gold
            shown_spurious = unmatched_pred

        out = precision_recall_f1(tp=tp, fp=fp, fn=fn)
        out["mode"] = "relaxed"
        out["errors"] = {
            "relaxed_mismatch": fp,
            "missing": fn,
            "spurious": fp,
        }
        out["examples"] = {
            "matched_pairs": shown_tp_pairs,
            "missing": [{"gold": g} for g in shown_missing],
            "spurious": [{"predicted": p} for p in shown_spurious],
        }
        return out


def evaluate_documents(
    gold_doc: NormalizedDocument,
    predicted_doc: NormalizedDocument,
    overlap_threshold: float = 0.5,
    mapping: Optional[EvaluationMapping] = None,
    max_examples: int = 5,
) -> Dict[str, Any]:
    """Evaluate gold vs predicted normalized documents."""
    cfg = mapping or EvaluationMapping()

    entity_attr = cfg.mention_attr_keys.get("entity", ())
    event_attr = cfg.mention_attr_keys.get("event", ())
    timex_attr = cfg.mention_attr_keys.get("timex", ())
    relation_attr = cfg.relation_attr_keys

    snapped_relations = set()
    for r in predicted_doc.relations:
        src = r.source_span
        tgt = r.target_span
        
        if r.source_kind == "entity": src = _align_relation_entity_span(src, gold_doc.entity_mentions)
        elif r.source_kind == "event": src = _align_relation_event_span(src, gold_doc.event_mentions)
        elif r.source_kind == "timex": src = _align_relation_timex_span(src, gold_doc.timex_mentions)

        if r.target_kind == "entity": tgt = _align_relation_entity_span(tgt, gold_doc.entity_mentions)
        elif r.target_kind == "event": tgt = _align_relation_event_span(tgt, gold_doc.event_mentions)
        elif r.target_kind == "timex": tgt = _align_relation_timex_span(tgt, gold_doc.timex_mentions)
        
        snapped_relations.add(Relation(r.kind, r.source_kind, src, r.target_kind, tgt, r.attrs))
        
    predicted_doc.relations = snapped_relations

    strict = {
        "entity": score_mention_layer(gold_doc.entity_mentions, predicted_doc.entity_mentions, mode="strict", overlap_threshold=overlap_threshold, attr_keys=entity_attr, max_examples=max_examples),
        "event": score_mention_layer(gold_doc.event_mentions, predicted_doc.event_mentions, mode="strict", overlap_threshold=overlap_threshold, attr_keys=event_attr, max_examples=max_examples),
        "timex": score_mention_layer(gold_doc.timex_mentions, predicted_doc.timex_mentions, mode="strict", overlap_threshold=overlap_threshold, attr_keys=timex_attr, max_examples=max_examples),
        "relation": score_relation_layer(gold_doc.relations, predicted_doc.relations, mode="strict", attr_keys=relation_attr, max_examples=max_examples),
    }
    relaxed = {
        "entity": score_mention_layer(gold_doc.entity_mentions, predicted_doc.entity_mentions, mode="relaxed", overlap_threshold=overlap_threshold, attr_keys=entity_attr, max_examples=max_examples),
        "event": score_mention_layer(gold_doc.event_mentions, predicted_doc.event_mentions, mode="relaxed", overlap_threshold=overlap_threshold, attr_keys=event_attr, max_examples=max_examples),
        "timex": score_mention_layer(gold_doc.timex_mentions, predicted_doc.timex_mentions, mode="relaxed", overlap_threshold=overlap_threshold, attr_keys=timex_attr, max_examples=max_examples),
        "relation": score_relation_layer(gold_doc.relations, predicted_doc.relations, mode="relaxed", attr_keys=relation_attr, max_examples=max_examples),
    }

    relation_kinds = sorted({r.kind for r in gold_doc.relations} | {r.kind for r in predicted_doc.relations})
    relation_by_kind: Dict[str, Dict[str, Dict[str, Any]]] = {"strict": {}, "relaxed": {}}
    for rel_kind in relation_kinds:
        gold_kind = {r for r in gold_doc.relations if r.kind == rel_kind}
        pred_kind = {r for r in predicted_doc.relations if r.kind == rel_kind}
        relation_by_kind["strict"][rel_kind] = score_relation_layer(
            gold_kind,
            pred_kind,
            mode="strict",
            attr_keys=relation_attr,
            max_examples=max_examples,
        )
        relation_by_kind["relaxed"][rel_kind] = score_relation_layer(
            gold_kind,
            pred_kind,
            mode="relaxed",
            attr_keys=relation_attr,
            max_examples=max_examples,
        )

    return {
        "doc_id": gold_doc.doc_id,
        "strict": strict,
        "relaxed": relaxed,
        "relation_by_kind": relation_by_kind,
        "counts": {
            "gold": {
                "entity": len(gold_doc.entity_mentions),
                "event": len(gold_doc.event_mentions),
                "timex": len(gold_doc.timex_mentions),
                "relation": len(gold_doc.relations),
            },
            "predicted": {
                "entity": len(predicted_doc.entity_mentions),
                "event": len(predicted_doc.event_mentions),
                "timex": len(predicted_doc.timex_mentions),
                "relation": len(predicted_doc.relations),
            },
        },
    }


def aggregate_reports(reports: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate per-document reports into micro and macro summaries."""
    rows = list(reports)
    layers = ("entity", "event", "timex", "relation")
    modes = ("strict", "relaxed")

    out: Dict[str, Any] = {
        "documents": len(rows),
        "micro": {},
        "macro": {},
        "relation_by_kind": {"micro": {}, "macro": {}},
    }

    for mode in modes:
        out["micro"][mode] = {}
        out["macro"][mode] = {}
        for layer in layers:
            tp = sum(int(r.get(mode, {}).get(layer, {}).get("tp", 0)) for r in rows)
            fp = sum(int(r.get(mode, {}).get(layer, {}).get("fp", 0)) for r in rows)
            fn = sum(int(r.get(mode, {}).get(layer, {}).get("fn", 0)) for r in rows)
            micro = precision_recall_f1(tp=tp, fp=fp, fn=fn)
            out["micro"][mode][layer] = micro

            n = max(1, len(rows))
            macro = {
                "precision": sum(float(r.get(mode, {}).get(layer, {}).get("precision", 0.0)) for r in rows) / n,
                "recall": sum(float(r.get(mode, {}).get(layer, {}).get("recall", 0.0)) for r in rows) / n,
                "f1": sum(float(r.get(mode, {}).get(layer, {}).get("f1", 0.0)) for r in rows) / n,
            }
            out["macro"][mode][layer] = macro

    relation_kinds = sorted(
        {
            kind
            for r in rows
            for kind in set(r.get("relation_by_kind", {}).get("strict", {}).keys())
            | set(r.get("relation_by_kind", {}).get("relaxed", {}).keys())
        }
    )
    for mode in modes:
        out["relation_by_kind"]["micro"][mode] = {}
        out["relation_by_kind"]["macro"][mode] = {}
        for rel_kind in relation_kinds:
            tp = sum(int(r.get("relation_by_kind", {}).get(mode, {}).get(rel_kind, {}).get("tp", 0)) for r in rows)
            fp = sum(int(r.get("relation_by_kind", {}).get(mode, {}).get(rel_kind, {}).get("fp", 0)) for r in rows)
            fn = sum(int(r.get("relation_by_kind", {}).get(mode, {}).get(rel_kind, {}).get("fn", 0)) for r in rows)
            out["relation_by_kind"]["micro"][mode][rel_kind] = precision_recall_f1(tp=tp, fp=fp, fn=fn)

            n = max(1, len(rows))
            out["relation_by_kind"]["macro"][mode][rel_kind] = {
                "precision": sum(
                    float(r.get("relation_by_kind", {}).get(mode, {}).get(rel_kind, {}).get("precision", 0.0))
                    for r in rows
                ) / n,
                "recall": sum(
                    float(r.get("relation_by_kind", {}).get(mode, {}).get(rel_kind, {}).get("recall", 0.0))
                    for r in rows
                ) / n,
                "f1": sum(
                    float(r.get("relation_by_kind", {}).get(mode, {}).get(rel_kind, {}).get("f1", 0.0))
                    for r in rows
                ) / n,
            }

    return out


def build_dual_scorecards_from_aggregate(aggregate: Dict[str, Any]) -> Dict[str, Any]:
    """Build TimeML and beyond-TimeML scorecards from aggregate metrics."""
    strict_micro = dict(aggregate.get("micro", {}).get("strict", {}))
    relaxed_micro = dict(aggregate.get("micro", {}).get("relaxed", {}))

    strict_event = float(strict_micro.get("event", {}).get("f1", 0.0))
    strict_timex = float(strict_micro.get("timex", {}).get("f1", 0.0))
    strict_relation = float(strict_micro.get("relation", {}).get("f1", 0.0))
    relaxed_event = float(relaxed_micro.get("event", {}).get("f1", 0.0))
    relaxed_relation = float(relaxed_micro.get("relation", {}).get("f1", 0.0))

    compliance_composite = (
        0.40 * strict_event
        + 0.30 * strict_timex
        + 0.30 * strict_relation
    )

    relation_gain = max(0.0, relaxed_relation - strict_relation)
    event_gain = max(0.0, relaxed_event - strict_event)
    reasoning_composite = (0.70 * relation_gain) + (0.30 * event_gain)

    return {
        "time_ml_compliance": {
            "strict_event_f1": strict_event,
            "strict_timex_f1": strict_timex,
            "strict_relation_f1": strict_relation,
            "composite": compliance_composite,
            "weights": {"event": 0.40, "timex": 0.30, "relation": 0.30},
        },
        "beyond_timeml_reasoning": {
            "strict_event_f1": strict_event,
            "relaxed_event_f1": relaxed_event,
            "strict_relation_f1": strict_relation,
            "relaxed_relation_f1": relaxed_relation,
            "event_gain": event_gain,
            "relation_gain": relation_gain,
            "composite": reasoning_composite,
            "weights": {"relation_gain": 0.70, "event_gain": 0.30},
        },
    }


def build_dual_scorecards_from_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Build dual scorecards from a single-document report payload."""
    pseudo_aggregate = {
        "micro": {
            "strict": {
                layer: report.get("strict", {}).get(layer, {})
                for layer in ("entity", "event", "timex", "relation")
            },
            "relaxed": {
                layer: report.get("relaxed", {}).get(layer, {})
                for layer in ("entity", "event", "timex", "relation")
            },
        }
    }
    return build_dual_scorecards_from_aggregate(pseudo_aggregate)


def _avg_f1_for_doc(report: Dict[str, Any], mode: str) -> float:
    layers = ("entity", "event", "timex", "relation")
    vals = [float(report.get(mode, {}).get(layer, {}).get("f1", 0.0)) for layer in layers]
    return sum(vals) / float(len(vals)) if vals else 0.0


def build_document_diagnostics(
    report: Dict[str, Any],
    mode: str = "strict",
    f1_threshold: float = 0.75,
) -> Dict[str, Any]:
    """Build actionable diagnostics and suggestions for one document report."""
    layers = ("entity", "event", "timex", "relation")
    layer_rows = []
    suggestions = []

    for layer in layers:
        m = report.get(mode, {}).get(layer, {})
        errors = m.get("errors", {})
        row = {
            "layer": layer,
            "f1": float(m.get("f1", 0.0)),
            "precision": float(m.get("precision", 0.0)),
            "recall": float(m.get("recall", 0.0)),
            "tp": int(m.get("tp", 0)),
            "fp": int(m.get("fp", 0)),
            "fn": int(m.get("fn", 0)),
            "errors": {
                "boundary_mismatch": int(errors.get("boundary_mismatch", 0)),
                "type_mismatch": int(errors.get("type_mismatch", 0)),
                "missing": int(errors.get("missing", 0)),
                "spurious": int(errors.get("spurious", 0)),
                "endpoint_mismatch": int(errors.get("endpoint_mismatch", 0)),
            },
            "examples": m.get("examples", {}),
        }
        layer_rows.append(row)

        if row["f1"] < f1_threshold:
            suggestions.append(
                f"{layer}: low F1 ({row['f1']:.3f}) - inspect extraction and matching rules for this layer."
            )
        if row["errors"]["boundary_mismatch"] > 0:
            suggestions.append(
                f"{layer}: boundary mismatches detected - verify token span anchoring (`start_tok`, `end_tok`) and overlap threshold."
            )
        if row["errors"]["type_mismatch"] > 0:
            suggestions.append(
                f"{layer}: type mismatches detected - tune label/attribute mapping in mapping-config."
            )
        if row["errors"]["missing"] > row["errors"]["spurious"]:
            suggestions.append(
                f"{layer}: recall is weaker than precision - investigate under-generation and missing extractions."
            )
        if row["errors"]["spurious"] > row["errors"]["missing"]:
            suggestions.append(
                f"{layer}: precision is weaker than recall - investigate over-generation and filtering criteria."
            )

    suggestions = sorted(set(suggestions))
    weak_layers = [r["layer"] for r in layer_rows if r["f1"] < f1_threshold]
    return {
        "doc_id": report.get("doc_id", ""),
        "mode": mode,
        "avg_f1": _avg_f1_for_doc(report, mode),
        "weak_layers": weak_layers,
        "layers": layer_rows,
        "suggestions": suggestions,
    }


def build_dataset_diagnostics(
    reports: Iterable[Dict[str, Any]],
    aggregate: Dict[str, Any],
    mode: str = "strict",
    f1_threshold: float = 0.75,
    top_k: int = 10,
) -> Dict[str, Any]:
    """Build cross-document diagnostics, hotspots, and actionable guidance."""
    rows = list(reports)
    doc_diags = [build_document_diagnostics(r, mode=mode, f1_threshold=f1_threshold) for r in rows]
    hotspots = sorted(doc_diags, key=lambda d: float(d.get("avg_f1", 0.0)))[: max(1, min(top_k, len(doc_diags) or 1))]

    issue_totals: Dict[str, Dict[str, int]] = {
        "entity": {},
        "event": {},
        "timex": {},
        "relation": {},
    }
    for d in doc_diags:
        for layer_row in d.get("layers", []):
            layer = layer_row["layer"]
            for k, v in layer_row.get("errors", {}).items():
                issue_totals[layer][k] = issue_totals[layer].get(k, 0) + int(v)

    global_suggestions = []
    for layer, counts in issue_totals.items():
        if counts.get("boundary_mismatch", 0) > 0:
            global_suggestions.append(
                f"{layer}: high boundary mismatch volume - calibrate span normalization and tokenizer alignment."
            )
        if counts.get("type_mismatch", 0) > 0:
            global_suggestions.append(
                f"{layer}: type mismatch volume present - refine schema mapping and attribute projection."
            )
        if counts.get("missing", 0) > counts.get("spurious", 0):
            global_suggestions.append(
                f"{layer}: dataset-level recall gap - prioritize recall-oriented rules and candidate generation."
            )
        if counts.get("spurious", 0) > counts.get("missing", 0):
            global_suggestions.append(
                f"{layer}: dataset-level precision gap - tighten confidence filters and post-processing constraints."
            )

    layers = ("entity", "event", "timex", "relation")
    for layer in layers:
        f1 = float(aggregate.get("micro", {}).get(mode, {}).get(layer, {}).get("f1", 0.0))
        if f1 < f1_threshold:
            global_suggestions.append(
                f"{layer}: micro F1={f1:.3f} below threshold {f1_threshold:.2f} - mark as priority optimization track."
            )

    return {
        "mode": mode,
        "f1_threshold": f1_threshold,
        "issue_totals": issue_totals,
        "hotspot_documents": [
            {
                "doc_id": h.get("doc_id", ""),
                "avg_f1": h.get("avg_f1", 0.0),
                "weak_layers": h.get("weak_layers", []),
            }
            for h in hotspots
        ],
        "suggestions": sorted(set(global_suggestions)),
        "documents": doc_diags,
    }


def flatten_report_rows_for_csv(
    reports: Iterable[Dict[str, Any]],
    mode: str = "strict",
) -> list[Dict[str, Any]]:
    """Flatten per-document metrics into CSV-friendly rows."""
    out: list[Dict[str, Any]] = []
    layers = ("entity", "event", "timex", "relation")
    for r in reports:
        doc_id = r.get("doc_id", "")
        for layer in layers:
            m = r.get(mode, {}).get(layer, {})
            errors = m.get("errors", {})
            out.append(
                {
                    "doc_id": doc_id,
                    "mode": mode,
                    "layer": layer,
                    "tp": int(m.get("tp", 0)),
                    "fp": int(m.get("fp", 0)),
                    "fn": int(m.get("fn", 0)),
                    "precision": float(m.get("precision", 0.0)),
                    "recall": float(m.get("recall", 0.0)),
                    "f1": float(m.get("f1", 0.0)),
                    "boundary_mismatch": int(errors.get("boundary_mismatch", 0)),
                    "type_mismatch": int(errors.get("type_mismatch", 0)),
                    "endpoint_mismatch": int(errors.get("endpoint_mismatch", 0)),
                    "missing": int(errors.get("missing", 0)),
                    "spurious": int(errors.get("spurious", 0)),
                }
            )
    return out


def flatten_aggregate_rows_for_csv(aggregate: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Flatten aggregate micro/macro metrics into CSV-friendly rows."""
    out: list[Dict[str, Any]] = []
    for scope in ("micro", "macro"):
        for mode, layer_map in dict(aggregate.get(scope, {})).items():
            for layer, metrics in dict(layer_map).items():
                out.append(
                    {
                        "scope": scope,
                        "mode": mode,
                        "layer": layer,
                        "tp": int(metrics.get("tp", 0)) if scope == "micro" else "",
                        "fp": int(metrics.get("fp", 0)) if scope == "micro" else "",
                        "fn": int(metrics.get("fn", 0)) if scope == "micro" else "",
                        "precision": float(metrics.get("precision", 0.0)),
                        "recall": float(metrics.get("recall", 0.0)),
                        "f1": float(metrics.get("f1", 0.0)),
                    }
                )
    return out


def render_markdown_report(report: Dict[str, Any]) -> str:
    """Render a human-readable markdown report from evaluation output."""
    lines: list[str] = []
    mode = str(report.get("mode", "single"))
    lines.append("# Evaluation Report")
    lines.append("")
    lines.append(f"- Mode: {mode}")
    if mode == "batch":
        lines.append(f"- Documents evaluated: {int(report.get('documents_evaluated', 0))}")
        skipped = report.get("skipped_prediction_files") or []
        lines.append(f"- Skipped files (missing predictions): {len(skipped)}")
    else:
        lines.append(f"- Document id: {report.get('doc_id', '')}")
    lines.append("")

    aggregate = report.get("aggregate")
    if aggregate:
        lines.append("## Aggregate Metrics")
        lines.append("")
        lines.append("| Scope | Mode | Layer | Precision | Recall | F1 |")
        lines.append("|---|---|---:|---:|---:|---:|")
        for row in flatten_aggregate_rows_for_csv(aggregate):
            lines.append(
                f"| {row.get('scope','')} | {row.get('mode','')} | {row.get('layer','')} | "
                f"{float(row.get('precision',0.0)):.3f} | {float(row.get('recall',0.0)):.3f} | {float(row.get('f1',0.0)):.3f} |"
            )
        lines.append("")

        relation_by_kind = aggregate.get("relation_by_kind", {})
        if relation_by_kind:
            strict_rel = dict(relation_by_kind.get("micro", {}).get("strict", {}))
            if strict_rel:
                lines.append("## Relation Kind Breakdown (Micro Strict)")
                lines.append("")
                lines.append("| Relation Kind | Precision | Recall | F1 |")
                lines.append("|---|---:|---:|---:|")
                for rel_kind in sorted(strict_rel.keys()):
                    m = strict_rel.get(rel_kind, {})
                    lines.append(
                        f"| {rel_kind} | {float(m.get('precision', 0.0)):.3f} | {float(m.get('recall', 0.0)):.3f} | {float(m.get('f1', 0.0)):.3f} |"
                    )
                lines.append("")

    scorecards = report.get("scorecards") or {}
    if scorecards:
        tm = dict(scorecards.get("time_ml_compliance", {}))
        bt = dict(scorecards.get("beyond_timeml_reasoning", {}))
        lines.append("## Scorecards")
        lines.append("")
        lines.append("### TimeML Compliance")
        lines.append("")
        lines.append(f"- Strict Event F1: {float(tm.get('strict_event_f1', 0.0)):.3f}")
        lines.append(f"- Strict TIMEX F1: {float(tm.get('strict_timex_f1', 0.0)):.3f}")
        lines.append(f"- Strict Relation F1: {float(tm.get('strict_relation_f1', 0.0)):.3f}")
        lines.append(f"- Composite: {float(tm.get('composite', 0.0)):.3f}")
        lines.append("")
        lines.append("### Beyond-TimeML Reasoning")
        lines.append("")
        lines.append(f"- Event Gain (relaxed - strict): {float(bt.get('event_gain', 0.0)):.3f}")
        lines.append(f"- Relation Gain (relaxed - strict): {float(bt.get('relation_gain', 0.0)):.3f}")
        lines.append(f"- Composite: {float(bt.get('composite', 0.0)):.3f}")
        lines.append("")

    determinism = report.get("projection_determinism") or {}
    if determinism:
        lines.append("## Projection Determinism")
        lines.append("")
        # Aggregate (batch) reports use 'all_stable'; single-doc reports use 'deterministic'.
        if "all_stable" in determinism:
            stable = bool(determinism.get("all_stable"))
            documents_checked = int(determinism.get("documents_checked", 0))
            stable_documents = int(determinism.get("stable_documents", 0))
            unstable_documents = int(determinism.get("unstable_documents", 0))
            lines.append(f"- Deterministic: {stable}")
            lines.append(f"- Runs: {int(determinism.get('runs', 0))}")
            lines.append(
                f"- Documents: {stable_documents}/{documents_checked} stable"
                + (f", {unstable_documents} unstable" if unstable_documents else "")
            )
            unstable = [
                doc_id
                for doc_id, info in (determinism.get("by_doc") or {}).items()
                if not bool(info.get("deterministic", True))
            ]
            if unstable:
                lines.append(f"- Unstable docs: {', '.join(sorted(unstable))}")
        else:
            lines.append(f"- Deterministic: {bool(determinism.get('deterministic', False))}")
            lines.append(f"- Runs: {int(determinism.get('runs', 0))}")
            mismatch_runs = determinism.get("mismatch_runs") or []
            lines.append(f"- Mismatch runs: {mismatch_runs if mismatch_runs else 'none'}")
        lines.append("")

    diagnostics = report.get("diagnostics", {})
    if diagnostics:
        lines.append("## Suggestions")
        lines.append("")
        sugg = diagnostics.get("suggestions") or []
        if sugg:
            for s in sugg:
                lines.append(f"- {s}")
        else:
            lines.append("- No major issues detected in the selected analysis mode.")
        lines.append("")

        hotspots = diagnostics.get("hotspot_documents") or []
        if hotspots:
            lines.append("## Hotspot Documents")
            lines.append("")
            lines.append("| Doc ID | Avg F1 | Weak Layers |")
            lines.append("|---|---:|---|")
            for h in hotspots:
                weak = ", ".join(h.get("weak_layers", [])) or "-"
                lines.append(f"| {h.get('doc_id','')} | {float(h.get('avg_f1',0.0)):.3f} | {weak} |")
            lines.append("")

    if mode == "batch":
        docs = diagnostics.get("documents") or []
        if docs:
            lines.append("## Per-Document Diagnostics")
            lines.append("")
            for d in docs:
                lines.append(f"### Doc {d.get('doc_id','')}")
                lines.append("")
                lines.append(f"- Avg F1: {float(d.get('avg_f1',0.0)):.3f}")
                weak_layers = d.get("weak_layers") or []
                lines.append(f"- Weak layers: {', '.join(weak_layers) if weak_layers else 'none'}")
                lines.append("")
                lines.append("| Layer | TP | FP | FN | Precision | Recall | F1 |")
                lines.append("|---|---:|---:|---:|---:|---:|---:|")
                for lr in d.get("layers", []):
                    lines.append(
                        f"| {lr.get('layer','')} | {int(lr.get('tp',0))} | {int(lr.get('fp',0))} | {int(lr.get('fn',0))} | "
                        f"{float(lr.get('precision',0.0)):.3f} | {float(lr.get('recall',0.0)):.3f} | {float(lr.get('f1',0.0)):.3f} |"
                    )
                lines.append("")

                ds = d.get("suggestions") or []
                if ds:
                    lines.append("Suggested actions:")
                    for s in ds:
                        lines.append(f"- {s}")
                    lines.append("")

                lines.append("Top failure examples:")
                has_any_examples = False
                for lr in d.get("layers", []):
                    layer_name = lr.get("layer", "")
                    examples = lr.get("examples", {}) or {}
                    layer_blocks = []
                    for bucket in ("boundary_mismatch", "type_mismatch", "endpoint_mismatch", "missing", "spurious"):
                        items = examples.get(bucket) or []
                        if not items:
                            continue
                        layer_blocks.append(f"- {bucket} ({len(items)} shown):")
                        for item in items[:3]:
                            if "gold" in item and "predicted" in item:
                                layer_blocks.append(f"  - gold={item['gold']} | predicted={item['predicted']}")
                            elif "gold" in item:
                                layer_blocks.append(f"  - gold={item['gold']}")
                            elif "predicted" in item:
                                layer_blocks.append(f"  - predicted={item['predicted']}")
                            else:
                                layer_blocks.append(f"  - {item}")

                    if layer_blocks:
                        has_any_examples = True
                        lines.append(f"- {layer_name}:")
                        lines.extend(layer_blocks)
                if not has_any_examples:
                    lines.append("- none")
                lines.append("")

    return "\n".join(lines).strip() + "\n"
