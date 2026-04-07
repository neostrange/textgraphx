"""M4.1: SRL Role Normalization and FrameNet Alignment.

Normalizes Semantic Role Labeling (SRL) role tags to a canonical vocabulary
aligned with FrameNet corpus conventions.

Provides:
  - PropBank role mapping (ARG0-ARG5 → semantic roles)
  - FrameNet frame-role alignment
  - Role normalization and validation
  - Missing role argument detection
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


# Standard PropBank core argument mappings
PROPBANK_CORE_ROLES = {
    "ARG0": "agent",        # Agent (doer of action)
    "ARG1": "patient",      # Patient (affected by action)
    "ARG2": "instrument",   # Instrument/attribute/topic
    "ARG3": "recipient",    # Recipient/beneficiary/attribute
    "ARG4": "attribute",    # Attribute (predicate nominalization)
    "ARG5": "location",     # Location
}

# FrameNet frame-role mappings (subset of common frames)
FRAMENET_CORE_ROLES_BY_FRAME = {
    "Motion": {
        "Agent": "ARG0",
        "Theme": "ARG1",
        "Source": "ARG4",
        "Path": "ARG2",
        "Goal": "ARG3",
    },
    "Transitive_action": {
        "Agent": "ARG0",
        "Patient": "ARG1",
        "Instrument": "ARG2",
        "Result": "ARG4",
    },
    "Communication": {
        "Communicator": "ARG0",
        "Message": "ARG1",
        "Addressee": "ARG3",
        "Topic": "ARG2",
    },
    "State_of_entity": {
        "Entity": "ARG1",
        "State": "ARG2",
    },
    "Possession": {
        "Owner": "ARG0",
        "Possession": "ARG1",
    },
}


class SRLRoleNormalizer:
    """Normalizes SRL role tags to canonical vocabulary."""
    
    @staticmethod
    def normalize_propbank_role(role_tag: str) -> Optional[str]:
        """Convert PropBank ARG tags to semantic role names.
        
        Args:
            role_tag: PropBank role tag (e.g., "ARG0", "ARG1")
        
        Returns:
            Semantic role name or None if not recognized
        """
        # Handle core arguments
        if role_tag in PROPBANK_CORE_ROLES:
            return PROPBANK_CORE_ROLES[role_tag]
        
        # Handle temporal/locative modifiers
        if role_tag == "ARGM-TMP":
            return "temporal"
        if role_tag == "ARGM-LOC":
            return "locative"
        if role_tag == "ARGM-MNR":
            return "manner"
        if role_tag == "ARGM-PRP":
            return "purpose"
        if role_tag == "ARGM-CAU":
            return "cause"
        
        return None
    
    @staticmethod
    def normalize_framenet_role(
        frame_name: str,
        frame_element: str,
    ) -> Optional[str]:
        """Normalize FrameNet frame element to semantic role.
        
        Args:
            frame_name: FrameNet frame name
            frame_element: Frame element (role) within frame
        
        Returns:
            Canonical semantic role or None
        """
        if frame_name not in FRAMENET_CORE_ROLES_BY_FRAME:
            return None
        
        frame_roles = FRAMENET_CORE_ROLES_BY_FRAME[frame_name]
        if frame_element not in frame_roles:
            return None
        
        # Map back to canonical role name
        propbank_arg = frame_roles[frame_element]
        return PROPBANK_CORE_ROLES.get(propbank_arg)
    
    @staticmethod
    def is_core_role(role: str) -> bool:
        """Check if a role is a core argument (not modifier)."""
        return role in ("agent", "patient", "instrument", "recipient", "attribute", "location")
    
    @staticmethod
    def is_modifier_role(role: str) -> bool:
        """Check if a role is a modifier (temporal, locative, etc.)."""
        modifiers = ("temporal", "locative", "manner", "purpose", "cause")
        return role in modifiers


class FrameNetAligner:
    """Aligns SRL annotations with FrameNet frame semantics."""
    
    @staticmethod
    def get_frame_roles(frame_name: str) -> Optional[Dict[str, str]]:
        """Get role mapping for a FrameNet frame."""
        return FRAMENET_CORE_ROLES_BY_FRAME.get(frame_name)
    
    @staticmethod
    def validate_frame_role_structure(
        frame_name: str,
        provided_roles: Set[str],
    ) -> Tuple[bool, List[str]]:
        """Validate that provided roles match frame expectations.
        
        Args:
            frame_name: FrameNet frame name
            provided_roles: Set of provided frame elements
        
        Returns:
            (is_valid, list of missing core roles)
        """
        if frame_name not in FRAMENET_CORE_ROLES_BY_FRAME:
            return True, []  # Unknown frame, no validation
        
        expected_roles = set(FRAMENET_CORE_ROLES_BY_FRAME[frame_name].keys())
        missing = expected_roles - provided_roles
        
        # Check if missing roles are critical
        critical_missing = ["Agent", "Theme", "Patient"]  # Typically required
        critical_gaps = [r for r in missing if r in critical_missing and frame_name in ("Motion", "Transitive_action")]
        
        is_valid = len(critical_gaps) == 0
        return is_valid, list(critical_gaps)
    
    @staticmethod
    def suggest_framenet_frame(
        predicate: str,
        observed_roles: List[str],
    ) -> Optional[str]:
        """Suggest a FrameNet frame based on predicate and roles.
        
        This is a simplified heuristic - full implementation would use
        a machine learning model or lexical lookup.
        """
        # Heuristic: motion verbs use Motion frame
        motion_verbs = ("move", "go", "travel", "run", "walk", "come")
        if any(pred.lower().startswith(v) for v, pred in [(v, predicate) for v in motion_verbs]):
            return "Motion"
        
        # Heuristic: communication verbs use Communication frame
        communication_verbs = ("say", "tell", "speak", "talk", "ask", "answer")
        if any(pred.lower().startswith(v) for v, pred in [(v, predicate) for v in communication_verbs]):
            return "Communication"
        
        # Heuristic: possession-related
        possession_verbs = ("have", "own", "hold", "keep", "carry")
        if any(pred.lower().startswith(v) for v, pred in [(v, predicate) for v in possession_verbs]):
            return "Possession"
        
        return None


class SRLRoleContract:
    """Defines contracts for SRL role annotation completeness."""
    
    # Expected role patterns by predicate type
    ROLE_REQUIREMENTS = {
        "transitive_action": {
            "required": ["agent", "patient"],
            "optional": ["instrument", "location", "temporal"],
            "forbidden": [],
        },
        "intransitive_action": {
            "required": ["agent"],
            "optional": ["location", "temporal", "manner"],
            "forbidden": ["patient"],
        },
        "state_predicate": {
            "required": ["patient"],
            "optional": ["location", "temporal"],
            "forbidden": ["agent"],
        },
        "possession": {
            "required": ["agent", "patient"],
            "optional": ["location", "temporal"],
            "forbidden": [],
        },
    }
    
    @staticmethod
    def validate_role_structure(
        predicate_type: str,
        assigned_roles: List[str],
    ) -> Tuple[bool, List[str]]:
        """Validate SRL role structure against contract.
        
        Args:
            predicate_type: Type of predicate ("transitive_action", etc.)
            assigned_roles: List of assigned roles
        
        Returns:
            (is_valid, list of violations)
        """
        if predicate_type not in SRLRoleContract.ROLE_REQUIREMENTS:
            return True, []  # Unknown type, no validation
        
        contract = SRLRoleContract.ROLE_REQUIREMENTS[predicate_type]
        violations = []
        
        # Check required roles
        assigned_set = set(assigned_roles)
        for required in contract["required"]:
            if required not in assigned_set:
                violations.append(f"Missing required role: {required}")
        
        # Check forbidden roles
        for forbidden in contract["forbidden"]:
            if forbidden in assigned_set:
                violations.append(f"Forbidden role assigned: {forbidden}")
        
        return len(violations) == 0, violations


def normalize_srl_annotation(
    predicate: str,
    roles: Dict[str, str],  # role_name -> value
) -> Dict[str, Any]:
    """Normalize an SRL annotation to canonical form.
    
    Args:
        predicate: The predicate/frame verb
        roles: Dict of role name -> argument value
    
    Returns:
        Normalized annotation with:
          - canonical_frame: Suggested FrameNet frame
          - canonical_roles: Normalized role assignments
          - missing_roles: Roles that should be present
          - annotation_confidence: Quality estimate (0.0-1.0)
    """
    normalizer = SRLRoleNormalizer()
    aligner = FrameNetAligner()
    
    # Suggest frame
    frame = aligner.suggest_framenet_frame(predicate, list(roles.keys()))
    
    # Normalize roles
    normalized_roles = {}
    for role_tag, value in roles.items():
        normalized = normalizer.normalize_propbank_role(role_tag)
        if normalized:
            normalized_roles[normalized] = value
    
    # Check completeness
    missing_roles = []
    if frame:
        expected = set(FRAMENET_CORE_ROLES_BY_FRAME[frame].values())
        provided = set(normalized_roles.keys())
        missing_roles = list(expected - provided)
    
    # Confidence score: higher if core roles present, lower if missing
    confidence = len(normalized_roles) / max(1, len(normalized_roles) + len(missing_roles))
    
    return {
        "predicate": predicate,
        "canonical_frame": frame,
        "canonical_roles": normalized_roles,
        "missing_roles": missing_roles,
        "annotation_confidence": confidence,
    }
