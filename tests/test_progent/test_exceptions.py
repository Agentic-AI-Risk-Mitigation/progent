"""Tests for progent.exceptions module."""

import pytest

from progent.exceptions import (
    ProgentError,
    ProgentBlockedError,
    PolicyValidationError,
    PolicyLoadError,
    PolicyConfigError,
)


class TestProgentBlockedError:
    """Tests for ProgentBlockedError."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = ProgentBlockedError("my_tool")
        
        assert error.tool_name == "my_tool"
        assert error.arguments == {}
        assert "my_tool" in str(error)
        assert "not allowed" in str(error)
    
    def test_with_arguments(self):
        """Test error with arguments."""
        error = ProgentBlockedError(
            tool_name="send_money",
            arguments={"recipient": "foo", "amount": 100},
        )
        
        assert error.tool_name == "send_money"
        assert error.arguments == {"recipient": "foo", "amount": 100}
    
    def test_with_custom_reason(self):
        """Test error with custom reason."""
        error = ProgentBlockedError(
            tool_name="my_tool",
            reason="Custom reason message",
        )
        
        assert error.reason == "Custom reason message"
        assert str(error) == "Custom reason message"
    
    def test_is_progent_error(self):
        """Test inheritance from ProgentError."""
        error = ProgentBlockedError("tool")
        assert isinstance(error, ProgentError)
        assert isinstance(error, Exception)


class TestPolicyValidationError:
    """Tests for PolicyValidationError."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = PolicyValidationError(
            argument_name="recipient",
            value="invalid@email",
            restriction={"type": "string", "pattern": "^[a-z]+$"},
        )
        
        assert error.argument_name == "recipient"
        assert error.value == "invalid@email"
        assert "recipient" in str(error)
    
    def test_with_custom_message(self):
        """Test error with custom message."""
        error = PolicyValidationError(
            argument_name="amount",
            value=-100,
            restriction={"minimum": 0},
            message="Amount must be non-negative",
        )
        
        assert str(error) == "Amount must be non-negative"
    
    def test_is_progent_error(self):
        """Test inheritance from ProgentError."""
        error = PolicyValidationError("arg", "val", {})
        assert isinstance(error, ProgentError)


class TestOtherErrors:
    """Tests for other error types."""
    
    def test_policy_load_error(self):
        """Test PolicyLoadError."""
        error = PolicyLoadError("File not found")
        assert isinstance(error, ProgentError)
        assert "File not found" in str(error)
    
    def test_policy_config_error(self):
        """Test PolicyConfigError."""
        error = PolicyConfigError("Invalid config")
        assert isinstance(error, ProgentError)
        assert "Invalid config" in str(error)
