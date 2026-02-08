import pytest
from progent.registry import ProgentRegistry
from progent.core import ProgentBlockedError

def test_registry_registration_and_enforcement():
    registry = ProgentRegistry()
    
    @registry.register
    def sensitive_tool(user: str):
        return f"Hello {user}"
    
    # Initialize implementation (pushes to core)
    registry.initialize()
    
    # Manually load a policy that denies "admin"
    from progent.core import update_security_policy
    policy = {
        "sensitive_tool": [
            (1, 1, {"user": "admin"}, 0) # Deny admin
        ]
    }
    update_security_policy(policy)
    
    # 1. Test direct execution via registry
    # Allowed
    assert registry.execute("sensitive_tool", user="alice") == "Hello alice"
    
    # Denied
    with pytest.raises(ProgentBlockedError):
        registry.execute("sensitive_tool", user="admin")
        
    # 2. Test getting wrapped tool
    tool_func = registry.get_tool("sensitive_tool")
    assert tool_func(user="bob") == "Hello bob"
    
    with pytest.raises(ProgentBlockedError):
        tool_func(user="admin")

def test_registry_auto_discovery():
    registry = ProgentRegistry()
    
    def my_tool(x: int):
        pass
        
    registry.register(my_tool)
    registry.initialize()
    
    from progent.core import get_available_tools
    tools = get_available_tools()
    
    found = next((t for t in tools if t["name"] == "my_tool"), None)
    assert found is not None
    assert "x" in found["args"]
    assert found["args"]["x"]["type"] == "integer"
