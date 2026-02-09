import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from progent.cli import main


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
            "check",
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
            "check",
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
            "check",
            "--policy", "non_existent.json",
            "--tool", "my_tool",
            "--args", "{}"
        ]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(SystemExit) as e:
                main()
            assert e.value.code == 1

    def test_analyze_no_conflicts(self, policy_file):
        # Create a clean policy (using the fixture's path, but we need to overwrite it or creating a new one)
        # The fixture creates a policy. Let's just use a mocking approach for the analysis module
        # to avoid complex setup, or just trust the fixture policy if it has no conflicts.
        # The fixture policy has 1 rule per tool, so no overlap.

        test_args = [
            "progent",
            "analyze",
            "--policy", policy_file
        ]

        # Mock analysis to return empty list (no conflicts)
        with patch("progent.analysis.analyze_policies", return_value=[]), \
             patch("progent.analysis.check_policy_type_errors", return_value=[]):
            with patch.object(sys, "argv", test_args):
                with pytest.raises(SystemExit) as e:
                    main()
                assert e.value.code == 0

    def test_analyze_with_conflicts(self, policy_file):
        test_args = [
            "progent",
            "analyze",
            "--policy", policy_file
        ]

        # Mock analysis to return warnings
        with patch("progent.analysis.analyze_policies", return_value=["Conflict detected"]), \
             patch("progent.analysis.check_policy_type_errors", return_value=[]):
            with patch.object(sys, "argv", test_args):
                with pytest.raises(SystemExit) as e:
                    main()
                # Should exit with 1 if conflicts found
                assert e.value.code == 1



