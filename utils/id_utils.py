"""ID generation helpers used across textgraphx.

Centralize id format strings so MERGE operations are deterministic and
consistent across modules.
"""
from typing import Union

def _safe_str(x: Union[str, int]) -> str:
    return str(x)

def make_frame_id(doc_id: Union[str, int], start: int, end: int) -> str:
    """Return a stable frame id: frame_<doc>_<start>_<end>"""
    return f"frame_{_safe_str(doc_id)}_{start}_{end}"

def make_fa_id(doc_id: Union[str, int], start: int, end: int, argtype: str) -> str:
    """Return a stable FrameArgument id: fa_<doc>_<start>_<end>_<argtype>"""
    return f"fa_{_safe_str(doc_id)}_{start}_{end}_{argtype}"

def make_ne_id(doc_id: Union[str, int], start: int, end: int, ne_type: str) -> str:
    """Return a stable NamedEntity id: <doc>_<start>_<end>_<type>"""
    return f"{_safe_str(doc_id)}_{start}_{end}_{ne_type}"

def make_tagocc_id(doc_id: Union[str, int], sent_index: int, token_idx: int) -> str:
    """Return a TagOccurrence id: <doc>_<sent>_<token_idx>"""
    return f"{_safe_str(doc_id)}_{sent_index}_{token_idx}"

def make_nounchunk_id(doc_id: Union[str, int], start: int) -> str:
    """Return a NounChunk id: <doc>_<start>"""
    return f"{_safe_str(doc_id)}_{start}"

def make_event_mention_token_id(doc_id: Union[str, int], start: int, end: int) -> str:
    """Return a stable EventMention token_id: em_<doc>_<start>_<end>
    
    Used for token-based migration-safe joins, similar to NamedEntity.token_id.
    The format uses 'em_' prefix to distinguish EventMention token IDs from other types.
    """
    return f"em_{_safe_str(doc_id)}_{start}_{end}"
