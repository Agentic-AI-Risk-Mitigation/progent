import pytest

from progent.core import (
    ProgentBlockedError,
    check_tool_call,
    update_security_policy,
)


def test_detailed_error_attributes():
    # Setup policy
    policy = {
        "test_tool": [
            (1, 1, {"arg1": "unsafe"}, 0)  # Deny if arg1 is "unsafe" (Effect 1 = Deny)
        ]
    }
    update_security_policy(policy)

    # Test
    with pytest.raises(ProgentBlockedError) as excinfo:
        check_tool_call("test_tool", {"arg1": "unsafe"})

    # Verify detailed attributes
    assert excinfo.value.tool_name == "test_tool"
    assert excinfo.value.arguments == {"arg1": "unsafe"}
    assert excinfo.value.policy_rule == (1, 1, {"arg1": "unsafe"}, 0)
    assert "Matched deny rule" in str(excinfo.value.failed_condition)


def test_no_matching_allow_rule_error():
    # Setup policy (Implicit deny if no matching allow rule for allow-only policy?)
    # Progent default is allow if no policy, but if policy exists it checks them.
    # If policy has logic: check_tool_call_impl iterates lists.
    # If Effect 0 (Allow) doesn't match, it continues.
    # If no rule matches at all, it raises ProgentBlockedError.

    policy = {
        "test_tool_2": [
            (1, 0, {"arg1": "safe"}, 0)  # Allow only if arg1 is "safe"
        ]
    }
    update_security_policy(policy)

    # Test
    with pytest.raises(ProgentBlockedError) as excinfo:
        check_tool_call("test_tool_2", {"arg1": "unknown"})

    # Verify message
    assert "No matching allow rule found" in str(excinfo.value.reason)
    assert "value 'unknown' does not match pattern 'safe'" in str(excinfo.value.reason) or \
           "does not match pattern" in str(excinfo.value.reason) # Regex check might fail with specific msg
