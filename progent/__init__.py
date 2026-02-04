"""
Progent - Programmable Privilege Control for LLM Agents.

A framework-agnostic library for enforcing fine-grained security policies
on AI agent tool calls using JSON Schema validation.

Basic Usage:
    from progent import secure, load_policies

    # Load policies from file or dict
    load_policies("policies.json")

    # Option 1: Use as decorator
    @secure
    def my_tool(arg: str) -> str:
        return f"Executed with {arg}"

    # Option 2: Wrap existing functions/tools
    tools = secure([tool1, tool2, tool3])

    # Option 3: Check manually
    from progent import check_tool_call
    check_tool_call("my_tool", {"arg": "value"})
"""

from progent.core import (
    check_tool_call,
    get_available_tools,
    get_security_policy,
    reset_security_policy,
    update_always_allowed_tools,
    update_always_blocked_tools,
    update_available_tools,
    update_security_policy,
)
from progent.exceptions import PolicyValidationError, ProgentBlockedError
from progent.policy import load_policies
from progent.wrapper import secure, secure_tool_wrapper

__version__ = "0.1.0"

__all__ = [
    # Core
    "check_tool_call",
    "get_security_policy",
    "get_available_tools",
    "update_security_policy",
    "update_available_tools",
    "update_always_allowed_tools",
    "update_always_blocked_tools",
    "reset_security_policy",
    # Policy loading
    "load_policies",
    # Wrapper/decorator
    "secure",
    "secure_tool_wrapper",
    # Exceptions
    "ProgentBlockedError",
    "PolicyValidationError",
]
