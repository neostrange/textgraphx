"""ID generation helpers used across textgraphx.

Centralize id format strings so MERGE operations are deterministic and
consistent across modules.
"""
from typing import Union
import hashlib
import re

def _safe_str(x: Union[str, int]) -> str:
    return str(x)


def _normalize_surface_text(text: Union[str, None]) -> str:
    """Return a normalized surface form used by stable mention IDs."""
    s = (text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _short_hash(parts: list[str], length: int = 20) -> str:
    payload = "|".join(parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]

def make_frame_id(doc_id: Union[str, int], start: int, end: int) -> str:
    """Return a stable frame id: frame_<doc>_<start>_<end>"""
    return f"frame_{_safe_str(doc_id)}_{start}_{end}"

def make_fa_id(doc_id: Union[str, int], start: int, end: int, argtype: str) -> str:
    """Return a stable FrameArgument id: fa_<doc>_<start>_<end>_<argtype>"""
    return f"fa_{_safe_str(doc_id)}_{start}_{end}_{argtype}"

def make_ne_id(doc_id: Union[str, int], start: int, end: int, ne_type: str) -> str:
    """Return a stable NamedEntity id: <doc>_<start>_<end>_<type>"""
    return f"{_safe_str(doc_id)}_{start}_{end}_{ne_type}"


def make_ne_uid(doc_id: Union[str, int], value: str, head_token_index: Union[int, None]) -> str:
    """Return a span-agnostic NamedEntity UID.

    This key is designed to remain stable across boundary adjustments by
    anchoring on document, normalized surface text, and semantic head index.
    """
    base = [
        _safe_str(doc_id),
        _normalize_surface_text(value),
        _safe_str(head_token_index if head_token_index is not None else -1),
    ]
    return f"ne_{_safe_str(doc_id)}_{_short_hash(base)}"


def make_entity_mention_uid(
    doc_id: Union[str, int],
    value: str,
    head_token_index: Union[int, None],
    source: str = "generic",
) -> str:
    """Return a span-agnostic EntityMention UID.

    EntityMention UIDs include a source namespace because several mention
    materializers can emit identical surfaces in the same document.
    """
    base = [
        _safe_str(doc_id),
        source,
        _normalize_surface_text(value),
        _safe_str(head_token_index if head_token_index is not None else -1),
    ]
    return f"em_{_safe_str(doc_id)}_{_short_hash(base)}"


def make_coref_uid(
    doc_id: Union[str, int],
    value: str,
    anchor_token_index: Union[int, None],
    node_type: str,
) -> str:
    """Return a boundary-tolerant UID for coreference nodes.

    Coreference nodes do not have a reliable semantic head at initial write
    time, so this key anchors on document, normalized surface text, node type,
    and a deterministic token anchor.
    """
    base = [
        _safe_str(doc_id),
        node_type.lower(),
        _normalize_surface_text(value),
        _safe_str(anchor_token_index if anchor_token_index is not None else -1),
    ]
    prefix = "corefmention" if node_type == "CorefMention" else "antecedent"
    return f"{prefix}_{_safe_str(doc_id)}_{_short_hash(base)}"


def make_ne_token_id(doc_id: Union[str, int], start: int, end: int) -> str:
    """Return a type-agnostic NamedEntity token_id: <doc>_<start>_<end>

    Unlike make_ne_id, this id does not embed the NER type, so it stays
    stable even if the type is later corrected by NEL or refinement.
    Intended for migration-safe span-level joins.

    NOTE: Before switching EntityProcessor/EntityExtractor to use this function,
    migration 0018 must drop the unique constraint on NamedEntity.token_id (which
    would otherwise reject two nodes sharing the same span with different types).
    """
    return f"{_safe_str(doc_id)}_{start}_{end}"

def make_tagocc_id(doc_id: Union[str, int], sent_index: int, token_idx: int) -> str:
    """Return a TagOccurrence id: <doc>_<sent>_<token_idx>"""
    return f"{_safe_str(doc_id)}_{sent_index}_{token_idx}"

def make_nounchunk_id(doc_id: Union[str, int], start: int, end: int = -1, head_tok: int = -1) -> str:
    """Return a stable NounChunk id anchored on (doc, start, end, head_tok).

    Including *end* and *head_tok* prevents id collisions when two chunks share
    the same start position but have different extents or heads.

    The *end* and *head_tok* parameters default to -1 for backward compatibility
    with call sites that have not yet been updated, but callers should supply them
    to guarantee uniqueness.
    """
    return f"nc_{_safe_str(doc_id)}_{start}_{end}_{head_tok}"


def make_entity_id(doc_id: Union[str, int], kb_id_or_surface: Union[str, None], ne_type: str) -> str:
    """Return a deterministic Entity id.

    Two strategies:
    - *kb_id* present  : id is derived from the KB URI fragment so that the same
      real-world entity always resolves to the same node regardless of which
      document introduced it.  The KB URI itself is stored on ``Entity.kb_id``.
    - *kb_id* absent   : id is cross-document stable, anchored on (normalized
      surface, type).  Entities with the same surface form and NE type are
      treated as the same real-world referent across documents (same-surface
      merging).  ``doc_id`` is accepted for API compatibility but not used in
      the hash.
    """
    surface = kb_id_or_surface or ""
    if surface and ("/" in surface or ":" in surface):
        # Looks like a URI — derive a cross-doc stable fragment
        fragment = surface.rsplit("/", 1)[-1].rsplit(":", 1)[-1]
        return f"entity_{_short_hash([fragment, ne_type], length=24)}"
    # Unresolved: cross-document stable by (normalized_surface, type)
    base = [_normalize_surface_text(surface), ne_type.lower()]
    return f"entity_{_short_hash(base, length=20)}"

def make_event_mention_token_id(doc_id: Union[str, int], start: int, end: int) -> str:
    """Return a stable EventMention token_id: em_<doc>_<start>_<end>
    
    Used for token-based migration-safe joins, similar to NamedEntity.token_id.
    The format uses 'em_' prefix to distinguish EventMention token IDs from other types.
    """
    return f"em_{_safe_str(doc_id)}_{start}_{end}"
