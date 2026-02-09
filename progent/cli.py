import argparse
import json
import sys
from pathlib import Path
from typing import Any

from progent.core import update_security_policy, check_tool_call
from progent.exceptions import ProgentBlockedError, PolicyValidationError
from progent.logger import get_logger, configure_logging

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = get_logger()

def main():
    parser = argparse.ArgumentParser(description="Progent Policy Debugger")
    parser.add_argument("--policy", "-p", required=True, help="Path to policy JSON file")
    parser.add_argument("--tool", "-t", required=True, help="Name of the tool to check")
    parser.add_argument("--args", "-a", required=True, help="JSON string of arguments")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-level", "-l", help="Set logging level (DEBUG, INFO, WARNING, ERROR)", default=None)

    args = parser.parse_args()

    # Configure Logging
    level = "DEBUG" if args.verbose else args.log_level
    configure_logging(level=level)

    # Load Policy
    policy_path = Path(args.policy)
    if not policy_path.exists():
        logger.error(f"Policy file not found: {policy_path}")
        sys.exit(1)

    try:
        with open(policy_path, "r") as f:
            policy = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in policy file: {e}")
        sys.exit(1)
    
    # Load Arguments
    try:
        tool_args = json.loads(args.args)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in arguments: {e}")
        sys.exit(1)

    # Initialize Progent
    update_security_policy(policy)

    logger.info(f"Checking access for tool '{args.tool}' with args: {json.dumps(tool_args, indent=2)}")

    try:
        check_tool_call(args.tool, tool_args)
        print("\n✅ ALLOWED")
        sys.exit(0)

    except ProgentBlockedError as e:
        print("\n❌ BLOCKED")
        print(f"Reason: {e.reason}")
        if hasattr(e, "policy_rule") and e.policy_rule:
             print(f"Rule: {e.policy_rule}")
        if hasattr(e, "failed_condition") and e.failed_condition:
             print(f"Failed Condition: {e.failed_condition}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
