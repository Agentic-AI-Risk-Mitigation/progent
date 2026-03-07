# Progent

**Programmable Privilege Control for LLM Agents** — a framework-agnostic Python library that enforces fine-grained security policies on AI agent tool calls using JSON Schema validation.

Progent intercepts tool calls made by LLM agents, evaluates them against declarative JSON policies, and allows or blocks execution based on argument constraints. Policies are framework-agnostic and work with LangChain, MCP, Google ADK, Claude Agent SDK, or raw OpenAI SDK agents.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation with uv (Recommended)

```bash
# Install core dependencies
uv sync

# Install optional extras as needed
uv sync --extra analysis       # Z3-based policy analysis
uv sync --extra adk            # Google ADK (Gemini)
uv sync --extra claude-sdk     # Claude Agent SDK
uv sync --extra all            # All optional dependencies
```

### Installation with pip

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the library
pip install -e .

# Install optional extras
pip install -e ".[analysis]"   # Z3-based policy analysis
pip install -e ".[all]"        # All optional dependencies
```

### Run the Example Agent

```bash
# Set up your API key
cd implementations/examples/coding_agent
cp env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# Run with default settings (LangChain framework)
uv run run_agent.py

# Or with a specific framework
uv run run_agent.py --framework adk
uv run run_agent.py --framework claude_sdk
uv run run_agent.py --framework raw_sdk
```

## Core API

```python
from progent import load_policies, check_tool_call
from progent import apply_secure_tool_wrapper, secure_tool_wrapper

# 1. Load policies from a JSON file or dict
load_policies("policies.json")

# 2. Check a tool call manually (raises ProgentBlockedError if denied)
check_tool_call("write_file", {"file_path": "/tmp/output.txt", "content": "hello"})

# 3. Wrap a function for automatic enforcement
secured_fn = apply_secure_tool_wrapper(my_tool_function)

# 4. Wrap a list of LangChain tools
secured_tools = [secure_tool_wrapper(t) for t in tools]
```

### Policy Format

Policies map tool names to ordered rule lists. Each rule has a priority, an effect (allow or deny), and optional JSON Schema conditions on the arguments:

```json
{
  "write_file": [
    {
      "priority": 1,
      "effect": 0,
      "conditions": {
        "file_path": {"pattern": "^sandbox/.*$"}
      }
    },
    {
      "priority": 2,
      "effect": 1,
      "conditions": {},
      "fallback": 0
    }
  ]
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `priority` | integer | Lower numbers are evaluated first |
| `effect` | `0` = allow, `1` = deny | What happens when conditions match |
| `conditions` | JSON Schema object | Constraints on tool arguments (empty = match all) |
| `fallback` | `0` = error, `1` = terminate, `2` = ask user | Action when a deny rule matches |

**Default behavior:** If no rule matches a tool call, it is **denied**.

### Policy Evaluation Flow

```
Tool Call -> check_tool_call(name, kwargs)
  -> Iterate rules by priority (lowest first)
  -> Match allow rule? -> Execute tool
  -> Match deny rule?  -> Block (apply fallback action)
  -> No match?         -> Block (default deny)
```

## Configuration

### Environment Variables (.env)

Create a `.env` file in the project root:

```bash
# Required: API key for LLM access
OPENROUTER_API_KEY=sk-or-v1-xxx  # Recommended - supports multiple models
# OR
OPENAI_API_KEY=sk-xxx
# OR
ANTHROPIC_API_KEY=sk-ant-xxx

# Optional: Model for LLM-based policy generation
PROGENT_POLICY_MODEL=openai/gpt-4o-mini
```

### Agent Configuration (config.yaml)

Located in `implementations/examples/coding_agent/`:

```yaml
llm:
  model: deepseek/deepseek-v3.2
  api_base: https://openrouter.ai/api/v1
```

### CLI Options

Run from `implementations/examples/coding_agent/`:

```bash
uv run run_agent.py                                    # Default (LangChain + sandbox)
uv run run_agent.py --workspace ./my_project           # Custom workspace
uv run run_agent.py --framework adk                    # Use Google ADK
uv run run_agent.py --framework raw_sdk                # Use raw OpenAI SDK
uv run run_agent.py --framework claude_sdk             # Use Claude Agent SDK
uv run run_agent.py --model anthropic/claude-3.5-sonnet  # Different model
uv run run_agent.py --policies custom.json             # Custom policies file
```

| Flag | Description |
|------|-------------|
| `-w, --workspace` | Working directory for the agent |
| `-f, --framework` | `langchain`, `adk`, `raw_sdk`, or `claude_sdk` |
| `-m, --model` | LLM model (OpenRouter format) |
| `-p, --policies` | Path to policies JSON file |
| `-c, --config` | Path to config YAML file |
| `--api-base` | API base URL override |

### REPL Commands

| Command | Action |
|---------|--------|
| `exit` | Quit |
| `clear` | Clear conversation |
| `verbose` | Toggle tool output |

## Repository Structure

```
progent/                          # Core SDK (pip-installable library)
|-- __init__.py
|-- core.py                       # Policy enforcement engine
|-- policy.py                     # Policy loading/saving
|-- validation.py                 # JSON Schema argument validation
|-- wrapper.py                    # Tool wrapping and @secure decorator
|-- exceptions.py                 # ProgentBlockedError, PolicyValidationError
|-- registry.py                   # Tool registration and enforcement
|-- logger.py                     # Centralized logging
|-- cli.py                        # Policy debugging CLI
|-- analysis.py                   # Z3-based policy analysis (optional)
|-- generation.py                 # LLM policy generation (optional)
|-- adapters/
|   |-- langchain.py              # LangChain integration
|   +-- mcp.py                    # MCP middleware

tests/                            # SDK tests
+-- test_progent/

implementations/                  # Agent implementations using the SDK
|-- requirements.txt
|-- core/                         # Shared infrastructure
|   |-- tool_definitions.py       # Tool schemas (single source of truth)
|   |-- secured_executor.py       # Policy enforcement wrapper
|   +-- progent_enforcer.py       # Progent library integration
|-- frameworks/                   # Agent framework adapters
|   |-- base_agent.py             # Abstract base agent
|   |-- langchain_agent.py        # LangChain adapter
|   |-- adk_agent.py              # Google ADK adapter
|   |-- raw_sdk_agent.py          # OpenAI SDK adapter
|   +-- claude_sdk_agent.py       # Claude Agent SDK adapter
|-- tools/                        # Tool implementations
|   |-- file_tools.py
|   |-- command_tools.py
|   +-- communication_tools.py
|-- evals/                        # Evaluation framework
|   |-- scenarios.py              # Test scenarios
|   |-- harness.py                # Test runner
|   |-- run_evals.py              # Entry point
|   |-- eval_policies.json        # Restrictive test policies
|   +-- results/                  # JSON test results
+-- examples/
    +-- coding_agent/             # Main example agent
        |-- run_agent.py          # Entry point
        |-- config.yaml           # Agent configuration
        |-- policies.json         # Security policies
        +-- env.template          # API key template

secagent/                         # Reference implementation (read-only)
```

## Evaluation Framework

The `implementations/evals/` directory provides automated testing for agent security and capabilities:

- Validates that policies block malicious actions (security)
- Ensures policies allow legitimate tasks (utility)
- Provides reproducible benchmarks for agent behavior

```bash
cd implementations
python -m evals.run_evals  # Run all test scenarios
```

**Test categories:**

| Prefix | Category | Expected Outcome |
|--------|----------|------------------|
| `A*` | Valid use cases | Should pass |
| `B*` | Tool misuse | Should be blocked |
| `C*` | Dangerous commands | Should be refused |
| `D*` | Social engineering | Should be refused |

## Creating New Examples

```bash
cd implementations/examples
cp -r coding_agent my_new_agent
# Edit config.yaml, policies.json, and run_agent.py as needed
```

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/

# Lint and format
uv run ruff check .
uv run ruff format .
```

## License

MIT
