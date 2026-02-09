from progent.validation import validate_policy_against_tools


def test_validate_unknown_tool():
    tools = [{"name": "known_tool", "description": "desc", "args": {}}]
    policy = {"unknown_tool": []}

    warnings = validate_policy_against_tools(policy, tools)
    assert len(warnings) == 1
    assert "Tool 'unknown_tool' is not available" in warnings[0]

def test_validate_unknown_argument():
    tools = [{
        "name": "my_tool",
        "description": "desc",
        "args": {"valid_arg": {"type": "string"}}
    }]
    policy = {
        "my_tool": [
            (1, 0, {"invalid_arg": "value"}, 0)
        ]
    }

    warnings = validate_policy_against_tools(policy, tools)
    assert len(warnings) >= 1
    assert "Argument 'invalid_arg' is not available" in warnings[0]

def test_validate_type_specific_keyword_misuse():
    tools = [{
        "name": "my_tool",
        "description": "desc",
        "args": {"arg1": {"type": "string"}}
    }]
    policy = {
        "my_tool": [
            (1, 0, {"arg1": {"type": "string", "multipleOf": 2}}, 0) # multipleOf is for numbers
        ]
    }

    warnings = validate_policy_against_tools(policy, tools)
    assert len(warnings) >= 1
    # The warning message depends on implementation details of jsonschema validator or our custom check
    # Our custom check in validation.py returns: "'key' is not valid for type 'type'"
    assert "is not valid for type 'string'" in warnings[0]
