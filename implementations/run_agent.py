#!/usr/bin/env python3
"""
Progent Coding Agent - CLI Entry Point

Usage:
    python run_agent.py                           # Use defaults (sandbox workspace, langchain)
    python run_agent.py --workspace ./my_project  # Specify workspace
    python run_agent.py --framework adk           # Use Google ADK
    python run_agent.py --model anthropic/claude-3.5-sonnet  # Override model
"""

import argparse
import os
import sys
from pathlib import Path

# Add implementations directory to path for imports
IMPL_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(IMPL_DIR))

# Add parent directory for secagent imports
sys.path.insert(0, str(IMPL_DIR.parent))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(IMPL_DIR / ".env")

import yaml


def load_config(config_path: str | Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    # Get the implementations directory
    impl_dir = Path(__file__).parent.resolve()
    
    parser = argparse.ArgumentParser(
        description="Progent Coding Agent - A secure coding assistant with policy enforcement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=None,
        help="Path to the workspace directory (default: ./sandbox)",
    )
    
    parser.add_argument(
        "--framework", "-f",
        type=str,
        choices=["langchain", "adk", "raw_sdk"],
        default=None,
        help="Agent framework to use (default: from config)",
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="LLM model to use (default: from config)",
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=str(impl_dir / "config.yaml"),
        help="Path to config file (default: ./config.yaml)",
    )
    
    parser.add_argument(
        "--policies", "-p",
        type=str,
        default=str(impl_dir / "policies.json"),
        help="Path to policies file (default: ./policies.json)",
    )
    
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directory for log files (default: from config)",
    )
    
    args = parser.parse_args()
    
    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid config file: {e}")
        sys.exit(1)
    
    # Apply command-line overrides
    if args.framework:
        config.setdefault("agent", {})["framework"] = args.framework
    
    if args.model:
        config.setdefault("llm", {})["model"] = args.model
    
    # Determine workspace
    if args.workspace:
        workspace = Path(args.workspace).resolve()
    else:
        default_workspace = config.get("workspace", {}).get("default_path", "./sandbox")
        workspace = (impl_dir / default_workspace).resolve()
    
    # Ensure workspace exists
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Initialize logging
    log_dir = args.log_dir or config.get("logging", {}).get("log_dir", "./logs")
    log_dir = (impl_dir / log_dir).resolve()
    log_level = config.get("logging", {}).get("level", "INFO")
    
    from core.logging_utils import init_logger
    init_logger(log_dir=str(log_dir), level=log_level)
    
    # Get framework
    framework = config.get("agent", {}).get("framework", "langchain")
    
    # Create the agent
    print(f"Initializing {framework} agent...")
    print(f"Workspace: {workspace}")
    print(f"Policies: {args.policies}")
    
    try:
        if framework == "langchain":
            from frameworks.langchain_agent import LangChainAgent
            agent = LangChainAgent(
                config=config,
                workspace=workspace,
                policies_path=args.policies,
            )
        elif framework == "adk":
            from frameworks.adk_agent import ADKAgent
            agent = ADKAgent(
                config=config,
                workspace=workspace,
                policies_path=args.policies,
            )
        elif framework == "raw_sdk":
            from frameworks.raw_sdk_agent import RawSDKAgent
            agent = RawSDKAgent(
                config=config,
                workspace=workspace,
                policies_path=args.policies,
            )
        else:
            print(f"Error: Unknown framework: {framework}")
            sys.exit(1)
            
    except ImportError as e:
        print(f"Error: Could not import {framework} agent. Is the framework installed?")
        print(f"Details: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error initializing agent: {e}")
        sys.exit(1)
    
    # Start the REPL
    agent.start_repl()


if __name__ == "__main__":
    main()
