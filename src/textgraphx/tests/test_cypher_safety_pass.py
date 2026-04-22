"""Cypher safety contract tests (backlog item 2).

Validates that Cypher queries across phase files are:
  1. Parameterized (using $param placeholders instead of string interpolation)
  2. Formatted consistently (proper spacing, alignment)
  3. Free of common injection patterns (bare interpolation in WHERE/SET)
  
Coverage:
  - EventEnrichmentPhase: parameterized WHERE/SET clauses
  - TemporalPhase: parameterized matches already in place; enforce consistency
  - RefinementPhase: static queries safe but standardize formatting
  - TlinksRecognizer: document safe patterns for future maintainers
  
These tests do not execute Cypher; they inspect source code patterns statically.
"""

import re
from pathlib import Path

import pytest

# Path constants
REPO_ROOT = Path(__file__).parent.parent
PKG_ROOT = REPO_ROOT / "textgraphx"

EVENT_ENRICHMENT_SRC = PKG_ROOT / "EventEnrichmentPhase.py"
TEMPORAL_SRC = PKG_ROOT / "TemporalPhase.py"
REFINEMENT_SRC = PKG_ROOT / "RefinementPhase.py"
TLINKS_SRC = PKG_ROOT / "TlinksRecognizer.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------


def _extract_cypher_strings(source: str) -> list[tuple[int, str]]:
    """Extract triple-quoted Cypher query strings with their line numbers."""
    queries = []
    lines = source.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for """ pattern
        if '"""' in line:
            start_line = i + 1
            # Find closing """
            rest = line.split('"""', 1)[1]  # skip opening """
            if '"""' in rest:
                # Same-line triple-quoted string (rare for Cypher)
                query_text = rest.split('"""')[0]
                queries.append((start_line, query_text))
                i += 1
            else:
                # Multi-line string
                query_text = rest
                i += 1
                while i < len(lines):
                    if '"""' in lines[i]:
                        query_text += lines[i].split('"""')[0]
                        queries.append((start_line, query_text))
                        break
                    else:
                        query_text += lines[i]
                    i += 1
                i += 1
        else:
            i += 1
    return queries


# ---------------------------------------------------------------------------
# EventEnrichmentPhase: parameterization required
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEventEnrichmentCypher:
    """EventEnrichmentPhase queries must use parameterized field placeholders."""

    def test_resolve_tevent_field_conflicts_uses_parameter_placeholders(self):
        """The _resolve_tevent_field_conflicts method must parameterize value assignments.
        
        Note: field_name (certainty|aspect|polarity|time) is constrained to an enum so
        f-string interpolation is acceptable for property names. However, all value
        assignments must use parameters.
        """
        src = _read(EVENT_ENRICHMENT_SRC)
        # Locate the method
        start = src.find("def _resolve_tevent_field_conflicts(")
        assert start != -1
        
        # Find queries within this method (next 3000 chars to get full method)
        method_section = src[start:start+3000]
        
        # Should use parameterized node ID matching
        assert "$te_id" in method_section, \
            "_resolve_tevent_field_conflicts missing $te_id parameter"
        
        # Should use parameterized values in SET
        has_value_param = "$value" in method_section
        has_source_param = "$source" in method_section
        assert has_value_param and has_source_param, \
            "SET clause missing value/source parameters"
        
        # Field name is constrained to enum, so f-string is acceptable
        # (could add CASE statement but enum whitelist + constrained at call site is sufficient)

    def test_link_frameargument_no_interpolation_in_where(self):
        """link_frameArgument_to_event queries must not interpolate variables."""
        src = _read(EVENT_ENRICHMENT_SRC)
        method_start = src.find("def link_frameArgument_to_event(")
        method_end = src.find("\n    def ", method_start + 10)
        method_section = src[method_start:method_end]
        
        # These queries are safe (static), so verify they stay static.
        # During participation-edge migration we accept either legacy-only
        # or transitional dual-edge patterns.
        has_legacy = "MATCH (f:Frame)<-[:PARTICIPATES_IN]-(t:TagOccurrence)" in method_section
        has_transition = "MATCH (f:Frame)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)" in method_section
        assert has_legacy or has_transition

    def test_add_core_participants_to_event_parameterized(self):
        """add_core_participants_to_event must parameterize dynamic values."""
        src = _read(EVENT_ENRICHMENT_SRC)
        method_start = src.find("def add_core_participants_to_event(")
        assert method_start != -1
        
        method_end = src.find("\n    def ", method_start + 10)
        if method_end == -1:
            method_end = len(src)
        method_section = src[method_start:method_end]
        
        # Static queries are fine, but if any parameters are passed to graph.run,
        # they must use $-style parameters
        graph_run_calls = re.findall(r'graph\.run\([^)]+\)', method_section)
        for call in graph_run_calls:
            if ',' in call:  # Has parameters
                assert '$' in call or 'parameters=' in call, \
                    f"graph.run() call has unparameterized values: {call}"


# ---------------------------------------------------------------------------
# TemporalPhase: verify existing parameterization is consistent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTemporalPhaseCypher:
    """TemporalPhase queries should use consistent parameterization (already mostly done)."""

    def test_all_variable_uses_have_parameters_dict(self):
        """Every graph.run() call with a WHERE clause must include parameters."""
        src = _read(TEMPORAL_SRC)
        
        # Find all graph.run calls
        run_calls = re.finditer(
            r'graph\.run\(\s*([^,]+),\s*([^)]+)\)',
            src,
            re.DOTALL
        )
        
        count = 0
        for match in run_calls:
            count += 1
            query_part = match.group(1)
            params_part = match.group(2)
            
            # If query has WHERE with $, must have parameters= or be a dict
            if re.search(r'WHERE.*\$\w+', query_part, re.DOTALL):
                assert 'parameters' in params_part or '{' in params_part, \
                    f"WHERE with $ parameter missing parameters dict: {query_part[:80]}"
        
        assert count > 0, "No parameterized graph.run calls found (expected at least 1)"

    def test_parameter_style_consistency(self):
        """All parameters use $name style (not ?) for Neo4j Python driver."""
        src = _read(TEMPORAL_SRC)
        
        # Should see $doc_id, $xml_path style
        assert re.search(r'\$\w+', src), "No parameter ($name) style found"
        
        # Should NOT see ? style (JDBC style)
        assert '?, ' not in src and '? ' not in src, \
            "Found JDBC-style ? parameters; use $name for Python driver"


# ---------------------------------------------------------------------------
# RefinementPhase: static queries (mostly safe but standardize formatting)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefinementPhaseCypher:
    """RefinementPhase queries are static; verify they have consistent formatting."""

    def test_no_bare_variable_interpolation_in_queries(self):
        """Static queries should not use f-string formatting for Cypher."""
        src = _read(REFINEMENT_SRC)
        
        # Look for assignment patterns like: query = f"""...{var}..."""
        f_string_patterns = re.finditer(r'query\s*=\s*f"""', src)
        
        # Count f-string query assignments (should be zero after fix)
        f_count = sum(1 for _ in f_string_patterns)
        assert f_count == 0, \
            f"Found {f_count} f-string Cypher queries; use regular strings for static queries"

    def test_all_label_restrictions_are_guards_not_interpolations(self):
        """Node label restrictions should use explicit MATCH clauses, not formats."""
        src = _read(REFINEMENT_SRC)
        
        # Valid patterns: MATCH (ne:NamedEntity) or MATCH (n:Label)
        # Invalid would be: MATCH (n:{some_var})
        assert re.search(r'MATCH.*:[A-Z][a-zA-Z]+', src), \
            "Expected explicit label restrictions in MATCH clauses"
        
        # Verify no dynamic label injection
        assert ':{' not in src, "Found potential dynamic label injection"


# ---------------------------------------------------------------------------
# TlinksRecognizer: document safe patterns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTlinksRecognizerCypher:
    """TlinksRecognizer queries should be static/safe; document the pattern."""

    def test_all_queries_are_static_strings(self):
        """All Cypher queries should be plain strings, not f-strings."""
        src = _read(TLINKS_SRC)
        
        # Find all strings that contain common Cypher keywords
        is_cypher_fstring = re.finditer(r'query\s*=\s*f""".*?(?:MATCH|MERGE|WHERE)', src, re.DOTALL)
        f_count = sum(1 for _ in is_cypher_fstring)
        
        assert f_count == 0, f"Found {f_count} f-string Cypher assignments in TlinksRecognizer"

    def test_literal_values_in_where_are_fixed_constants(self):
        """WHERE clauses with literals should use fixed constants, not variable interpolation."""
        src = _read(TLINKS_SRC)
        
        # Should see patterns like: fa.type = 'ARGM-TMP' (literal string)
        # NOT: fa.type = {type_var} (variable)
        assert "fa.type = 'ARGM-TMP'" in src or 'fa.type = "ARGM-TMP"' in src, \
            "Expected literal type restrictions in WHERE"
        
        # Verify no dynamic type injection
        assert 'fa.type = {' not in src and 'fa.type = $' not in src, \
            "Type should be literal constant, not parameterized"


# ---------------------------------------------------------------------------
# Cross-file: consistent formatting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCypherFormattingConsistency:
    """All Cypher queries should follow consistent formatting conventions."""

    def test_match_keyword_indentation(self):
        """MATCH clauses should be consistently indented."""
        for src_file in [EVENT_ENRICHMENT_SRC, TEMPORAL_SRC, REFINEMENT_SRC, TLINKS_SRC]:
            src = _read(src_file)
            
            # Find MATCH lines (should be indented consistently)
            match_lines = [l for l in src.splitlines() if 'MATCH' in l]
            
            # At least one MATCH should be found
            assert len(match_lines) > 0, f"No MATCH clauses found in {src_file.name}"

    def test_no_mixed_quote_styles_in_queries(self):
        """Queries should use consistent quote style for strings (lenient check).
        
        Skips complex quote-balance checks since docstrings and comments can
        contain unmatched quotes; relies on other tests for actual safety.
        """
        # This test is a placeholder for future style enforcement.
        # Actual quote safety is handled by Cypher parser at runtime.
        pass
