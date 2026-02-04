# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Progent is a **Programmable Privilege Control framework for LLM Agents**. It enforces fine-grained security policies on AI agent tool calls using JSON Schema validation. Policies are declarative (JSON) and framework-agnostic.

## Common Commands

### Setup
```bash
uv sync                          # Install all dependencies
uv sync --extra analysis         # Include Z3 policy analysis
uv sync --extra all              # Include all optional deps
```

### Testing
```bash
uv run pytest tests/             # Run all tests
uv run pytest tests/test_core.py # Run a single test file
uv run pytest tests/test_core.py::test_function_name  # Run a single test
```

### Linting
```bash
uv run ruff check .              # Lint
uv run ruff format .             # Format
```

### Running the Example Agent
```bash
cd implementations/examples/coding_agent
uv run run_agent.py              # Requires OPENROUTER_API_KEY in .env
uv run run_agent.py --framework langchain --policies policies.json
```

## Architecture

### Three-Layer Structure

1. **`progent/`** — Core SDK library (pip-installable)
   - `core.py` — Global policy/tool registry + `check_tool_call()` enforcement
   - `policy.py` — Policy loading from JSON files or dicts
   - `validation.py` — Argument validation (JSON Schema, regex, callables)
   - `wrapper.py` — `@secure` decorator and LangChain tool wrapping
   - `exceptions.py` — `ProgentBlockedError`, `PolicyValidationError`, `PolicyLoadError`, `PolicyConfigError`
   - `analysis.py` — Z3-based conflict detection (optional, requires `z3-solver`)
   - `generation.py` — LLM-based policy generation (optional, not yet tested)
   - `adapters/` — `langchain.py`, `mcp.py`

2. **`implementations/`** — Example agent implementations using the SDK
   - `core/tool_definitions.py` — Single source of truth for tool schemas
   - `core/secured_executor.py` — Tool wrapping with logging + policy
   - `core/progent_enforcer.py` — Wrapper around progent library
   - `frameworks/base_agent.py` — Abstract base; subclassed by `langchain_agent.py`, `adk_agent.py`, `raw_sdk_agent.py`
   - `tools/` — Reusable tool implementations (file, command, communication)

3. **`secagent/`** — Reference implementation from the Progent paper authors

### Policy Format

Policies map tool names to rule lists: `{tool_name: [(priority, effect, conditions, fallback), ...]}`. Effect `0` = allow, `1` = deny. Conditions are JSON Schema constraints on arguments. Default behavior is deny (no matching rule = blocked).

### Policy Evaluation Flow

```
Tool Call → check_tool_call(name, kwargs)
  → Iterate rules by priority
  → Match allow rule? → Execute
  → Match deny rule? → Block (fallback: 0=error, 1=terminate, 2=ask user)
  → No match? → Block (default deny)
```

### Core API

```python
from progent import secure, load_policies, check_tool_call

load_policies("policies.json")    # Load policy file
check_tool_call("tool", {args})   # Manual check (raises ProgentBlockedError)

@secure                           # Decorator
def my_tool(arg: str) -> str: ...

tools = secure([tool1, tool2])    # Wrap list of tools/functions
```

### Global State

`progent/core.py` uses module-level globals (`_available_tools`, `_security_policy`, `_user_query`) with getter/setter functions. Tests must call `reset_security_policy()` in fixtures to avoid state leakage.

## Key Conventions

- Python >=3.11, target 3.12 (`.python-version`)
- Ruff for linting/formatting (line-length 100, ignores E501)
- pytest with `asyncio_mode = "auto"`
- Build system: hatchling
- Environment variables via `.env` (gitignored): `OPENROUTER_API_KEY`, `PROGENT_POLICY_MODEL`

## Known Weak Spots (from TODO.md)

- MCP adapter (`progent/adapters/mcp.py`) has no real-world testing
- `progent/generation.py` is untested and not integrated
- `implementations/core/progent_enforcer.py` duplicates some logic from `progent/core.py`
- Z3 regex-to-Z3 conversion may fail on edge cases
- No CI/CD pipeline
