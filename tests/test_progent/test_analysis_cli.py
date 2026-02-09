
import json
import sys
from unittest.mock import patch

import pytest

from progent.cli import main

# Mock policy with conflict
CONFLICT_POLICY = {
    "tool_A": [
        (1, 0, {"arg1": {"type": "string", "pattern": "A.*"}}, 0),
        (2, 0, {"arg1": {"type": "string", "pattern": ".*B"}}, 0),
    ]
}

# Mock policy without conflict
CLEAN_POLICY = {
    "tool_B": [
        (1, 0, {"arg1": {"type": "integer", "minimum": 10}}, 0),
        (2, 0, {"arg1": {"type": "integer", "maximum": 5}}, 0),
    ]
}

@pytest.fixture
def policy_file(tmp_path):
    def _create(policy_data):
        p = tmp_path / "policy.json"
        p.write_text(json.dumps(policy_data))
        return str(p)
    return _create

def test_analyze_no_conflicts(policy_file, capsys):
    p_path = policy_file(CLEAN_POLICY)

    with patch.object(sys, 'argv', ["progent", "analyze", "--policy", p_path]):
        # Expect exit code 0
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0

    captured = capsys.readouterr()
    assert "Policy looks good" in captured.out

def test_analyze_with_conflicts(policy_file, capsys):
    p_path = policy_file(CONFLICT_POLICY)

    # Mock analyze_policies to return a warning
    with patch("progent.analysis.analyze_policies", return_value=["Warning: Overlap detected"]):
         with patch.object(sys, 'argv', ["progent", "analyze", "--policy", p_path]):
            # Expect exit code 1 due to warnings
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1

    captured = capsys.readouterr()
    assert "Found 1 issues" in captured.out
    assert "Warning: Overlap detected" in captured.out

def test_check_command_allowed(policy_file, capsys):
    p_path = policy_file(CLEAN_POLICY)

    with patch("progent.cli.check_tool_call"):
        with patch.object(sys, 'argv', ["progent", "check", "--policy", p_path, "--tool", "t", "--args", "{}"]):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 0

    captured = capsys.readouterr()
    assert "ALLOWED" in captured.out



