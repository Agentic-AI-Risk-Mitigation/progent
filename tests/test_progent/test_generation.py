import json
from unittest.mock import patch

import pytest

from progent.generation import (
    _convert_generated_policies,
    _extract_json,
    generate_policies,
    update_policies_from_result,
)

PROMPT_RESPONSE_JSON = """
```json
[
    {
        "name": "read_file",
        "args": {
            "file_path": {
                "pattern": "^/tmp/safe/.*"
            }
        }
    }
]
```
"""

PLAIN_JSON_RESPONSE = """
[
    {
        "name": "write_file",
        "args": {
            "content": {
                "maxLength": 100
            }
        }
    }
]
"""


@pytest.fixture
def mock_tools():
    return [
        {"name": "read_file", "description": "Read a file", "args": {}},
        {"name": "write_file", "description": "Write a file", "args": {}},
    ]


class TestGeneration:
    def test_extract_json_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        result = _extract_json(PROMPT_RESPONSE_JSON)
        assert isinstance(result, list)
        assert result[0]["name"] == "read_file"

    def test_extract_json_plain(self):
        """Test extracting plain JSON."""
        result = _extract_json(PLAIN_JSON_RESPONSE)
        assert isinstance(result, list)
        assert result[0]["name"] == "write_file"

    def test_extract_json_yes_prefix(self):
        """Test extracting JSON with 'Yes' prefix."""
        text = "Yes " + PLAIN_JSON_RESPONSE
        result = _extract_json(text)
        assert isinstance(result, list)

    def test_convert_policies(self):
        """Test converting generated list to internal policy dict."""
        generated = json.loads(PROMPT_RESPONSE_JSON.replace("```json", "").replace("```", ""))
        policies = _convert_generated_policies(generated)

        assert "read_file" in policies
        rule = policies["read_file"][0]
        # Check rule format: (priority, effect, args, fallback)
        assert rule[0] == 100  # Priority 100 for generated
        assert rule[1] == 0  # Effect 0 (allow)
        assert rule[2]["file_path"]["pattern"] == "^/tmp/safe/.*"

    @patch("progent.generation._api_request")
    @patch("progent.generation.get_available_tools")
    @patch("progent.generation.update_security_policy")
    @patch("progent.generation.get_security_policy")
    def test_generate_policies_success(
        self, mock_get_policy, mock_update, mock_get_tools, mock_request, mock_tools
    ):
        """Test successful policy generation flow."""
        mock_get_tools.return_value = mock_tools
        mock_request.return_value = PROMPT_RESPONSE_JSON
        mock_get_policy.return_value = {}

        policies = generate_policies("Read safe files")

        assert "read_file" in policies
        mock_request.assert_called_once()
        mock_update.assert_called_once()

        # Verify update was called with correct structure
        updated_policy = mock_update.call_args[0][0]
        assert "read_file" in updated_policy
        assert updated_policy["read_file"][0][0] == 100

    @patch("progent.generation._api_request")
    @patch("progent.generation.get_available_tools")
    def test_generate_policies_retry_failure(self, mock_get_tools, mock_request, mock_tools):
        """Test that generation raises RuntimeError after retries."""
        mock_get_tools.return_value = mock_tools
        mock_request.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Policy generation failed"):
            generate_policies("Do something")

        assert mock_request.call_count > 1

    @patch("progent.generation._api_request")
    @patch("progent.generation.get_user_query")
    @patch("progent.generation.get_available_tools")
    @patch("progent.generation.update_security_policy")
    @patch("progent.generation.get_security_policy")
    def test_update_policies_from_result_yes(
        self, mock_get_policy, mock_update, mock_get_tools, mock_query, mock_request, mock_tools
    ):
        """Test updating policy when LLM says Yes."""
        mock_query.return_value = "Original query"
        mock_get_tools.return_value = mock_tools
        mock_get_policy.return_value = {}

        # First call (_should_update_policy) returns "Yes"
        # Second call returns JSON
        mock_request.side_effect = ["Yes", PROMPT_RESPONSE_JSON]

        result = update_policies_from_result(
            tool_call_params={"path": "/tmp/test"}, tool_call_result="content", manual_confirm=False
        )

        assert result is not None
        assert "read_file" in result
        mock_update.assert_called_once()

    @patch("progent.generation._api_request")
    @patch("progent.generation.get_user_query")
    def test_update_policies_from_result_no(self, mock_query, mock_request):
        """Test no update when LLM says No."""
        mock_query.return_value = "Original query"
        mock_request.return_value = "No"

        result = update_policies_from_result(
            tool_call_params={"path": "/tmp/test"}, tool_call_result="content", manual_confirm=False
        )

        assert result is None

    def test_priority_system(self):
        """Test that generated policies use priority 100."""
        from progent.generation import _convert_generated_policies, _delete_generated_policies

        generated = [{"name": "tool1", "args": {"param": "value"}}]
        policies = _convert_generated_policies(generated)

        assert policies["tool1"][0][0] == 100

        # Test delete removes only generated
        mixed_policy = {
            "tool1": [(1, 0, {}, 0), (100, 0, {}, 0)],  # human + generated
            "tool2": [(100, 0, {}, 0)],  # only generated
        }

        _delete_generated_policies(mixed_policy)

        assert len(mixed_policy["tool1"]) == 1
        assert mixed_policy["tool1"][0][0] == 1
        assert "tool2" not in mixed_policy

    def test_token_tracking(self):
        """Test token usage tracking."""
        from progent.generation import get_token_usage, reset_token_usage

        reset_token_usage()
        usage = get_token_usage()

        assert usage["completion_tokens"] == 0
        assert usage["prompt_tokens"] == 0
        assert usage["total_tokens"] == 0
