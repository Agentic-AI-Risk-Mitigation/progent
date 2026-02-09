
import pytest
from unittest.mock import MagicMock, patch
import sys
import importlib

# Mock BaseTool definition
class MockBaseTool:
    def __init__(self, name, description, args):
        self.name = name
        self.description = description
        self.args = args
        self._to_args_and_kwargs = MagicMock(return_value=((), {}))

@pytest.fixture
def mock_langchain_env():
    """
    Sets up a mocked langchain environment in sys.modules safely.
    """
    mock_core = MagicMock()
    # IMPORTANT: BaseTool must be a class (type) for isinstance() checks
    mock_core.tools.BaseTool = MockBaseTool 
    # Also set it on the parent if 'tools' is aliased or accessed via parent
    mock_core.BaseTool = MockBaseTool 
    mock_core.tools.StructuredTool = MagicMock()
    
    # We patch sys.modules to insert our mocks
    with patch.dict(sys.modules, {
        "langchain_core": mock_core,
        "langchain_core.tools": mock_core.tools,
    }):
        # Reload the target module to pick up the mocked langchain
        # We handle the case where it might or might not be imported yet
        if "progent.adapters.langchain" in sys.modules:
            importlib.reload(sys.modules["progent.adapters.langchain"])
        else:
            import progent.adapters.langchain
            
        yield

        # Cleanup: Reload again to restore original state (or fail if not installed)
        if "progent.adapters.langchain" in sys.modules:
            importlib.reload(sys.modules["progent.adapters.langchain"])
        if "progent.wrapper" in sys.modules:
            importlib.reload(sys.modules["progent.wrapper"])

# Use the fixture in all tests in this execution
@pytest.fixture(autouse=True)
def setup_env(mock_langchain_env):
    pass

from progent.exceptions import ProgentBlockedError

def get_target_module():
    import progent.adapters.langchain as target
    return target

@pytest.fixture
def mock_check_tool_call():
    with patch("progent.adapters.langchain.check_tool_call") as mock:
        yield mock

@pytest.fixture
def mock_get_available_tools():
    with patch("progent.adapters.langchain.get_available_tools", return_value=[]) as mock:
        yield mock

@pytest.fixture
def mock_update_available_tools():
    with patch("progent.adapters.langchain.update_available_tools") as mock:
        yield mock

def test_secure_langchain_tool_allowed(mock_check_tool_call, mock_get_available_tools, mock_update_available_tools):
    target = get_target_module()
    
    # Setup
    tool = MockBaseTool(name="test_tool", description="A test tool", args={"arg1": {"type": "string"}})
    tool._to_args_and_kwargs.return_value = ((), {"arg1": "value"})
    
    # Wrap
    secured = target.secure_langchain_tool(tool)
    
    # Execute
    secured._to_args_and_kwargs(arg1="value")
    
    # Verify
    mock_check_tool_call.assert_called_once_with("test_tool", {"arg1": "value"})

def test_secure_langchain_tool_blocked(mock_check_tool_call, mock_get_available_tools, mock_update_available_tools):
    target = get_target_module()
    
    tool = MockBaseTool(name="dangerous_tool", description="Dangerous", args={})
    tool._to_args_and_kwargs.return_value = ((), {})
    
    mock_check_tool_call.side_effect = ProgentBlockedError("dangerous_tool", {}, "Blocked")
    
    secured = target.secure_langchain_tool(tool)
    
    with pytest.raises(ProgentBlockedError):
        secured._to_args_and_kwargs()

def test_create_secured_tool(mock_check_tool_call, mock_get_available_tools, mock_update_available_tools):
    target = get_target_module()
    
    def my_function(x: int):
        return x * 2
    
    # Setup return value for StructuredTool.from_function
    mock_tool_instance = MockBaseTool("my_function", "doc", {})
    
    # Access the mock from sys.modules to configure it
    # We must configure the mock that the module sees
    sys.modules["langchain_core.tools"].StructuredTool.from_function.return_value = mock_tool_instance
    
    # Execute
    tool = target.create_secured_tool(my_function)
    
    # Verify registration
    mock_update_available_tools.assert_called_once()
    registered_list = mock_update_available_tools.call_args[0][0]
    
    # Fix: registered_list contains TypeDicts/dicts, so access via keys, not attributes
    assert len(registered_list) == 1
    assert registered_list[0]["name"] == "my_function"
    
    # Verify execution wrapper
    mock_structured_tool = sys.modules["langchain_core.tools"].StructuredTool
    wrapper_func = mock_structured_tool.from_function.call_args.kwargs['func']
    
    wrapper_func(x=5)
    mock_check_tool_call.assert_called_once_with("my_function", {"x": 5})
