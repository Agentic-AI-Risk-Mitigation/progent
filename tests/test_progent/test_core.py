"""Tests for progent.core module."""

import pytest

from progent.core import (
    Tool,
    check_tool_call,
    get_available_tools,
    get_security_policy,
    reset_security_policy,
    update_always_allowed_tools,
    update_always_blocked_tools,
    update_available_tools,
    update_security_policy,
)
from progent.exceptions import ProgentBlockedError


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    # Reset to clean state
    update_available_tools([])
    reset_security_policy(include_manual=True)
    yield
    # Clean up after test
    update_available_tools([])
    reset_security_policy(include_manual=True)


class TestToolRegistration:
    """Tests for tool registration."""

    def test_update_and_get_tools(self):
        """Test updating and getting available tools."""
        tools = [
            Tool(name="tool1", description="First tool", args={}),
            Tool(name="tool2", description="Second tool", args={"param": {"type": "string"}}),
        ]

        update_available_tools(tools)
        result = get_available_tools()

        assert len(result) == 2
        assert result[0]["name"] == "tool1"
        assert result[1]["name"] == "tool2"

    def test_get_tools_returns_copy(self):
        """Test that get_available_tools returns a copy."""
        tools = [Tool(name="tool1", description="Test", args={})]
        update_available_tools(tools)

        result = get_available_tools()
        result.append(Tool(name="tool2", description="Added", args={}))

        # Original should be unchanged
        assert len(get_available_tools()) == 1


class TestPolicyManagement:
    """Tests for policy management."""

    def test_update_and_get_policy(self):
        """Test updating and getting security policy."""
        policy = {
            "tool1": [(1, 0, {}, 0)],
            "tool2": [(1, 0, {"arg": {"type": "string"}}, 0)],
        }

        update_security_policy(policy)
        result = get_security_policy()

        assert "tool1" in result
        assert "tool2" in result

    def test_get_policy_returns_copy(self):
        """Test that get_security_policy returns a copy."""
        policy = {"tool1": [(1, 0, {}, 0)]}
        update_security_policy(policy)

        result = get_security_policy()
        result["tool2"] = [(1, 0, {}, 0)]

        # Original should be unchanged
        assert "tool2" not in get_security_policy()

    def test_reset_policy_full(self):
        """Test full policy reset."""
        policy = {"tool1": [(1, 0, {}, 0)]}
        update_security_policy(policy)

        reset_security_policy(include_manual=True)

        assert get_security_policy() is None

    def test_reset_policy_generated_only(self):
        """Test reset of generated policies only."""
        policy = {
            "tool1": [(1, 0, {}, 0)],  # Manual (priority < 100)
            "tool2": [(100, 0, {}, 0)],  # Generated (priority >= 100)
        }
        update_security_policy(policy)

        reset_security_policy(include_manual=False)

        result = get_security_policy()
        assert "tool1" in result
        assert "tool2" not in result

    def test_always_allowed_tools(self):
        """Test marking tools as always allowed."""
        update_always_allowed_tools(["tool1", "tool2"])

        policy = get_security_policy()
        assert "tool1" in policy
        assert "tool2" in policy
        # Check they have allow rule (effect=0)
        assert policy["tool1"][0][1] == 0

    def test_always_blocked_tools(self):
        """Test marking tools as always blocked."""
        update_always_blocked_tools(["dangerous_tool"])

        policy = get_security_policy()
        assert "dangerous_tool" in policy
        # Check it has deny rule (effect=1)
        assert policy["dangerous_tool"][0][1] == 1


class TestPolicyEnforcement:
    """Tests for policy enforcement."""

    def test_allowed_tool_call(self):
        """Test allowed tool call passes."""
        policy = {
            "my_tool": [(1, 0, {}, 0)],
        }
        update_security_policy(policy)

        # Should not raise
        check_tool_call("my_tool", {"arg": "value"})

    def test_blocked_tool_not_in_policy(self):
        """Test tool not in policy is blocked."""
        policy = {
            "allowed_tool": [(1, 0, {}, 0)],
        }
        update_security_policy(policy)

        with pytest.raises(ProgentBlockedError) as exc_info:
            check_tool_call("unknown_tool", {})

        assert exc_info.value.tool_name == "unknown_tool"

    def test_blocked_tool_explicit_deny(self):
        """Test explicitly denied tool is blocked."""
        policy = {
            "my_tool": [(1, 1, {}, 0)],  # effect=1 means deny
        }
        update_security_policy(policy)

        with pytest.raises(ProgentBlockedError):
            check_tool_call("my_tool", {})

    def test_allowed_with_conditions_match(self):
        """Test allowed tool call with matching conditions."""
        policy = {
            "send_money": [
                (
                    1,
                    0,
                    {
                        "recipient": {"type": "string", "pattern": "^UK"},
                    },
                    0,
                )
            ],
        }
        update_security_policy(policy)

        # Should pass - matches pattern
        check_tool_call("send_money", {"recipient": "UK12345"})

    def test_blocked_with_conditions_mismatch(self):
        """Test blocked tool call with non-matching conditions."""
        policy = {
            "send_money": [
                (
                    1,
                    0,
                    {
                        "recipient": {"type": "string", "pattern": "^UK"},
                    },
                    0,
                )
            ],
        }
        update_security_policy(policy)

        with pytest.raises(ProgentBlockedError):
            check_tool_call("send_money", {"recipient": "US12345"})

    def test_multiple_rules_first_match_wins(self):
        """Test that first matching rule wins."""
        policy = {
            "my_tool": [
                # Rule 1: Allow if arg starts with "good"
                (1, 0, {"arg": {"type": "string", "pattern": "^good"}}, 0),
                # Rule 2: Deny if arg starts with "bad" (lower priority)
                (2, 1, {"arg": {"type": "string", "pattern": "^bad"}}, 0),
            ],
        }
        update_security_policy(policy)

        # "good" matches rule 1 -> allowed
        check_tool_call("my_tool", {"arg": "good_value"})

        # "bad" doesn't match rule 1 but matches rule 2 -> blocked
        with pytest.raises(ProgentBlockedError):
            check_tool_call("my_tool", {"arg": "bad_value"})

    def test_no_policy_allows_by_default(self):
        """Test that no policy set allows calls by default."""
        reset_security_policy(include_manual=True)

        # Should not raise when no policy is set
        check_tool_call("any_tool", {"arg": "value"})

    def test_enum_restriction(self):
        """Test enum restriction."""
        policy = {
            "set_color": [
                (
                    1,
                    0,
                    {
                        "color": {"type": "string", "enum": ["red", "green", "blue"]},
                    },
                    0,
                )
            ],
        }
        update_security_policy(policy)

        check_tool_call("set_color", {"color": "red"})

        with pytest.raises(ProgentBlockedError):
            check_tool_call("set_color", {"color": "yellow"})

    def test_numeric_restriction(self):
        """Test numeric restrictions."""
        policy = {
            "transfer": [
                (
                    1,
                    0,
                    {
                        "amount": {"type": "number", "minimum": 0, "maximum": 1000},
                    },
                    0,
                )
            ],
        }
        update_security_policy(policy)

        check_tool_call("transfer", {"amount": 500})

        with pytest.raises(ProgentBlockedError):
            check_tool_call("transfer", {"amount": 2000})

        with pytest.raises(ProgentBlockedError):
            check_tool_call("transfer", {"amount": -100})
