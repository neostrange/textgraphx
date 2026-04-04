"""MEANTIME-oriented evaluation utilities.

This module normalizes gold annotations and pipeline outputs into a shared
representation, then computes precision/recall/F1 with strict and relaxed span
matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any, Dict, Iterable, Optional, Set, Tuple
import xml.etree.ElementTree as ET

from textgraphx.evaluation.metrics import precision_recall_f1

try:
    from nltk.corpus import wordnet as _wn  # type: ignore
except Exception:
    _wn = None


TokenSpan = Tuple[int, ...]


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
            "entity": ("syntactic_type",),
            "event": ("pos", "tense", "aspect", "certainty", "polarity", "time", "pred"),
            "timex": ("type", "value", "functionInDocument"),
        }
    )
    relation_attr_keys: Dict[str, Tuple[str, ...]] = field(
        default_factory=lambda: {
            "tlink": ("reltype",),
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
                attrs=_attrs_from_element(el, ("syntactic_type",)),
            )
            doc.entity_mentions.add(mention)
            mention_by_id[m_id] = mention
        elif tag == "EVENT_MENTION":
            mention = Mention(
                kind="event",
                span=span,
                attrs=_attrs_from_element(
                    el,
                    ("pos", "tense", "aspect", "certainty", "polarity", "time", "pred"),
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
                    }
                ),
            )
            doc.timex_mentions.add(mention)
            mention_by_id[m_id] = mention

    relations = root.find("Relations")
    if relations is None:
        return doc

    for rel in relations:
        if rel.tag not in {"TLINK", "HAS_PARTICIPANT"}:
            continue

        sources = [s.get("m_id") for s in rel.findall("source") if s.get("m_id")]
        targets = [t.get("m_id") for t in rel.findall("target") if t.get("m_id")]
        if not sources or not targets:
            continue

        relation_attrs: Tuple[Tuple[str, str], ...] = ()
        if rel.tag == "TLINK":
            relation_attrs = _attrs_from_element(rel, ("reltype",))
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


def build_document_from_neo4j(
    graph: Any,
    doc_id: int | str,
    gold_token_sequence: Optional[Tuple[Tuple[int, str], ...]] = None,
    discourse_only: bool = False,
    normalize_nominal_boundaries: bool = True,
    gold_like_nominal_filter: bool = False,
    nominal_profile_mode: str = "all",
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
    """
    doc_id_int = _resolve_graph_doc_id(graph, doc_id)
    profile_mode = str(nominal_profile_mode or "all").strip().lower()
    allowed_profile_modes = {"all", "eventive", "salient", "candidate-gold", "background"}
    if profile_mode not in allowed_profile_modes:
        raise ValueError(
            f"Unsupported nominal_profile_mode: {nominal_profile_mode}. "
            f"Expected one of: {sorted(allowed_profile_modes)}"
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
        MATCH (:AnnotatedText {{id: $doc_id}})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:PARTICIPATES_IN]->(m)
        WHERE (m:EntityMention OR m:NamedEntity) {_entity_discourse_clause}
        WITH m, min(tok.tok_index_doc) AS start_tok, max(tok.tok_index_doc) AS end_tok
        RETURN DISTINCT start_tok, end_tok,
             id(m) AS node_id,
               coalesce(m.syntactic_type, m.syntacticType) AS syntactic_type
        ORDER BY start_tok, end_tok
        """,
        {"doc_id": doc_id_int},
    ).data()
    for row in entity_rows:
        span = _span_from_bounds(int(row["start_tok"]), int(row["end_tok"]), token_index_alignment)
        syntactic_type = str(row.get("syntactic_type") or "")
        if syntactic_type.upper() == "NOMINAL":
            syntactic_type = "NOM"
        if normalize_nominal_boundaries and syntactic_type.upper() in {"NOM", "NOMINAL"}:
            span = _normalize_nominal_entity_span_for_eval(span, gold_token_lookup)
            if not span:
                continue
        if gold_like_nominal_filter and syntactic_type.upper() in {"NOM", "NOMINAL"}:
            features = _nominal_projection_features(
                graph=graph,
                doc_id=doc_id_int,
                node_id=int(row.get("node_id")),
                fallback_head_idx=int(row["end_tok"]),
            )
            if features.get("eventive_head", False) or _is_wordnet_eventive_noun(features):
                continue
            if _looks_like_proper_name_span(span, gold_token_lookup) or str(features.get("head_pos") or "") in {"NNP", "NNPS"}:
                syntactic_type = "NAM"
            else:
                cluster_size = int(features.get("mention_cluster_size", 0))
                has_named_link = bool(features.get("has_named_link", False))
                has_core_argument = bool(features.get("has_core_argument", False))
                if cluster_size <= 1 and not has_named_link and not has_core_argument:
                    continue
        if profile_mode != "all" and syntactic_type.upper() in {"NOM", "NOMINAL"}:
            features = _nominal_projection_features(
                graph=graph,
                doc_id=doc_id_int,
                node_id=int(row.get("node_id")),
                fallback_head_idx=int(row["end_tok"]),
            )
            eval_profile = str(features.get("nominal_eval_profile") or "").strip().lower()
            candidate_gold = bool(features.get("nominal_eval_candidate_gold", False))
            eventive = bool(features.get("eventive_head", False)) or _is_wordnet_eventive_noun(features)
            salient = bool(features.get("has_named_link", False)) or bool(features.get("has_core_argument", False)) or int(features.get("mention_cluster_size", 0)) > 1
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
        if syntactic_type:
            attrs = (("syntactic_type", syntactic_type),)
        doc.entity_mentions.add(Mention(kind="entity", span=span, attrs=attrs))

    event_rows = graph.run(
        """
         CALL {
             WITH $doc_id AS doc_id
             MATCH (m:EventMention)
             OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(m_tok:TagOccurrence)-[:PARTICIPATES_IN]->(m)
             WITH m, doc_id, count(m_tok) > 0 AS token_scoped
             WHERE (m.doc_id = doc_id OR token_scoped)
               AND m.start_tok IS NOT NULL AND m.end_tok IS NOT NULL
               AND coalesce(m.low_confidence, false) = false
             RETURN DISTINCT m.start_tok AS start_tok, m.end_tok AS end_tok,
                 m.pos AS pos, m.tense AS tense, m.aspect AS aspect,
                 m.certainty AS certainty, m.polarity AS polarity,
                 m.time AS time, m.pred AS pred,
                 2 AS source_priority
             UNION
             WITH $doc_id AS doc_id
             MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:TRIGGERS]->(m:TEvent)
                         WHERE coalesce(m.low_confidence, false) = false
                             AND NOT EXISTS {
                                     MATCH (em:EventMention)-[:REFERS_TO]->(m)
                                                                         WHERE (em.doc_id = doc_id OR EXISTS {
                                                                                         MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(em)
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
                 m.time AS time, pred AS pred,
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
                                 f.headword AS pred,
                                 0 AS source_priority
         }
         WITH start_tok, end_tok, pos, tense, aspect, certainty, polarity, time, pred, source_priority
         WHERE start_tok IS NOT NULL AND end_tok IS NOT NULL
         RETURN DISTINCT start_tok, end_tok, pos, tense, aspect, certainty, polarity, time, pred, source_priority
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
        mention = Mention(kind="event", span=span, attrs=attrs)
        priority = int(row.get("source_priority") or 0)
        current = event_by_span.get(span)
        if current is None or (priority, len(attrs)) > (current[0], len(current[1].attrs)):
            event_by_span[span] = (priority, mention)

    doc.event_mentions.update(m for _, m in event_by_span.values())

    timex_rows = graph.run(
        """
        MATCH (m:TIMEX)
        WHERE m.doc_id = $doc_id
           OR EXISTS {
               MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(m)
           }
        OPTIONAL MATCH (tok:TagOccurrence)-[:TRIGGERS]->(m)
        WITH m, min(tok.tok_index_doc) AS trig_start, max(tok.tok_index_doc) AS trig_end
        OPTIONAL MATCH (a:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok2:TagOccurrence)
                WHERE coalesce(m.start_char, m.start_index, m.begin) IS NOT NULL
                    AND coalesce(m.end_char, m.end_index, m.end) IS NOT NULL
                    AND toInteger(tok2.index) >= toInteger(coalesce(m.start_char, m.start_index, m.begin))
                    AND toInteger(tok2.end_index) <= toInteger(coalesce(m.end_char, m.end_index, m.end))
        WITH m,
             trig_start,
             trig_end,
             min(tok2.tok_index_doc) AS span_start,
             max(tok2.tok_index_doc) AS span_end
        WITH coalesce(m.start_tok, trig_start, span_start) AS start_tok,
             coalesce(m.end_tok, trig_end, span_end) AS end_tok,
             m
        WHERE start_tok IS NOT NULL AND end_tok IS NOT NULL
        RETURN DISTINCT start_tok, end_tok,
               m.type AS type, m.value AS value, m.functionInDocument AS functionInDocument
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
            }
        )
        doc.timex_mentions.add(Mention(kind="timex", span=span, attrs=attrs))

    tlink_rows = graph.run(
        """
                MATCH (a)-[r:TLINK]-(b)
                WHERE (a.doc_id = $doc_id OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN]->(a)
                            })
                    AND (b.doc_id = $doc_id OR EXISTS {
                                 MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS|PARTICIPATES_IN]->(b)
                            })
                    AND a.start_tok IS NOT NULL AND a.end_tok IS NOT NULL
          AND b.start_tok IS NOT NULL AND b.end_tok IS NOT NULL
        RETURN labels(a) AS source_labels,
               a.start_tok AS a_start, a.end_tok AS a_end,
               labels(b) AS target_labels,
               b.start_tok AS b_start, b.end_tok AS b_end,
               r.relType AS reltype
        """,
        {"doc_id": doc_id_int},
    ).data()
    for row in tlink_rows:
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

    participant_rows = graph.run(
        """
        CALL {
            WITH $doc_id AS doc_id
            MATCH (src)-[r:EVENT_PARTICIPANT|PARTICIPANT]->(evt:TEvent)
            WHERE evt.doc_id = doc_id
               OR EXISTS {
                   MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(evt)
               }
            OPTIONAL MATCH (mention:NamedEntity)-[:REFERS_TO]->(src)
            WITH coalesce(mention, src) AS endpoint, evt, r, doc_id
            MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(evt_tok:TagOccurrence)-[:TRIGGERS]->(evt)
            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN]->(endpoint)
              WITH endpoint, evt, r,
                 min(src_tok.tok_index_doc) AS src_start,
                 max(src_tok.tok_index_doc) AS src_end,
                  min(evt_tok.tok_index_doc) AS evt_tok_start,
                  max(evt_tok.tok_index_doc) AS evt_tok_end,
                 labels(endpoint) AS source_labels
              WITH source_labels, src_start, src_end,
                  coalesce(evt.start_tok, evt_tok_start) AS evt_start,
                  coalesce(evt.end_tok, evt_tok_end) AS evt_end,
                  r
              WHERE src_start IS NOT NULL AND src_end IS NOT NULL
                AND evt_start IS NOT NULL AND evt_end IS NOT NULL
              RETURN DISTINCT src_start, src_end, evt_start, evt_end,
                   coalesce(r.type, '') AS sem_role,
                   source_labels
            UNION
            WITH $doc_id AS doc_id
            MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(f:Frame)
            WITH DISTINCT f, doc_id
                 MATCH (fa:FrameArgument)-[r:PARTICIPANT|HAS_FRAME_ARGUMENT]->(f)
                        WHERE fa.type IN ['ARG0', 'ARG1', 'ARG2']
                        OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(head_tok:TagOccurrence)
                        WHERE head_tok.tok_index_doc = coalesce(f.headTokenIndex, f.start_tok)
                        WITH f, fa, r, doc_id, head(collect(head_tok)) AS head_tok
                        WHERE (coalesce(head_tok.pos, '') STARTS WITH 'VB')
                             OR EXISTS {
                                     MATCH (ev:TEvent)
                                     WHERE ev.start_tok = f.start_tok
                                         AND ev.end_tok = f.end_tok
                                         AND (ev.doc_id = doc_id OR EXISTS {
                                                 MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:TRIGGERS]->(ev)
                                         })
                             }
            OPTIONAL MATCH (fa)-[:REFERS_TO]->(src)
            OPTIONAL MATCH (mention:NamedEntity)-[:REFERS_TO]->(src)
                 OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(fa_tok:TagOccurrence)-[:PARTICIPATES_IN]->(fa)
                 OPTIONAL MATCH (fa_tok)-[:PARTICIPATES_IN]->(em:EntityMention)
                 WITH f, fa, r, coalesce(mention, src, em) AS endpoint, doc_id
            WHERE endpoint IS NOT NULL
            OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:PARTICIPATES_IN]->(endpoint)
                 WITH f, fa, r,
                 min(src_tok.tok_index_doc) AS src_start,
                 max(src_tok.tok_index_doc) AS src_end,
                 labels(endpoint) AS source_labels
            WHERE src_start IS NOT NULL AND src_end IS NOT NULL
              AND f.start_tok IS NOT NULL
              AND f.end_tok IS NOT NULL
                        WITH f.start_tok AS evt_start,
                                 f.end_tok AS evt_end,
                                 coalesce(r.type, fa.type, '') AS sem_role,
                                 src_start,
                                 src_end,
                                 source_labels,
                                 (src_end - src_start) AS span_width
                        ORDER BY evt_start, evt_end, sem_role, span_width ASC, src_start ASC
                        WITH evt_start, evt_end, sem_role,
                                 collect({src_start: src_start, src_end: src_end, source_labels: source_labels}) AS cands
                        WITH evt_start, evt_end, sem_role, head(cands) AS best
                        RETURN DISTINCT best.src_start AS src_start,
                                     best.src_end AS src_end,
                                     evt_start,
                                     evt_end,
                                     sem_role,
                                     best.source_labels AS source_labels
        }
        RETURN DISTINCT src_start, src_end, evt_start, evt_end, sem_role, source_labels
        ORDER BY evt_start, src_start
        """,
        {"doc_id": doc_id_int},
    ).data()
    for row in participant_rows:
        src_kind = _node_kind_from_labels(row.get("source_labels", []))
        if src_kind != "entity":
            continue
        evt_span = _span_from_bounds(int(row["evt_start"]), int(row["evt_end"]), token_index_alignment)
        evt_span = _align_relation_event_span(evt_span, doc.event_mentions)
        doc.relations.add(
            Relation(
                kind="has_participant",
                source_kind="event",
                source_span=evt_span,
                target_kind="entity",
                target_span=_span_from_bounds(int(row["src_start"]), int(row["src_end"]), token_index_alignment),
                attrs=(("sem_role", str(row.get("sem_role") or "")),),
            )
        )

    return doc


def _node_kind_from_labels(labels: Iterable[str]) -> Optional[str]:
    s = set(labels)
    if "TIMEX" in s:
        return "timex"
    if "EventMention" in s or "TEvent" in s:
        return "event"
    if "EntityMention" in s or "NamedEntity" in s:
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
    """Normalize event attrs toward MEANTIME strict comparison semantics.

    The graph frequently omits certainty/polarity/time for otherwise valid
    events, while noun-like events often carry placeholder tense/aspect values
    that are absent in gold. Canonicalization keeps strict matching from being
    dominated by representation defaults rather than extraction quality.
    """
    pos = _normalize_event_pos(row.get("pos"))
    tense = str(row.get("tense") or "").strip().upper()
    aspect = str(row.get("aspect") or "").strip().upper()
    certainty = str(row.get("certainty") or "").strip().upper() or "CERTAIN"
    polarity = str(row.get("polarity") or "").strip().upper() or "POS"
    time = str(row.get("time") or "").strip().upper() or "NON_FUTURE"
    pred = str(row.get("pred") or "").strip().lower()

    attrs_map: Dict[str, str] = {}
    if pos:
        attrs_map["pos"] = pos
    if pred:
        attrs_map["pred"] = pred

    # Gold noun events typically omit tense/aspect when they are semantically
    # unexpressed. Preserve those attrs only when informative.
    if pos == "NOUN":
        if tense and tense not in {"NONE", "O"}:
            attrs_map["tense"] = tense
        if aspect and aspect not in {"NONE", "O"}:
            attrs_map["aspect"] = aspect
    else:
        if tense:
            attrs_map["tense"] = tense
        if aspect:
            attrs_map["aspect"] = aspect

    attrs_map["certainty"] = certainty
    attrs_map["polarity"] = polarity
    attrs_map["time"] = time
    return tuple(sorted(attrs_map.items()))


def _canonicalize_timex_attrs(row: Dict[str, Any]) -> Tuple[Tuple[str, str], ...]:
    """Normalize TIMEX attrs toward MEANTIME strict comparison semantics."""
    typ = str(row.get("type") or "").strip().upper()
    value = str(row.get("value") or "").strip()
    function_in_document = str(row.get("functionInDocument") or "").strip() or "NONE"

    if typ == "DATE":
        if len(value) == 8 and value.isdigit():
            value = f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
        elif len(value) == 6 and value.isdigit():
            value = f"{value[0:4]}-{value[4:6]}"
        elif len(value) == 7 and value.isdigit():
            value = f"{value[0:4]}-{value[4:6]}-{value[6]}"

    attrs_map: Dict[str, str] = {}
    if typ:
        attrs_map["type"] = typ
    if value:
        attrs_map["value"] = value
    if function_in_document:
        attrs_map["functionInDocument"] = function_in_document
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
        first = gold_token_lookup.get(int(items[0]), "")
        if first in leading_determiners:
            items.pop(0)
            continue
        break

    while items:
        last = gold_token_lookup.get(int(items[-1]), "")
        if last in trailing_punct:
            items.pop()
            continue
        break

    return tuple(items)


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
    node_id: int,
    fallback_head_idx: int,
) -> Dict[str, Any]:
    rows = graph.run(
        """
        MATCH (m)
        WHERE id(m) = $node_id
        OPTIONAL MATCH (ht:TagOccurrence)-[:PARTICIPATES_IN]->(m)
                WHERE ht.tok_index_doc = coalesce(m.nominalSemanticHeadTokenIndex, m.headTokenIndex, $fallback_head_idx)
        WITH m, head(collect(ht)) AS head_tok
                WITH m, head_tok,
                         size([(head_tok)-[:TRIGGERS]->(:TEvent {doc_id: $doc_id}) | 1]) > 0 AS trigger_eventive
        OPTIONAL MATCH (m)-[:REFERS_TO]->(e:Entity)<-[:REFERS_TO]-(other:EntityMention)
        WHERE other <> m
                WITH m, head_tok, trigger_eventive, count(DISTINCT other) AS mention_cluster_size
         OPTIONAL MATCH (arg_tok:TagOccurrence)-[:PARTICIPATES_IN]->(m)
         OPTIONAL MATCH (arg_tok)-[:PARTICIPATES_IN]->(fa:FrameArgument)
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
                         coalesce(m.nominalEventiveConfidence, 0.0) AS nominal_eventive_confidence
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
        "noun.phenomenon",
        "noun.process",
        "noun.state",
    }

    lexname = str(features.get("head_wn_lexname") or "").strip()
    synset = str(features.get("head_nltk_synset") or "").strip()
    if not lexname:
        lexname = _wordnet_lexname(synset)
    if lexname in target_lex:
        return True

    # Fallback: use persisted hypernyms if synset cannot be resolved at runtime.
    eventive_hypernym_roots = ("event.n.", "act.n.", "process.n.", "state.n.", "phenomenon.n.")
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
        return _sorted_span(mapped)
    return _sorted_span(range(start_tok, end_tok + 1))


def _align_relation_event_span(span: TokenSpan, event_mentions: Set[Mention]) -> TokenSpan:
    """Align relation-side event span to the nearest projected event mention span."""
    if not span or not event_mentions:
        return span

    mention_spans = [m.span for m in event_mentions if m.kind == "event"]
    if not mention_spans:
        return span
    if span in mention_spans:
        return span

    overlapping = [s for s in mention_spans if _span_iou(span, s) > 0.0]
    if not overlapping:
        return span

    return max(overlapping, key=lambda s: (_span_iou(span, s), len(s)))


def _span_iou(a: TokenSpan, b: TokenSpan) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return float(len(sa & sb)) / float(len(sa | sb)) if (sa or sb) else 0.0


def _pair_mentions(
    gold: Set[Mention],
    pred: Set[Mention],
    mode: str,
    overlap_threshold: float,
) -> Tuple[Set[Tuple[Mention, Mention]], Set[Mention], Set[Mention]]:
    matched: Set[Tuple[Mention, Mention]] = set()
    used_gold: Set[Mention] = set()
    used_pred: Set[Mention] = set()

    def _compatible(g: Mention, p: Mention) -> bool:
        if g.kind != p.kind:
            return False
        if mode == "strict":
            return g == p
        if g.with_attrs([]) != p.with_attrs([]):
            return _span_iou(g.span, p.span) >= overlap_threshold
        return True

    for g in sorted(gold, key=lambda x: (x.kind, x.span, x.attrs)):
        candidates = [p for p in pred if p not in used_pred and _compatible(g, p)]
        if not candidates:
            continue
        if mode == "strict":
            best = candidates[0]
        else:
            best = max(candidates, key=lambda p: _span_iou(g.span, p.span))
        matched.add((g, best))
        used_gold.add(g)
        used_pred.add(best)

    unmatched_gold = {g for g in gold if g not in used_gold}
    unmatched_pred = {p for p in pred if p not in used_pred}
    return matched, unmatched_gold, unmatched_pred


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
        "missing": [{"gold": _mention_to_dict(m)} for m in missing_mentions[:max_examples]],
        "spurious": [{"predicted": _mention_to_dict(m)} for m in spurious_mentions[:max_examples]],
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

    m = precision_recall_f1(tp=len(matched), fp=len(unmatched_pred), fn=len(unmatched_gold))
    m["mode"] = mode
    m["matched_pairs"] = len(matched)
    m["errors"] = _bucket_mention_errors(unmatched_gold, unmatched_pred)
    m["examples"] = _collect_mention_examples(unmatched_gold, unmatched_pred, max_examples=max_examples)
    return m


def _relation_key(rel: Relation, mode: str) -> Tuple[Any, ...]:
    src = rel.source_span
    tgt = rel.target_span
    attrs = rel.attrs if mode == "strict" else tuple((k, v) for k, v in rel.attrs if k == "reltype")
    return (rel.kind, rel.source_kind, src, rel.target_kind, tgt, attrs)


def _relation_span_overlap(a: TokenSpan, b: TokenSpan) -> bool:
    return _span_iou(a, b) > 0.0


def _bucket_relation_errors(gold_keys: Set[Tuple[Any, ...]], pred_keys: Set[Tuple[Any, ...]]) -> Dict[str, int]:
    remaining_pred = set(pred_keys)
    endpoint_mismatch = 0
    type_mismatch = 0

    for g in gold_keys:
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

    missing = max(0, len(gold_keys) - type_mismatch - endpoint_mismatch)
    spurious = max(0, len(pred_keys) - type_mismatch - endpoint_mismatch)
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

    missing = [k for k in sorted(gold_keys, key=lambda x: str(x)) if k not in used_gold][:max_examples]
    spurious = sorted(remaining_pred, key=lambda x: str(x))[:max_examples]
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
    attr_keys: Tuple[str, ...] = (),
    max_examples: int = 5,
) -> Dict[str, Any]:
    """Compute TP/FP/FN + precision/recall/F1 for relation layer."""
    if attr_keys:
        gold_relations = {
            Relation(
                kind=r.kind,
                source_kind=r.source_kind,
                source_span=r.source_span,
                target_kind=r.target_kind,
                target_span=r.target_span,
                attrs=tuple(sorted((k, v) for k, v in r.attrs if k in set(attr_keys))),
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
                attrs=tuple(sorted((k, v) for k, v in r.attrs if k in set(attr_keys))),
            )
            for r in predicted_relations
        }

    gold_keys = {_relation_key(r, mode) for r in gold_relations}
    pred_keys = {_relation_key(r, mode) for r in predicted_relations}

    tp = len(gold_keys & pred_keys)
    fp = len(pred_keys - gold_keys)
    fn = len(gold_keys - pred_keys)
    out = precision_recall_f1(tp=tp, fp=fp, fn=fn)
    out["mode"] = mode
    out["errors"] = _bucket_relation_errors(gold_keys, pred_keys)
    out["examples"] = _collect_relation_examples(gold_keys, pred_keys, max_examples=max_examples)
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
    rel_tlink_attr = cfg.relation_attr_keys.get("tlink", ())

    strict = {
        "entity": score_mention_layer(gold_doc.entity_mentions, predicted_doc.entity_mentions, mode="strict", overlap_threshold=overlap_threshold, attr_keys=entity_attr, max_examples=max_examples),
        "event": score_mention_layer(gold_doc.event_mentions, predicted_doc.event_mentions, mode="strict", overlap_threshold=overlap_threshold, attr_keys=event_attr, max_examples=max_examples),
        "timex": score_mention_layer(gold_doc.timex_mentions, predicted_doc.timex_mentions, mode="strict", overlap_threshold=overlap_threshold, attr_keys=timex_attr, max_examples=max_examples),
        "relation": score_relation_layer(gold_doc.relations, predicted_doc.relations, mode="strict", attr_keys=rel_tlink_attr, max_examples=max_examples),
    }
    relaxed = {
        "entity": score_mention_layer(gold_doc.entity_mentions, predicted_doc.entity_mentions, mode="relaxed", overlap_threshold=overlap_threshold, attr_keys=entity_attr, max_examples=max_examples),
        "event": score_mention_layer(gold_doc.event_mentions, predicted_doc.event_mentions, mode="relaxed", overlap_threshold=overlap_threshold, attr_keys=event_attr, max_examples=max_examples),
        "timex": score_mention_layer(gold_doc.timex_mentions, predicted_doc.timex_mentions, mode="relaxed", overlap_threshold=overlap_threshold, attr_keys=timex_attr, max_examples=max_examples),
        "relation": score_relation_layer(gold_doc.relations, predicted_doc.relations, mode="relaxed", attr_keys=rel_tlink_attr, max_examples=max_examples),
    }
    return {
        "doc_id": gold_doc.doc_id,
        "strict": strict,
        "relaxed": relaxed,
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

    return out


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
