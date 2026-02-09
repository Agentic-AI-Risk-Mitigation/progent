
# Mock dependencies if not installed
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# NOTE: ruff E402 requires imports at top, but we need to mock sys.modules
# before importing progent.adapters.mcp. Using noqa to suppress
# Mock fastmcp module structure
mock_fastmcp = MagicMock()
sys.modules["fastmcp"] = mock_fastmcp
sys.modules["fastmcp.server"] = MagicMock()
sys.modules["fastmcp.server.proxy"] = MagicMock()

from progent.adapters.mcp import ProgentMiddleware, create_secured_mcp_server  # noqa: E402
from progent.exceptions import ProgentBlockedError  # noqa: E402


@pytest.fixture
def mock_check_tool_call():
    with patch("progent.adapters.mcp.check_tool_call") as mock:
        yield mock

@pytest.mark.asyncio
async def test_mcp_middleware_allowed(mock_check_tool_call):
    # Setup
    middleware = ProgentMiddleware(log_calls=False)

    # Mock Context and Next
    context = MagicMock()
    context.message.name = "test_tool"
    context.message.arguments = {"arg": "val"}

    call_next = AsyncMock(return_value="result")

    # Execute
    result = await middleware.on_call_tool(context, call_next)

    # Verify
    mock_check_tool_call.assert_called_once_with("test_tool", {"arg": "val"})
    call_next.assert_called_once_with(context)
    assert result == "result"

@pytest.mark.asyncio
async def test_mcp_middleware_blocked(mock_check_tool_call):
    # Setup
    middleware = ProgentMiddleware(log_calls=False)

    # Mock Context
    context = MagicMock()
    context.message.name = "dangerous_tool"
    context.message.arguments = {}

    # Mock check failing
    mock_check_tool_call.side_effect = ProgentBlockedError("dangerous_tool", {}, "Blocked!")

    call_next = AsyncMock()

    # Execute & Verify
    with pytest.raises(ProgentBlockedError):
        await middleware.on_call_tool(context, call_next)

    call_next.assert_not_called()

@pytest.mark.asyncio
async def test_mcp_middleware_callback(mock_check_tool_call):
    # Setup
    callback = MagicMock()
    middleware = ProgentMiddleware(on_blocked=callback, log_calls=False)

    context = MagicMock()
    context.message.name = "blocked_tool"
    context.message.arguments = {"x": 1}

    mock_check_tool_call.side_effect = ProgentBlockedError("blocked_tool", {"x": 1}, "Blocked")

    # Execute
    with pytest.raises(ProgentBlockedError):
        await middleware.on_call_tool(context, AsyncMock())

    # Verify callback
    callback.assert_called_once_with("blocked_tool", {"x": 1}, "Blocked")

def test_create_secured_mcp_server():
    # Test convenience function
    with patch("fastmcp.FastMCP") as MockFastMCP:
        create_secured_mcp_server(name="TestServer")

        MockFastMCP.assert_called_with(name="TestServer")
        server_instance = MockFastMCP.return_value

        # Verify middleware was added
        assert server_instance.add_middleware.call_count == 1
        middleware = server_instance.add_middleware.call_args[0][0]
        assert isinstance(middleware, ProgentMiddleware)
