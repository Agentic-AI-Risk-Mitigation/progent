"""
Tests for progent.analysis module.
"""

import pytest

# Skip all tests if z3 is not installed
z3 = pytest.importorskip("z3")


class TestAnalyzePolicies:
    """Tests for analyze_policies function."""

    def test_empty_policies(self):
        """Test analyzing empty policies."""
        from progent.analysis import analyze_policies

        warnings = analyze_policies({})
        assert warnings == []

    def test_none_policies(self):
        """Test analyzing None policies."""
        from progent.analysis import analyze_policies

        warnings = analyze_policies(None)
        assert warnings == []

    def test_no_overlap_different_enum(self):
        """Test policies with non-overlapping enum values."""
        from progent.analysis import analyze_policies

        policies = {
            "tool": [
                (1, 0, {"arg": {"type": "string", "enum": ["abc"]}}, 0),
                (2, 0, {"arg": {"type": "string", "enum": ["xyz"]}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        # These enums don't overlap
        assert len(warnings) == 0

    def test_overlap_detected_patterns(self):
        """Test detection of overlapping patterns."""
        from progent.analysis import analyze_policies

        policies = {
            "send_email": [
                (1, 0, {"recipient": {"type": "string", "pattern": ".*@example.com"}}, 0),
                (2, 1, {"recipient": {"type": "string", "pattern": "test@example.com"}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        assert len(warnings) == 1
        assert "overlap" in warnings[0].lower()

    def test_overlap_integer_range(self):
        """Test detection of overlapping integer ranges."""
        from progent.analysis import analyze_policies

        policies = {
            "transfer": [
                (1, 0, {"amount": {"type": "integer", "minimum": 0, "maximum": 100}}, 0),
                (2, 0, {"amount": {"type": "integer", "minimum": 50, "maximum": 200}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        # Ranges 0-100 and 50-200 overlap at 50-100
        assert len(warnings) == 1
        assert "overlap" in warnings[0].lower()

    def test_no_overlap_integer_range(self):
        """Test non-overlapping integer ranges."""
        from progent.analysis import analyze_policies

        policies = {
            "transfer": [
                (1, 0, {"amount": {"type": "integer", "minimum": 0, "maximum": 50}}, 0),
                (2, 0, {"amount": {"type": "integer", "minimum": 100, "maximum": 200}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        # Ranges 0-50 and 100-200 don't overlap
        assert len(warnings) == 0

    def test_overlap_enum(self):
        """Test detection of overlapping enum values."""
        from progent.analysis import analyze_policies

        policies = {
            "action": [
                (1, 0, {"type": {"type": "string", "enum": ["read", "write", "delete"]}}, 0),
                (2, 0, {"type": {"type": "string", "enum": ["write", "execute"]}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        # Both have "write"
        assert len(warnings) == 1


class TestSchemaOverlap:
    """Tests for check_schema_overlap function."""

    def test_overlapping_string_patterns(self):
        """Test overlapping string patterns."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "pattern": "[a-z]+"}
        schema_b = {"type": "string", "minLength": 1, "maxLength": 10}

        result = check_schema_overlap(schema_a, schema_b)
        # Should find a value like "a" that satisfies both
        assert result is not None

    def test_non_overlapping_enum(self):
        """Test non-overlapping enums."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "enum": ["a", "b"]}
        schema_b = {"type": "string", "enum": ["c", "d"]}

        result = check_schema_overlap(schema_a, schema_b)
        assert result is None

    def test_overlapping_enum(self):
        """Test overlapping enums."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "enum": ["a", "b", "c"]}
        schema_b = {"type": "string", "enum": ["b", "c", "d"]}

        result = check_schema_overlap(schema_a, schema_b)
        assert result is not None


class TestArraySupport:
    """Tests for array type support."""

    def test_array_overlap(self):
        """Test overlapping array constraints."""
        from progent.analysis import analyze_policies

        policies = {
            "update": [
                (1, 0, {"items": {"type": "array", "items": {"type": "string"}, "minItems": 1}}, 0),
                (2, 0, {"items": {"type": "array", "items": {"type": "string"}, "maxItems": 5}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        # Arrays with 1-5 items satisfy both
        assert len(warnings) == 1

    def test_array_no_overlap(self):
        """Test non-overlapping array constraints."""
        from progent.analysis import analyze_policies

        policies = {
            "update": [
                (
                    1,
                    0,
                    {"items": {"type": "array", "items": {"type": "string"}, "minItems": 10}},
                    0,
                ),
                (2, 0, {"items": {"type": "array", "items": {"type": "string"}, "maxItems": 5}}, 0),
            ]
        }
        warnings = analyze_policies(policies)
        # Can't have array with both minItems=10 and maxItems=5
        assert len(warnings) == 0


class TestRegexConversion:
    """Tests for regex to Z3 conversion."""

    def test_simple_literal(self):
        """Test simple literal pattern."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "pattern": "abc"}
        schema_b = {"type": "string", "pattern": "abc"}

        result = check_schema_overlap(schema_a, schema_b)
        assert result is not None

    def test_character_class(self):
        """Test character class pattern."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "pattern": "[a-z]+"}
        schema_b = {"type": "string", "pattern": "[abc]+"}

        result = check_schema_overlap(schema_a, schema_b)
        assert result is not None

    def test_digit_class(self):
        """Test digit class pattern."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "pattern": "\\d+"}
        schema_b = {"type": "string", "pattern": "[0-9]+"}

        result = check_schema_overlap(schema_a, schema_b)
        assert result is not None

    def test_alternation(self):
        """Test alternation pattern."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "pattern": "cat|dog"}
        schema_b = {"type": "string", "pattern": "dog|bird"}

        result = check_schema_overlap(schema_a, schema_b)
        # Both match "dog"
        assert result is not None

    def test_kleene_star(self):
        """Test Kleene star pattern."""
        from progent.analysis import check_schema_overlap

        schema_a = {"type": "string", "pattern": "a*"}
        schema_b = {"type": "string", "pattern": ""}

        result = check_schema_overlap(schema_a, schema_b)
        # Empty string matches a*
        assert result is not None


class TestCheckPolicyTypeErrors:
    """Tests for check_policy_type_errors function."""

    def test_valid_policies(self):
        """Test valid policies have no errors."""
        from progent.analysis import check_policy_type_errors

        policies = {
            "tool1": [
                (1, 0, {"arg1": {"type": "string"}}, 0),
            ]
        }
        available_tools = {"tool1": {"arg1": {"type": "string"}}}

        warnings = check_policy_type_errors(policies, available_tools)
        assert len(warnings) == 0

    def test_tool_not_in_available(self):
        """Test warning when tool not in available tools."""
        from progent.analysis import check_policy_type_errors

        policies = {
            "unknown_tool": [
                (1, 0, {"arg1": {"type": "string"}}, 0),
            ]
        }
        available_tools = {"tool1": {"arg1": {"type": "string"}}}

        warnings = check_policy_type_errors(policies, available_tools)
        assert any("unknown_tool" in w and "not in available tools" in w for w in warnings)

    def test_arg_not_in_tool(self):
        """Test warning when argument not in tool."""
        from progent.analysis import check_policy_type_errors

        policies = {
            "tool1": [
                (1, 0, {"unknown_arg": {"type": "string"}}, 0),
            ]
        }
        available_tools = {"tool1": {"arg1": {"type": "string"}}}

        warnings = check_policy_type_errors(policies, available_tools)
        assert any("unknown_arg" in w and "not found" in w for w in warnings)
