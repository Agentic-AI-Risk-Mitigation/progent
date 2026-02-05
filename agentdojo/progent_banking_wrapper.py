"""
Progent-secured wrapper for AgentDojo banking suite tools.
This module wraps banking tools with Progent security policies.
"""

import sys
from pathlib import Path

# Add progent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Any, Callable
from functools import wraps

from progent import load_policies, check_tool_call, ProgentBlockedError
from agentdojo.default_suites.v1.tools.banking_client import (
    get_iban,
    send_money,
    schedule_transaction,
    update_scheduled_transaction,
    get_balance,
    get_most_recent_transactions,
    get_scheduled_transactions,
)
from agentdojo.default_suites.v1.tools.file_reader import read_file
from agentdojo.default_suites.v1.tools.user_account import (
    get_user_info,
    update_password,
    update_user_info,
)


class ProgentSecuredBankingTools:
    """
    Wrapper class that secures banking tools with Progent policies.
    """

    def __init__(self, policy_file: str = "progent_banking_policies.json"):
        """
        Initialize with policy file.
        
        Args:
            policy_file: Path to the Progent policy JSON file
        """
        # Load policies
        policy_path = Path(__file__).parent / policy_file
        load_policies(str(policy_path))
        print(f"[OK] Loaded Progent policies from {policy_path}")

        # Store original tools
        self._original_tools = {
            "send_money": send_money,
            "schedule_transaction": schedule_transaction,
            "update_scheduled_transaction": update_scheduled_transaction,
            "update_password": update_password,
            "update_user_info": update_user_info,
            "get_iban": get_iban,
            "get_balance": get_balance,
            "get_most_recent_transactions": get_most_recent_transactions,
            "get_scheduled_transactions": get_scheduled_transactions,
            "read_file": read_file,
            "get_user_info": get_user_info,
        }

        # Track blocked and allowed calls for analysis
        self.blocked_calls = []
        self.allowed_calls = []

    def _wrap_tool(self, tool_name: str, original_func: Callable) -> Callable:
        """
        Wrap a tool function with Progent security check.
        
        Args:
            tool_name: Name of the tool
            original_func: Original function to wrap
            
        Returns:
            Wrapped function with security checks
        """
        @wraps(original_func)
        def secured_wrapper(*args, **kwargs):
            # Extract kwargs from the function call
            # AgentDojo uses dependency injection, so we need to handle both cases
            import inspect
            sig = inspect.signature(original_func)
            
            # Build kwargs dict from positional and keyword args
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Filter out Depends arguments (they start with account, filesystem, etc.)
            call_kwargs = {
                k: v for k, v in bound_args.arguments.items()
                if not str(sig.parameters[k].annotation).startswith("Annotated")
            }
            
            try:
                # Check with Progent
                check_tool_call(tool_name, call_kwargs)
                self.allowed_calls.append((tool_name, call_kwargs))
                print(f"  [OK] {tool_name} allowed: {call_kwargs}")
                
                # Execute original function
                return original_func(*args, **kwargs)
                
            except ProgentBlockedError as e:
                self.blocked_calls.append((tool_name, call_kwargs, str(e)))
                print(f"  [BLOCKED] {tool_name}: {call_kwargs}")
                print(f"    Reason: {e}")
                raise
                
        return secured_wrapper

    def get_secured_tools(self) -> dict[str, Callable]:
        """
        Get dictionary of secured tool functions.
        
        Returns:
            Dictionary mapping tool names to secured functions
        """
        return {
            name: self._wrap_tool(name, func)
            for name, func in self._original_tools.items()
        }

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about allowed and blocked calls.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_allowed": len(self.allowed_calls),
            "total_blocked": len(self.blocked_calls),
            "allowed_calls": self.allowed_calls,
            "blocked_calls": self.blocked_calls,
        }

    def print_summary(self):
        """Print a summary of security enforcement."""
        stats = self.get_stats()
        print("\n" + "="*70)
        print("PROGENT SECURITY SUMMARY")
        print("="*70)
        print(f"Total Allowed Calls: {stats['total_allowed']}")
        print(f"Total Blocked Calls: {stats['total_blocked']}")
        
        if stats['blocked_calls']:
            print("\nBlocked Calls (Attacks Prevented):")
            for tool_name, kwargs, reason in stats['blocked_calls']:
                print(f"  - {tool_name}: {kwargs}")
                print(f"    Reason: {reason}")
        
        print("="*70)
