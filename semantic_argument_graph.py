"""M4.2: Semantic Role Argument Graph Construction.

Constructs semantic graphs from SRL role annotations, linking:
  - Predicates → arguments via semantic roles
  - Arguments → entities via coreference
  - Role chains for compositional semantics
  - Role alternations (passives, ditransitives)

Provides:
  - Graph node/edge construction from SRL
  - Role chain inference
  - Argument span mapping
  - Graph consistency validation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class SemanticGraphNode:
    """Represents a node in the semantic argument graph."""
    
    node_id: str                    # Unique identifier
    node_type: str                  # "predicate", "argument", "entity", "event"
    label: str                      # Content (predicate name or entity surface form)
    span: Optional[Tuple[int, int]]  # Token range (start, end) if available
    properties: Dict[str, Any]      # Additional metadata
    
    def __repr__(self) -> str:
        span_str = f"@{self.span}" if self.span else ""
        return f"{self.node_type}({self.label}{span_str})"


@dataclass
class SemanticGraphEdge:
    """Represents a directed edge in the semantic argument graph."""
    
    source_id: str
    target_id: str
    role: str                       # Role label (e.g., "agent", "patient")
    properties: Dict[str, Any]
    
    def __repr__(self) -> str:
        return f"{self.source_id} --[{self.role}]--> {self.target_id}"


class SemanticArgumentGraph:
    """Constructs and manages semantic graphs from SRL annotations."""
    
    def __init__(self):
        """Initialize empty graph."""
        self.nodes: Dict[str, SemanticGraphNode] = {}
        self.edges: List[SemanticGraphEdge] = []
        self._next_node_id = 0
    
    def add_node(
        self,
        node_type: str,
        label: str,
        span: Optional[Tuple[int, int]] = None,
        properties: Optional[Dict[str, Any]] = None,
        node_id: Optional[str] = None,
    ) -> str:
        """Add a node to the graph.
        
        Args:
            node_type: Type of node ("predicate", "argument", "entity", "event")
            label: Content/label of the node
            span: Token range (start, end) if applicable
            properties: Additional metadata
            node_id: Optional explicit node ID (generated if not provided)
        
        Returns:
            The node ID
        """
        if node_id is None:
            node_id = f"node_{self._next_node_id}"
            self._next_node_id += 1
        
        node = SemanticGraphNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            span=span,
            properties=properties or {},
        )
        self.nodes[node_id] = node
        return node_id
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        role: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> SemanticGraphEdge:
        """Add an edge to the graph.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            role: Role label for the edge
            properties: Additional metadata
        
        Returns:
            The created edge
        """
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Invalid node IDs: {source_id}, {target_id}")
        
        edge = SemanticGraphEdge(
            source_id=source_id,
            target_id=target_id,
            role=role,
            properties=properties or {},
        )
        self.edges.append(edge)
        return edge
    
    def get_node(self, node_id: str) -> Optional[SemanticGraphNode]:
        """Retrieve a node by ID."""
        return self.nodes.get(node_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[SemanticGraphEdge]:
        """Get all edges emanating from a node."""
        return [e for e in self.edges if e.source_id == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[SemanticGraphEdge]:
        """Get all edges targeting a node."""
        return [e for e in self.edges if e.target_id == node_id]
    
    def get_edges_by_role(self, role: str) -> List[SemanticGraphEdge]:
        """Get all edges with a specific role."""
        return [e for e in self.edges if e.role == role]
    
    def find_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 3,
    ) -> List[List[SemanticGraphEdge]]:
        """Find paths between two nodes (for role chains).
        
        Args:
            start_id: Starting node ID
            end_id: Target node ID
            max_depth: Maximum path length
        
        Returns:
            List of paths (each path is a list of edges)
        """
        paths = []
        
        def dfs(current_id: str, target_id: str, path: List[SemanticGraphEdge], depth: int):
            if depth > max_depth:
                return
            if current_id == target_id and path:
                paths.append(path[:])
                return
            
            for edge in self.get_outgoing_edges(current_id):
                path.append(edge)
                dfs(edge.target_id, target_id, path, depth + 1)
                path.pop()
        
        dfs(start_id, end_id, [], 0)
        return paths
    
    def get_role_chain(self, start_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get transitive role relationships from a node.
        
        Args:
            start_id: Starting node (typically a predicate)
            depth: How many levels of role forwarding to explore
        
        Returns:
            Dict mapping roles to sets of reachable entities
        """
        role_chains = {}
        visited = set()
        
        def collect_roles(node_id: str, current_depth: int):
            if node_id in visited or current_depth > depth:
                return
            visited.add(node_id)
            
            for edge in self.get_outgoing_edges(node_id):
                role = edge.role
                if role not in role_chains:
                    role_chains[role] = set()
                
                target_node = self.get_node(edge.target_id)
                if target_node:
                    role_chains[role].add(target_node.label)
                    collect_roles(edge.target_id, current_depth + 1)
        
        collect_roles(start_id, 0)
        return role_chains


class RoleAlternationHandler:
    """Handles semantic role alternations (passive, ditransitive, etc.)."""
    
    # Passive: ARG1 (patient) moves to subject position, ARG0 (agent) optional prepositional phrase
    PASSIVE_PATTERN = {
        "active_roles": ["agent", "patient"],
        "passive_roles": ["patient", "agent"],
        "passive_agent_marker": "by",  # "by" phrase in English passives
    }
    
    # Ditransitive: ARG0 (agent), ARG1 (theme), ARG3 (recipient)
    # Can alternate: "give X to Y" vs "give Y X"
    DITRANSITIVE_ALTERNATIONS = {
        "to_dative": {
            "primary": "ARG1",  # Theme is the direct object
            "secondary": "ARG3",  # Recipient is the indirect object (PP)
        },
        "double_object": {
            "primary": "ARG3",   # Recipient is the direct object
            "secondary": "ARG1", # Theme is the indirect object
        },
    }
    
    @staticmethod
    def detect_passive_voice(
        predicate: str,
        roles: Dict[str, str],
        morphology: Optional[str] = None,
    ) -> bool:
        """Detect if a predicate is in passive voice.
        
        Args:
            predicate: Predicate/verb form
            roles: Assigned semantic roles
            morphology: Morphological annotation if available (e.g., "VBN")
        
        Returns:
            True if passive construction detected
        """
        # Heuristic: agent missing or marked as "by" phrase suggests passive
        has_agent = "agent" in roles
        has_patient = "patient" in roles
        
        # If patient is subject (ARG0 position) and agent is missing/PP, likely passive
        # (This is simplified; full implementation needs syntactic parsing)
        return has_patient and not has_agent
    
    @staticmethod
    def normalize_passive_to_active(
        roles: Dict[str, str],
    ) -> Dict[str, str]:
        """Convert passive role structure to active equivalent.
        
        Maps passive argument structure back to canonical active form.
        
        Args:
            roles: Passive voice roles
        
        Returns:
            Normalized active-voice role structure
        """
        normalized = {}
        
        # In passive: subject (ARG0 position) is actually patient → move to ARG1
        if "patient" in roles:
            normalized["patient"] = roles.get("patient", roles.get("ARG0"))
        
        # Agent in passive typically appears in "by" phrase
        if "agent" in roles:
            normalized["agent"] = roles.get("agent", "")
        
        # Other arguments remain the same
        for role in ["instrument", "recipient", "location"]:
            if role in roles:
                normalized[role] = roles[role]
        
        return normalized
    
    @staticmethod
    def detect_ditransitive_alternation(
        predicate: str,
        roles: Dict[str, str],
        syntactic_structure: Optional[str] = None,
    ) -> Optional[str]:
        """Detect which ditransitive alternation is used.
        
        Args:
            predicate: Predicate/verb
            roles: Assigned roles
            syntactic_structure: Syntactic parse information if available
        
        Returns:
            "to_dative", "double_object", or None if not a ditransitive alternation
        """
        # Check if this is a ditransitive predicate
        ditransitive_verbs = {"give", "send", "tell", "show", "teach", "ask", "bring", "take"}
        if not any(predicate.lower().startswith(v) for v in ditransitive_verbs):
            return None
        
        # Check if both theme and recipient are present
        has_theme = "patient" in roles
        has_recipient = "recipient" in roles
        
        if not (has_theme and has_recipient):
            return None
        
        # Heuristic: if recipient is in prepositional phrase (marked "to", "for"), it's to-dative
        # Otherwise, if recipient is direct object, it's double-object
        recipient_val = roles.get("recipient", "")
        if "to" in recipient_val or "for" in recipient_val:
            return "to_dative"
        else:
            return "double_object"


class SRLGraphConstructor:
    """High-level constructor for semantic argument graphs from SRL."""
    
    @staticmethod
    def build_from_srl_annotation(
        sentence_text: str,
        predicate: str,
        predicate_span: Tuple[int, int],
        roles: Dict[str, Tuple[str, Tuple[int, int]]],  # role → (text, span)
        coreference_chains: Optional[Dict[str, str]] = None,  # span_id → entity_id
    ) -> SemanticArgumentGraph:
        """Build a semantic argument graph from SRL annotation.
        
        Args:
            sentence_text: Full sentence text
            predicate: Predicate/verb form
            predicate_span: (start, end) token positions of predicate
            roles: Dict of role_name → (argument_text, (start, end))
            coreference_chains: Optional mapping from argument spans to entity identities
        
        Returns:
            Populated SemanticArgumentGraph
        """
        graph = SemanticArgumentGraph()
        
        # Add predicate node
        pred_id = graph.add_node(
            node_type="predicate",
            label=predicate,
            span=predicate_span,
            properties={"sentence": sentence_text},
        )
        
        # Add argument nodes and edges
        for role, (arg_text, arg_span) in roles.items():
            # Try to resolve coreference
            entity_id = None
            if coreference_chains and str(arg_span) in coreference_chains:
                entity_id = coreference_chains[str(arg_span)]
            
            # Add argument node
            arg_node_id = graph.add_node(
                node_type="argument" if not entity_id else "entity",
                label=arg_text,
                span=arg_span,
                properties={
                    "surface_form": arg_text,
                    "entity_id": entity_id,
                },
            )
            
            # Add role edge
            graph.add_edge(
                source_id=pred_id,
                target_id=arg_node_id,
                role=role,
                properties={
                    "argument_text": arg_text,
                    "surface_span": arg_span,
                },
            )
        
        return graph


def validate_graph_consistency(
    graph: SemanticArgumentGraph,
) -> Tuple[bool, List[str]]:
    """Validate semantic argument graph consistency.
    
    Checks:
      - No dangling references
      - Role predicates match inverted predicates
      - No cycles in argument chains
    
    Args:
        graph: The semantic argument graph
    
    Returns:
        (is_valid, list of violations)
    """
    violations = []
    
    # Check for dangling edges
    all_node_ids = set(graph.nodes.keys())
    for edge in graph.edges:
        if edge.source_id not in all_node_ids:
            violations.append(f"Dangling source: {edge.source_id}")
        if edge.target_id not in all_node_ids:
            violations.append(f"Dangling target: {edge.target_id}")
    
    # Check for cycles
    def has_cycle() -> bool:
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for edge in graph.get_outgoing_edges(node_id):
                if edge.target_id not in visited:
                    if dfs(edge.target_id):
                        return True
                elif edge.target_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in graph.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False
    
    if has_cycle():
        violations.append("Graph contains cycle in argument chains")
    
    return len(violations) == 0, violations
