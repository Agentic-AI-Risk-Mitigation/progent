"""Tests for progent.policy module."""

import json
import tempfile
from pathlib import Path

import pytest

from progent.core import get_security_policy, reset_security_policy
from progent.exceptions import PolicyLoadError
from progent.policy import (
    load_policies,
    save_policies,
    validate_policies,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    reset_security_policy(include_manual=True)
    yield
    reset_security_policy(include_manual=True)


class TestLoadPolicies:
    """Tests for load_policies function."""

    def test_load_from_dict_progent_format(self):
        """Test loading policies from dict in Progent format."""
        policies_dict = {
            "tool1": [
                {
                    "priority": 1,
                    "effect": 0,
                    "conditions": {"arg": {"type": "string"}},
                    "fallback": 0,
                }
            ],
        }

        result = load_policies(policies_dict)

        assert "tool1" in result
        assert result["tool1"][0] == (1, 0, {"arg": {"type": "string"}}, 0)

    def test_load_from_dict_simple_format(self):
        """Test loading policies from dict in simple format."""
        policies_dict = {
            "tool1": {
                "arg": {"type": "string", "pattern": "^test"},
            },
        }

        result = load_policies(policies_dict)

        assert "tool1" in result
        assert result["tool1"][0][2] == {"arg": {"type": "string", "pattern": "^test"}}

    def test_load_from_file(self):
        """Test loading policies from JSON file."""
        policies_dict = {
            "read_file": [
                {
                    "priority": 1,
                    "effect": 0,
                    "conditions": {"path": {"type": "string", "pattern": "^/safe/"}},
                    "fallback": 0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(policies_dict, f)
            temp_path = f.name

        try:
            result = load_policies(temp_path)
            assert "read_file" in result
        finally:
            Path(temp_path).unlink()

    def test_load_from_path_object(self):
        """Test loading policies from Path object."""
        policies_dict = {"tool1": [{"priority": 1, "effect": 0, "conditions": {}, "fallback": 0}]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(policies_dict, f)
            temp_path = Path(f.name)

        try:
            result = load_policies(temp_path)
            assert "tool1" in result
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(PolicyLoadError):
            load_policies("/nonexistent/path/policies.json")

    def test_load_invalid_json(self):
        """Test loading invalid JSON raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            temp_path = f.name

        try:
            with pytest.raises(PolicyLoadError):
                load_policies(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_applies_to_core(self):
        """Test that load_policies applies to core state."""
        policies_dict = {
            "my_tool": [{"priority": 1, "effect": 0, "conditions": {}, "fallback": 0}],
        }

        load_policies(policies_dict)

        core_policy = get_security_policy()
        assert "my_tool" in core_policy


class TestSavePolicies:
    """Tests for save_policies function."""

    def test_save_and_reload(self):
        """Test saving and reloading policies."""
        original = {
            "tool1": [(1, 0, {"arg": {"type": "string"}}, 0)],
            "tool2": [(2, 1, {"x": {"type": "integer"}}, 1)],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_policies(original, temp_path)

            # Reload and verify
            with open(temp_path) as f:
                loaded = json.load(f)

            assert "tool1" in loaded
            assert "tool2" in loaded
            assert loaded["tool1"][0]["priority"] == 1
            assert loaded["tool2"][0]["effect"] == 1
        finally:
            Path(temp_path).unlink()


class TestValidatePolicies:
    """Tests for validate_policies function."""

    def test_valid_policies(self):
        """Test validation of valid policies."""
        policies = {
            "tool1": [(1, 0, {"arg": {"type": "string", "minLength": 1}}, 0)],
        }

        warnings = validate_policies(policies)
        assert len(warnings) == 0

    def test_invalid_schema_keyword(self):
        """Test detection of invalid schema keywords."""
        policies = {
            "tool1": [
                (
                    1,
                    0,
                    {
                        "arg": {
                            "type": "integer",
                            "pattern": "^test$",
                        }  # pattern invalid for integer
                    },
                    0,
                )
            ],
        }

        warnings = validate_policies(policies)
        assert len(warnings) > 0
        assert any("pattern" in w for w in warnings)

    def test_invalid_rule_format(self):
        """Test detection of invalid rule format."""
        policies = {
            "tool1": ["invalid_rule"],
        }

        warnings = validate_policies(policies)
        assert len(warnings) > 0
