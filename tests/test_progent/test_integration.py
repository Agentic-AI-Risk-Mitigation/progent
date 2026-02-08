"""Integration tests for progent library."""

import json
import tempfile
from pathlib import Path

import pytest

from progent import (
    ProgentBlockedError,
    check_tool_call,
    load_policies,
    reset_security_policy,
    apply_secure_tool_wrapper,
    update_available_tools,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    update_available_tools([])
    reset_security_policy(include_manual=True)
    yield
    update_available_tools([])
    reset_security_policy(include_manual=True)


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_basic_workflow(self):
        """Test basic workflow: load policies, wrap tools, execute."""
        # 1. Define policies
        policies = {
            "send_email": [
                {
                    "priority": 1,
                    "effect": 0,
                    "conditions": {
                        "to": {"type": "string", "pattern": r".*@company\.com$"},
                    },
                    "fallback": 0,
                }
            ],
            "read_file": [
                {
                    "priority": 1,
                    "effect": 0,
                    "conditions": {
                        "path": {"type": "string", "pattern": r"^/safe/"},
                    },
                    "fallback": 0,
                }
            ],
        }

        # 2. Load policies
        load_policies(policies)

        # 3. Define and wrap tools
        @apply_secure_tool_wrapper
        def send_email(to: str, subject: str, body: str) -> str:
            """Send an email."""
            return f"Email sent to {to}"

        @apply_secure_tool_wrapper
        def read_file(path: str) -> str:
            """Read a file."""
            return f"Contents of {path}"

        # 4. Test allowed operations
        result = send_email(to="user@company.com", subject="Hi", body="Hello")
        assert "user@company.com" in result

        result = read_file(path="/safe/document.txt")
        assert "/safe/document.txt" in result

        # 5. Test blocked operations
        with pytest.raises(ProgentBlockedError):
            send_email(to="user@external.com", subject="Hi", body="Hello")

        with pytest.raises(ProgentBlockedError):
            read_file(path="/secret/passwords.txt")

    def test_workflow_with_file(self):
        """Test workflow loading policies from file."""
        policies = {
            "calculator": [
                {
                    "priority": 1,
                    "effect": 0,
                    "conditions": {
                        "operation": {"type": "string", "enum": ["add", "subtract"]},
                    },
                    "fallback": 0,
                }
            ],
        }

        # Write policies to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(policies, f)
            temp_path = f.name

        try:
            # Load from file
            load_policies(temp_path)

            @apply_secure_tool_wrapper
            def calculator(operation: str, a: float, b: float) -> float:
                """Perform calculation."""
                if operation == "add":
                    return a + b
                elif operation == "subtract":
                    return a - b
                else:
                    raise ValueError(f"Unknown operation: {operation}")

            # Allowed
            assert calculator(operation="add", a=1, b=2) == 3
            assert calculator(operation="subtract", a=5, b=3) == 2

            # Blocked
            with pytest.raises(ProgentBlockedError):
                calculator(operation="multiply", a=2, b=3)

        finally:
            Path(temp_path).unlink()

    def test_multiple_rules_priority(self):
        """Test multiple rules with different priorities."""
        policies = {
            "action": [
                # Higher priority allow for admin paths
                {
                    "priority": 1,
                    "effect": 0,
                    "conditions": {
                        "path": {"type": "string", "pattern": "^/admin/"},
                    },
                    "fallback": 0,
                },
                # Lower priority allow for user paths
                {
                    "priority": 2,
                    "effect": 0,
                    "conditions": {
                        "path": {"type": "string", "pattern": "^/user/"},
                    },
                    "fallback": 0,
                },
                # Deny everything else
                {"priority": 3, "effect": 1, "conditions": {}, "fallback": 0},
            ],
        }

        load_policies(policies)

        @apply_secure_tool_wrapper
        def action(path: str) -> str:
            """Perform action."""
            return f"Action on {path}"

        # Allowed by rule 1
        assert "admin" in action(path="/admin/settings")

        # Allowed by rule 2
        assert "user" in action(path="/user/profile")

        # Blocked by rule 3
        with pytest.raises(ProgentBlockedError):
            action(path="/other/path")

    def test_manual_check_tool_call(self):
        """Test using check_tool_call directly."""
        load_policies(
            {
                "api_call": [
                    {
                        "priority": 1,
                        "effect": 0,
                        "conditions": {
                            "endpoint": {"type": "string", "pattern": "^/api/v1/"},
                            "method": {"type": "string", "enum": ["GET", "POST"]},
                        },
                        "fallback": 0,
                    }
                ],
            }
        )

        # Check without executing
        check_tool_call("api_call", {"endpoint": "/api/v1/users", "method": "GET"})

        with pytest.raises(ProgentBlockedError):
            check_tool_call("api_call", {"endpoint": "/internal/admin", "method": "GET"})

        with pytest.raises(ProgentBlockedError):
            check_tool_call("api_call", {"endpoint": "/api/v1/users", "method": "DELETE"})


class TestComplexRestrictions:
    """Tests for complex policy restrictions."""

    def test_combined_string_restrictions(self):
        """Test combining multiple string restrictions."""
        load_policies(
            {
                "create_user": [
                    {
                        "priority": 1,
                        "effect": 0,
                        "conditions": {
                            "username": {
                                "type": "string",
                                "minLength": 3,
                                "maxLength": 20,
                                "pattern": "^[a-z][a-z0-9_]*$",
                            },
                        },
                        "fallback": 0,
                    }
                ],
            }
        )

        @apply_secure_tool_wrapper
        def create_user(username: str) -> str:
            """Create a user."""
            return f"Created {username}"

        # Valid usernames
        assert "admin" in create_user(username="admin")
        assert "user123" in create_user(username="user123")
        assert "test_user" in create_user(username="test_user")

        # Too short
        with pytest.raises(ProgentBlockedError):
            create_user(username="ab")

        # Too long
        with pytest.raises(ProgentBlockedError):
            create_user(username="this_username_is_way_too_long")

        # Invalid characters
        with pytest.raises(ProgentBlockedError):
            create_user(username="user@name")

        # Starts with number
        with pytest.raises(ProgentBlockedError):
            create_user(username="123user")

    def test_numeric_range_restrictions(self):
        """Test numeric range restrictions."""
        load_policies(
            {
                "set_volume": [
                    {
                        "priority": 1,
                        "effect": 0,
                        "conditions": {
                            "level": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 100,
                            },
                        },
                        "fallback": 0,
                    }
                ],
            }
        )

        @apply_secure_tool_wrapper
        def set_volume(level: int) -> str:
            """Set volume level."""
            return f"Volume set to {level}"

        assert "50" in set_volume(level=50)
        assert "0" in set_volume(level=0)
        assert "100" in set_volume(level=100)

        with pytest.raises(ProgentBlockedError):
            set_volume(level=-1)

        with pytest.raises(ProgentBlockedError):
            set_volume(level=101)

    def test_array_restrictions(self):
        """Test array item restrictions."""
        load_policies(
            {
                "process_tags": [
                    {
                        "priority": 1,
                        "effect": 0,
                        "conditions": {
                            "tags": {
                                "type": "array",
                                "items": {"type": "string", "pattern": "^[a-z]+$"},
                                "minItems": 1,
                                "maxItems": 5,
                            },
                        },
                        "fallback": 0,
                    }
                ],
            }
        )

        @apply_secure_tool_wrapper
        def process_tags(tags: list) -> str:
            """Process tags."""
            return f"Processed {len(tags)} tags"

        # Valid
        assert "1 tags" in process_tags(tags=["one"])
        assert "3 tags" in process_tags(tags=["one", "two", "three"])

        # Invalid item type
        with pytest.raises(ProgentBlockedError):
            process_tags(tags=["valid", 123])

        # Invalid item pattern
        with pytest.raises(ProgentBlockedError):
            process_tags(tags=["UPPERCASE"])

        # Too few items
        with pytest.raises(ProgentBlockedError):
            process_tags(tags=[])

        # Too many items
        with pytest.raises(ProgentBlockedError):
            process_tags(tags=["a", "b", "c", "d", "e", "f"])
