import pytest
import sys
import json
import tempfile
import os
from unittest.mock import patch, MagicMock
from progent.cli import main
from progent.exceptions import ProgentBlockedError

class TestCLI:
    @pytest.fixture
    def policy_file(self):
        policy = {
            "my_tool": [
                [1, 1, {"arg": "unsafe"}, 0],
                [2, 0, {}, None]
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(policy, f)
            path = f.name
        yield path
        os.remove(path)

    def test_cli_allowed(self, policy_file):
        test_args = [
            "progent",
            "--policy", policy_file,
            "--tool", "my_tool",
            "--args", '{"arg": "safe"}'
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 0

    def test_cli_blocked(self, policy_file):
        test_args = [
            "progent",
            "--policy", policy_file,
            "--tool", "my_tool",
            "--args", '{"arg": "unsafe"}'
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1

    def test_cli_invalid_policy_path(self):
        test_args = [
            "progent",
            "--policy", "non_existent.json",
            "--tool", "my_tool",
            "--args", "{}"
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1
