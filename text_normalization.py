"""Helpers for normalizing source text before spaCy processing."""

from __future__ import annotations

import re


_END_PUNCT_RE = re.compile(r"[.!?]\s*$")
_MULTISPACE_RE = re.compile(r"[ \t]+")
_BLANKLINE_SPLIT_RE = re.compile(r"\n\s*\n+")


def _normalize_newlines(text: str) -> str:
    # Normalize CRLF/CR to LF so subsequent logic is platform-independent.
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def _join_lines_with_space(paragraph: str) -> str:
    joined = " ".join(line.strip() for line in paragraph.split("\n") if line.strip())
    return _MULTISPACE_RE.sub(" ", joined).strip()


def _normalize_meantime_style(text: str) -> str:
    paragraphs = [_join_lines_with_space(p) for p in _BLANKLINE_SPLIT_RE.split(text) if _join_lines_with_space(p)]
    if not paragraphs:
        return ""

    out: list[str] = []
    for i, para in enumerate(paragraphs):
        if i == 0:
            out.append(para)
            continue
        prev = out[-1]
        if _END_PUNCT_RE.search(prev):
            out.append(" " + para)
        else:
            out.append(". " + para)
    return "".join(out)


def _looks_like_meantime_header(text: str) -> bool:
    paragraphs = [p.strip() for p in _BLANKLINE_SPLIT_RE.split(text) if p.strip()]
    if len(paragraphs) < 2:
        return False
    first = _join_lines_with_space(paragraphs[0])
    second = _join_lines_with_space(paragraphs[1])
    if not first or not second:
        return False
    return (not _END_PUNCT_RE.search(first)) and len(first) < 140 and len(second) < 80


def normalize_naf_raw_text(raw_text: str, mode: str = "auto") -> str:
    """Normalize NAF raw text for sentence segmentation.

    Modes:
    - auto: detect MEANTIME-style headline/date formatting and apply meantime mode.
    - preserve: keep line breaks (safe default for generic corpora).
    - meantime: convert paragraph breaks into sentence separators for headline/date blocks.
    - legacy: old behavior that strips newlines.
    """
    normalized = _normalize_newlines(raw_text)
    selected = (mode or "auto").strip().lower()

    if selected == "legacy":
        return normalized.replace(".\n", ". \n").replace("”\n", "” ").replace("\n", "")
    if selected == "preserve":
        return normalized
    if selected == "meantime":
        return _normalize_meantime_style(normalized)
    if selected == "auto":
        if _looks_like_meantime_header(normalized):
            return _normalize_meantime_style(normalized)
        return normalized

    raise ValueError("Unknown NAF sentence normalization mode: " + selected)
