"""Tests for progent.wrapper module."""

import pytest

from progent.core import (
    get_available_tools,
    reset_security_policy,
    update_available_tools,
    update_security_policy,
)
from progent.exceptions import ProgentBlockedError
from progent.wrapper import apply_secure_tool_wrapper


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    update_available_tools([])
    reset_security_policy(include_manual=True)
    yield
    update_available_tools([])
    reset_security_policy(include_manual=True)


class TestSecureDecorator:
    """Tests for @secure decorator."""

    def test_decorator_basic(self):
        """Test basic decorator usage."""
        # Set up policy that allows the tool
        update_security_policy(
            {
                "greet": [(1, 0, {}, 0)],
            }
        )

        @apply_secure_tool_wrapper
        def greet(name: str) -> str:
            """Greet someone."""
            return f"Hello, {name}!"

        result = greet(name="World")
        assert result == "Hello, World!"

    def test_decorator_registers_tool(self):
        """Test that decorator registers tool."""

        @apply_secure_tool_wrapper
        def my_tool(arg: str) -> str:
            """My tool description."""
            return arg

        tools = get_available_tools()
        tool_names = [t["name"] for t in tools]
        assert "my_tool" in tool_names

    def test_decorator_blocks_when_policy_denies(self):
        """Test that decorator blocks calls when policy denies."""
        update_security_policy(
            {
                "restricted": [(1, 1, {}, 0)],  # Deny all
            }
        )

        @apply_secure_tool_wrapper
        def restricted(data: str) -> str:
            """Restricted operation."""
            return data

        with pytest.raises(ProgentBlockedError):
            restricted(data="test")

    def test_decorator_enforces_conditions(self):
        """Test that decorator enforces policy conditions."""
        update_security_policy(
            {
                "write_data": [
                    (
                        1,
                        0,
                        {
                            "path": {"type": "string", "pattern": "^/safe/"},
                        },
                        0,
                    )
                ],
            }
        )

        @apply_secure_tool_wrapper
        def write_data(path: str, content: str) -> str:
            """Write data to path."""
            return f"Written to {path}"

        # Should pass
        result = write_data(path="/safe/file.txt", content="hello")
        assert "/safe/file.txt" in result

        # Should block
        with pytest.raises(ProgentBlockedError):
            write_data(path="/unsafe/file.txt", content="hello")

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @apply_secure_tool_wrapper
        def my_func(x: int) -> int:
            """My docstring."""
            return x * 2

        # Allow the tool
        update_security_policy({"my_func": [(1, 0, {}, 0)]})

        assert my_func.__name__ == "my_func"
        assert "docstring" in my_func.__doc__

    def test_decorator_with_defaults(self):
        """Test decorator with default arguments."""
        update_security_policy(
            {
                "with_defaults": [(1, 0, {}, 0)],
            }
        )

        @apply_secure_tool_wrapper
        def with_defaults(required: str, optional: str = "default") -> str:
            """Function with defaults."""
            return f"{required}-{optional}"

        result = with_defaults(required="test")
        assert result == "test-default"

        result = with_defaults(required="test", optional="custom")
        assert result == "test-custom"


class TestSecureFunction:
    """Tests for secure() function."""

    def test_wrap_single_function(self):
        """Test wrapping a single function."""

        def my_tool(x: str) -> str:
            return x.upper()

        update_security_policy({"my_tool": [(1, 0, {}, 0)]})

        wrapped = apply_secure_tool_wrapper(my_tool)
        result = wrapped(x="hello")
        assert result == "HELLO"

    def test_wrap_list_of_functions(self):
        """Test wrapping a list of functions."""

        def tool1(a: str) -> str:
            return a

        def tool2(b: str) -> str:
            return b

        update_security_policy(
            {
                "tool1": [(1, 0, {}, 0)],
                "tool2": [(1, 0, {}, 0)],
            }
        )

        wrapped = apply_secure_tool_wrapper([tool1, tool2])

        assert len(wrapped) == 2
        assert wrapped[0](a="test1") == "test1"
        assert wrapped[1](b="test2") == "test2"


class TestToolDefinitionExtraction:
    """Tests for tool definition extraction."""

    def test_extracts_description_from_docstring(self):
        """Test that description is extracted from docstring."""

        @apply_secure_tool_wrapper
        def described_tool(x: str) -> str:
            """This is the tool description.

            More details here.
            """
            return x

        tools = get_available_tools()
        tool = next(t for t in tools if t["name"] == "described_tool")
        assert "This is the tool description" in tool["description"]

    def test_extracts_parameter_types(self):
        """Test that parameter types are extracted."""

        @apply_secure_tool_wrapper
        def typed_tool(name: str, count: int, active: bool) -> str:
            """A typed tool."""
            return f"{name}: {count}, {active}"

        tools = get_available_tools()
        tool = next(t for t in tools if t["name"] == "typed_tool")

        assert "name" in tool["args"]
        assert "count" in tool["args"]
        assert "active" in tool["args"]

    def test_handles_missing_docstring(self):
        """Test handling of missing docstring."""

        @apply_secure_tool_wrapper
        def no_docs(x: str) -> str:
            return x

        tools = get_available_tools()
        tool = next(t for t in tools if t["name"] == "no_docs")
        # Should use function name as fallback description
        assert tool["description"] is not None
