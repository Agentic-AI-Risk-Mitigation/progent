"""Progent policy enforcement wrapper."""

import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

# Add parent directory to path to import secagent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from secagent import (
    check_tool_call,
    update_security_policy,
    update_available_tools,
    get_available_tools,
    apply_secure_tool_wrapper,
)
from secagent.tool import ValidationError

from .logging_utils import get_logger


def load_policies(policies_path: str | Path) -> dict:
    """
    Load policies from a JSON file.
    
    The file format matches Progent's internal format:
    {
        "tool_name": [
            {
                "priority": 1,
                "effect": 0,  # 0=allow, 1=deny
                "conditions": {...},  # JSON Schema
                "fallback": 0  # 0=error, 1=terminate, 2=ask user
            }
        ]
    }
    """
    path = Path(policies_path)
    if not path.exists():
        raise FileNotFoundError(f"Policies file not found: {policies_path}")
    
    with open(path, "r") as f:
        raw_policies = json.load(f)
    
    # Convert to Progent's internal format (list of tuples)
    converted = {}
    for tool_name, rules in raw_policies.items():
        converted[tool_name] = []
        for rule in rules:
            # (priority, effect, conditions, fallback)
            converted[tool_name].append((
                rule.get("priority", 1),
                rule.get("effect", 0),
                rule.get("conditions", {}),
                rule.get("fallback", 0),
            ))
    
    return converted


def init_progent(
    policies_path: str | Path,
    tools: list[dict[str, Any]],
) -> None:
    """
    Initialize Progent with policies and available tools.
    
    :param policies_path: Path to the policies JSON file
    :param tools: List of tool definitions in Progent format
    """
    # Update available tools
    update_available_tools(tools)
    
    # Load and apply policies
    policies = load_policies(policies_path)
    update_security_policy(policies)
    
    logger = get_logger()
    logger.info(f"Progent initialized with {len(tools)} tools and {len(policies)} policies")


def enforce_policy(tool_name: str, kwargs: dict[str, Any]) -> tuple[bool, str]:
    """
    Check if a tool call is allowed by the current policy.
    
    :param tool_name: Name of the tool being called
    :param kwargs: Arguments to the tool
    :return: Tuple of (allowed: bool, reason: str)
    """
    logger = get_logger()
    
    try:
        check_tool_call(tool_name, kwargs)
        logger.progent_decision(tool_name, kwargs, allowed=True)
        return True, ""
    except ValidationError as e:
        reason = str(e)
        logger.progent_decision(tool_name, kwargs, allowed=False, reason=reason)
        return False, reason
    except Exception as e:
        reason = f"Policy check error: {type(e).__name__}: {e}"
        logger.progent_decision(tool_name, kwargs, allowed=False, reason=reason)
        return False, reason


def wrap_tool_with_enforcement(func: Callable, tool_name: str) -> Callable:
    """
    Wrap a tool function with Progent policy enforcement.
    
    :param func: The tool function to wrap
    :param tool_name: Name of the tool (for policy lookup)
    :return: Wrapped function that enforces policies
    """
    def wrapper(*args, **kwargs):
        logger = get_logger()
        
        # Log the tool call
        logger.tool_call(tool_name, kwargs)
        
        # Check policy
        allowed, reason = enforce_policy(tool_name, kwargs)
        
        if not allowed:
            error_msg = f"Policy blocked: {reason}"
            logger.tool_result(tool_name, error_msg, success=False)
            return error_msg
        
        # Execute the tool
        try:
            result = func(*args, **kwargs)
            result_str = str(result)
            logger.tool_result(tool_name, result_str, success=True)
            return result
        except Exception as e:
            error_msg = f"Tool error: {type(e).__name__}: {e}"
            logger.tool_result(tool_name, error_msg, success=False)
            raise
    
    # Preserve function metadata
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = getattr(func, "__annotations__", {})
    
    return wrapper


class ProgentEnforcedRegistry:
    """
    A tool registry that automatically enforces Progent policies.
    """
    
    def __init__(self, policies_path: str | Path):
        self.policies_path = Path(policies_path)
        self._tools: dict[str, Callable] = {}
        self._tool_definitions: list[dict[str, Any]] = []
        self._initialized = False
    
    def register(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None) -> Callable:
        """Register a tool with automatic policy enforcement."""
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip().split("\n")[0]
        
        # Store the wrapped function
        wrapped = wrap_tool_with_enforcement(func, tool_name)
        self._tools[tool_name] = wrapped
        
        # Build tool definition for Progent
        # Extract parameter info (simplified)
        import inspect
        sig = inspect.signature(func)
        params = {}
        for pname, param in sig.parameters.items():
            params[pname] = {"type": "string", "description": f"The {pname} parameter"}
        
        self._tool_definitions.append({
            "name": tool_name,
            "description": tool_desc,
            "args": params,
        })
        
        return wrapped
    
    def initialize(self) -> None:
        """Initialize Progent with registered tools and policies."""
        if self._initialized:
            return
        
        init_progent(self.policies_path, self._tool_definitions)
        self._initialized = True
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> dict[str, Callable]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        if not self._initialized:
            self.initialize()
        
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        
        return tool(**kwargs)
