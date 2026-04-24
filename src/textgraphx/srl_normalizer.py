"""Compatibility wrapper for canonical SRL normalization helpers."""

from textgraphx.reasoning.srl_normalizer import (
    FRAMENET_CORE_ROLES_BY_FRAME,
    PROPBANK_CORE_ROLES,
    FrameNetAligner,
    SRLRoleContract,
    SRLRoleNormalizer,
    normalize_srl_annotation,
)

__all__ = [
    "FRAMENET_CORE_ROLES_BY_FRAME",
    "PROPBANK_CORE_ROLES",
    "FrameNetAligner",
    "SRLRoleContract",
    "SRLRoleNormalizer",
    "normalize_srl_annotation",
]
