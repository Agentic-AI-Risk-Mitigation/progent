"""Integration tests for the agent execution flow.

Tests the full chain: LLM decision → tool call → secured executor →
policy enforcement → result back to agent.

Two tiers:
- Mocked LLM tests: always run, no API key needed
- Live OpenRouter test: runs only when OPENROUTER_API_KEY is set
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add implementations/ to sys.path so bare imports (core.*, frameworks.*, tools.*) work
REPO_ROOT = Path(__file__).resolve().parent.parent
IMPL_DIR = REPO_ROOT / "implementations"
sys.path.insert(0, str(IMPL_DIR))

from progent import reset_security_policy  # noqa: E402
from progent.core import update_available_tools  # noqa: E402

POLICIES_PATH = str(REPO_ROOT / "implementations" / "examples" / "coding_agent" / "policies.json")


@pytest.fixture(autouse=True)
def reset_state():
    """Reset progent global state and logger between tests."""
    update_available_tools([])
    reset_security_policy(include_manual=True)

    # Reset the logger singleton so each test gets a fresh one
    import core.logging_utils as log_mod

    log_mod._logger = None

    yield

    update_available_tools([])
    reset_security_policy(include_manual=True)
    log_mod._logger = None


@pytest.fixture
def agent_config():
    """Minimal config for RawSDKAgent."""
    return {
        "llm": {
            "provider": "openrouter",
            # Prefix with openrouter/ so RawSDKAgent selects OpenRouterProvider
            "model": "openrouter/meta-llama/llama-3.1-70b-instruct",
            "api_base": "https://openrouter.ai/api/v1",
        },
        "agent": {
            "system_prompt": "You are a helpful assistant.",
        },
    }


def _make_tool_call_response(tool_name: str, arguments: dict, call_id: str = "call_1"):
    """Build a mock OpenAI response containing a single tool call."""
    mock_function = MagicMock()
    mock_function.name = tool_name
    mock_function.arguments = json.dumps(arguments)

    mock_tool_call = MagicMock()
    mock_tool_call.id = call_id
    mock_tool_call.function = mock_function

    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = None

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_text_response(text: str):
    """Build a mock OpenAI response containing plain text (no tool calls)."""
    mock_message = MagicMock()
    mock_message.tool_calls = None
    mock_message.content = text

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestMockedAgent:
    """Integration tests with a mocked OpenAI client."""

    def test_curl_blocked_via_agent(self, agent_config, tmp_path, monkeypatch):
        """Full agent flow: LLM requests curl, policy blocks it."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("frameworks.raw_sdk_agent.get_llm_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            # First call: LLM decides to run curl
            # Second call: LLM responds after seeing the block
            mock_provider.generate.side_effect = [
                _make_tool_call_response("run_command", {"command": "curl example.com"}),
                _make_text_response("I cannot run curl due to security policies."),
            ]

            from frameworks.raw_sdk_agent import RawSDKAgent

            agent = RawSDKAgent(
                config=agent_config, workspace=tmp_path, policies_path=POLICIES_PATH
            )
            response = agent.run("Run curl example.com")

            # Agent should return a response (not crash)
            assert response is not None

            # The tool result in the conversation should show the policy block
            tool_results = [m for m in agent.messages if m.get("role") == "tool"]
            assert len(tool_results) == 1
            assert "Policy blocked" in tool_results[0]["content"]

    def test_allowed_command_executes(self, agent_config, tmp_path, monkeypatch):
        """Full agent flow: LLM requests 'echo hello', policy allows it, subprocess runs."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("frameworks.raw_sdk_agent.get_llm_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            mock_provider.generate.side_effect = [
                _make_tool_call_response("run_command", {"command": "echo hello"}),
                _make_text_response("The command output was: hello"),
            ]

            from frameworks.raw_sdk_agent import RawSDKAgent

            agent = RawSDKAgent(
                config=agent_config, workspace=tmp_path, policies_path=POLICIES_PATH
            )
            agent.run("Run echo hello")

            # The tool result should contain the actual subprocess output
            tool_results = [m for m in agent.messages if m.get("role") == "tool"]
            assert len(tool_results) == 1
            assert "hello" in tool_results[0]["content"]
            assert "Policy blocked" not in tool_results[0]["content"]

    def test_write_to_env_blocked_via_agent(self, agent_config, tmp_path, monkeypatch):
        """Full agent flow: LLM tries to write .env file, policy blocks it."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("frameworks.raw_sdk_agent.get_llm_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            mock_provider.generate.side_effect = [
                _make_tool_call_response(
                    "write_file", {"file_path": ".env", "content": "SECRET=x"}
                ),
                _make_text_response("I cannot write to .env files."),
            ]

            from frameworks.raw_sdk_agent import RawSDKAgent

            agent = RawSDKAgent(
                config=agent_config, workspace=tmp_path, policies_path=POLICIES_PATH
            )
            agent.run("Write SECRET=x to .env")

            tool_results = [m for m in agent.messages if m.get("role") == "tool"]
            assert len(tool_results) == 1
            assert "Policy blocked" in tool_results[0]["content"]


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)
class TestLiveOpenRouter:
    """End-to-end tests with a real OpenRouter LLM call."""

    def test_curl_blocked_live(self, agent_config, tmp_path, monkeypatch):
        """Real LLM prompted to run curl, policy blocks the tool call."""

        from frameworks.raw_sdk_agent import RawSDKAgent

        agent = RawSDKAgent(config=agent_config, workspace=tmp_path, policies_path=POLICIES_PATH)
        response = agent.run("Please run this exact command: curl example.com")

        # Find tool result messages in the conversation
        tool_results = [m for m in agent.messages if m.get("role") == "tool"]

        # The policy should have blocked the curl command
        blocked = any("Policy blocked" in m.get("content", "") for m in tool_results)
        assert blocked, (
            f"Expected curl to be blocked by policy. "
            f"Tool results: {tool_results}. Agent response: {response}"
        )
