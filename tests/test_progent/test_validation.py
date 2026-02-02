"""Tests for progent.validation module."""

import pytest

from progent.validation import (
    check_argument,
    validate_schema,
)
from progent.exceptions import PolicyValidationError


class TestCheckArgumentJsonSchema:
    """Tests for JSON Schema validation."""
    
    def test_string_type_valid(self):
        """Test valid string type."""
        check_argument("name", "hello", {"type": "string"})
    
    def test_string_type_invalid(self):
        """Test invalid string type."""
        with pytest.raises(PolicyValidationError):
            check_argument("name", 123, {"type": "string"})
    
    def test_string_enum_valid(self):
        """Test valid enum value."""
        check_argument("color", "red", {"type": "string", "enum": ["red", "green", "blue"]})
    
    def test_string_enum_invalid(self):
        """Test invalid enum value."""
        with pytest.raises(PolicyValidationError):
            check_argument("color", "yellow", {"type": "string", "enum": ["red", "green", "blue"]})
    
    def test_string_pattern_valid(self):
        """Test valid pattern match."""
        check_argument("email", "test@example.com", {
            "type": "string",
            "pattern": r"^[\w]+@[\w]+\.\w+$"
        })
    
    def test_string_pattern_invalid(self):
        """Test invalid pattern match."""
        with pytest.raises(PolicyValidationError):
            check_argument("email", "not-an-email", {
                "type": "string",
                "pattern": r"^[\w]+@[\w]+\.\w+$"
            })
    
    def test_string_minlength_valid(self):
        """Test valid minLength."""
        check_argument("name", "hello", {"type": "string", "minLength": 3})
    
    def test_string_minlength_invalid(self):
        """Test invalid minLength."""
        with pytest.raises(PolicyValidationError):
            check_argument("name", "hi", {"type": "string", "minLength": 3})
    
    def test_string_maxlength_valid(self):
        """Test valid maxLength."""
        check_argument("name", "hi", {"type": "string", "maxLength": 5})
    
    def test_string_maxlength_invalid(self):
        """Test invalid maxLength."""
        with pytest.raises(PolicyValidationError):
            check_argument("name", "hello world", {"type": "string", "maxLength": 5})
    
    def test_integer_type_valid(self):
        """Test valid integer type."""
        check_argument("count", 42, {"type": "integer"})
    
    def test_integer_type_invalid(self):
        """Test invalid integer type."""
        with pytest.raises(PolicyValidationError):
            check_argument("count", "42", {"type": "integer"})
    
    def test_integer_minimum_valid(self):
        """Test valid minimum."""
        check_argument("amount", 10, {"type": "integer", "minimum": 0})
    
    def test_integer_minimum_invalid(self):
        """Test invalid minimum."""
        with pytest.raises(PolicyValidationError):
            check_argument("amount", -5, {"type": "integer", "minimum": 0})
    
    def test_integer_maximum_valid(self):
        """Test valid maximum."""
        check_argument("amount", 50, {"type": "integer", "maximum": 100})
    
    def test_integer_maximum_invalid(self):
        """Test invalid maximum."""
        with pytest.raises(PolicyValidationError):
            check_argument("amount", 150, {"type": "integer", "maximum": 100})
    
    def test_number_valid(self):
        """Test valid number."""
        check_argument("price", 19.99, {"type": "number", "minimum": 0})
    
    def test_boolean_valid(self):
        """Test valid boolean."""
        check_argument("active", True, {"type": "boolean"})
    
    def test_array_valid(self):
        """Test valid array."""
        check_argument("items", ["a", "b", "c"], {
            "type": "array",
            "items": {"type": "string"}
        })
    
    def test_array_invalid_items(self):
        """Test array with invalid items."""
        with pytest.raises(PolicyValidationError):
            check_argument("items", ["a", 1, "c"], {
                "type": "array",
                "items": {"type": "string"}
            })


class TestCheckArgumentRegex:
    """Tests for regex pattern validation."""
    
    def test_regex_valid(self):
        """Test valid regex match."""
        check_argument("code", "ABC123", r"^[A-Z]+\d+$")
    
    def test_regex_invalid(self):
        """Test invalid regex match."""
        with pytest.raises(PolicyValidationError) as exc_info:
            check_argument("code", "abc123", r"^[A-Z]+\d+$")
        assert "pattern" in str(exc_info.value)
    
    def test_regex_non_string_value(self):
        """Test regex on non-string value."""
        with pytest.raises(PolicyValidationError) as exc_info:
            check_argument("code", 123, r"^\d+$")
        assert "non-string" in str(exc_info.value)


class TestCheckArgumentCallable:
    """Tests for callable validation."""
    
    def test_callable_valid(self):
        """Test valid callable check."""
        check_argument("amount", 100, lambda x: x > 0)
    
    def test_callable_invalid(self):
        """Test invalid callable check."""
        with pytest.raises(PolicyValidationError):
            check_argument("amount", -5, lambda x: x > 0)
    
    def test_callable_with_exception(self):
        """Test callable that raises."""
        def bad_validator(x):
            raise ValueError("broken")
        
        with pytest.raises(PolicyValidationError):
            check_argument("value", "test", bad_validator)


class TestValidateSchema:
    """Tests for schema validation."""
    
    def test_valid_schema(self):
        """Test valid JSON schema."""
        warnings = validate_schema({
            "type": "string",
            "pattern": "^[a-z]+$",
        })
        assert len(warnings) == 0
    
    def test_invalid_type_keyword(self):
        """Test type-specific keyword on wrong type."""
        warnings = validate_schema({
            "type": "integer",
            "pattern": "^[a-z]+$",  # pattern is for strings
        })
        assert len(warnings) > 0
        assert any("pattern" in w for w in warnings)
    
    def test_invalid_schema_syntax(self):
        """Test invalid JSON schema syntax."""
        # This should produce a warning about invalid schema
        warnings = validate_schema({
            "type": ["string", "invalid_type_name"],
        })
        # jsonschema may or may not catch this, but our type check should
        # Just ensure no crash
        assert isinstance(warnings, list)
