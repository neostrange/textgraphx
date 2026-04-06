"""Utilities for enforcing ontology-backed reasoning contracts at runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

_ONT_CACHE: Optional[Dict[str, Any]] = None


def _ontology_path() -> Path:
    return Path(__file__).resolve().parent / "schema" / "ontology.json"


def load_ontology_contract(force_reload: bool = False) -> Dict[str, Any]:
    global _ONT_CACHE
    if _ONT_CACHE is None or force_reload:
        _ONT_CACHE = json.loads(_ontology_path().read_text(encoding="utf-8"))
    return _ONT_CACHE


def canonical_event_attribute_vocabulary() -> Dict[str, Iterable[str]]:
    payload = load_ontology_contract()
    return payload.get("event_attribute_vocabulary", {})


def temporal_reasoning_profile() -> Dict[str, Any]:
    payload = load_ontology_contract()
    return payload.get("temporal_reasoning_profile", {})


def normalize_event_attr(field: str, value: Any) -> Any:
    """Normalize event attribute values against ontology vocabulary.

    Unknown values fall back to conservative defaults for core fields.
    """
    if value is None:
        return None

    vocab = canonical_event_attribute_vocabulary()
    normalized = str(value).strip().upper()
    if normalized == "":
        return None

    allowed = set(vocab.get(field, []))
    if not allowed:
        return normalized

    if normalized in allowed:
        return normalized

    fallback = {
        "tense": "NONE",
        "aspect": "NONE",
        "polarity": "POS",
        "certainty": "UNCERTAIN",
    }.get(field)
    return fallback if fallback in allowed else None


def relation_endpoint_contract() -> Dict[str, Any]:
    payload = load_ontology_contract()
    return payload.get("relation_endpoint_contract", {})


def _count_query(graph: Any, query: str, params: Dict[str, Any]) -> int:
    rows = graph.run(query, params).data()
    return int(rows[0].get("c", 0)) if rows else 0


def count_endpoint_violations(graph: Any, rel_type: str) -> int:
    """Count relationships that violate ontology endpoint typing contract.

    For generic source/target contracts, checks source and target labels independently.
    For explicit allowed_pairs contracts, enforces pair-level compatibility.
    """
    contract = relation_endpoint_contract().get(rel_type)
    if not contract:
        return 0

    if "allowed_pairs" in contract:
        allowed_pairs = contract.get("allowed_pairs", [])
        if not allowed_pairs:
            return 0
        pair_clauses = []
        params: Dict[str, Any] = {}
        for idx, pair in enumerate(allowed_pairs):
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            src_key = f"src_{idx}"
            dst_key = f"dst_{idx}"
            params[src_key] = str(pair[0])
            params[dst_key] = str(pair[1])
            pair_clauses.append(
                f"(any(lbl IN labels(s) WHERE lbl = ${src_key}) AND any(lbl IN labels(t) WHERE lbl = ${dst_key}))"
            )
        if not pair_clauses:
            return 0

        query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE NOT ({' OR '.join(pair_clauses)})
        RETURN count(r) AS c
        """
        return _count_query(graph, query, params)

    sources = list(contract.get("sources", []))
    targets = list(contract.get("targets", []))
    if not sources or not targets:
        return 0

    query = f"""
    MATCH (s)-[r:{rel_type}]->(t)
    WHERE NOT any(lbl IN labels(s) WHERE lbl IN $sources)
       OR NOT any(lbl IN labels(t) WHERE lbl IN $targets)
    RETURN count(r) AS c
    """
    return _count_query(graph, query, {"sources": sources, "targets": targets})
