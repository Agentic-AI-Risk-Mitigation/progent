# Progent

Secure coding agent with policy enforcement via the `progent` library.

## Quick Start

```bash
# 1. Create environment
conda create -n progent python=3.11 -y
conda activate progent

# 2. Install dependencies
cd implementations
pip install -r requirements.txt
pip install -e ..  # Install progent library

# 3. Set API key
cd examples/coding_agent
cp env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# 4. Run
python run_agent.py
```

## CLI Options

```bash
python run_agent.py                              # Default (LangChain + sandbox)
python run_agent.py --workspace ./my_project     # Custom workspace
python run_agent.py --framework adk              # Use Google ADK
python run_agent.py --framework raw_sdk          # Use raw OpenAI SDK
python run_agent.py --model anthropic/claude-3.5-sonnet  # Different model
python run_agent.py --policies custom.json       # Custom policies file
```

| Flag | Description |
|------|-------------|
| `-w, --workspace` | Working directory for the agent |
| `-f, --framework` | `langchain`, `adk`, or `raw_sdk` |
| `-m, --model` | LLM model (OpenRouter format) |
| `-p, --policies` | Path to policies JSON file |
| `-c, --config` | Path to config YAML file |

## Configuration

**`config.yaml`** - LLM settings, system prompt, logging:
```yaml
llm:
  model: meta-llama/llama-3.1-70b-instruct
  api_base: https://openrouter.ai/api/v1
```

**`policies.json`** - Security policies (JSON Schema format):
```json
{
  "write_file": [{"priority": 1, "effect": 0, "conditions": {
    "file_path": {"pattern": "^(?!.*\\.env).*$"}
  }}]
}
```

**`.env`** - API keys:
```
OPENROUTER_API_KEY=sk-or-v1-xxx
```

## Repository Structure

```
progent/                      # PROGENT SDK (pip-installable library)
├── core.py                   # Policy enforcement engine
├── policy.py                 # Policy loading/saving
├── validation.py             # JSON Schema validation
├── wrapper.py                # @secure decorator
├── analysis.py               # Z3-based policy analysis (optional)
├── generation.py             # LLM policy generation (optional)
└── adapters/
    ├── langchain.py          # LangChain integration
    └── mcp.py                # MCP middleware

tests/                        # SDK tests
└── test_progent/

implementations/              # AGENT IMPLEMENTATIONS
├── core/                     # Shared infrastructure (stable)
│   ├── tool_definitions.py   # All tools defined HERE (single source)
│   ├── secured_executor.py   # Policy enforcement wrapper
│   ├── progent_enforcer.py   # Progent integration
│   └── logging_utils.py
├── frameworks/               # Agent adapters (stable)
│   ├── base_agent.py         # Shared agent logic
│   ├── langchain_agent.py    # LangChain adapter
│   ├── adk_agent.py          # Google ADK adapter
│   └── raw_sdk_agent.py      # OpenAI SDK adapter
├── tools/                    # Tool implementations (stable)
│   ├── file_tools.py
│   ├── command_tools.py
│   └── communication_tools.py
└── examples/                 # EXAMPLES (freely editable)
    └── coding_agent/         # Main example
        ├── run_agent.py      # Entry point
        ├── config.yaml       # Agent configuration
        ├── policies.json     # Security policies
        ├── sandbox/          # Workspace
        └── logs/

secagent/                     # Original implementation (reference only)
```

## What is `progent/`?

`progent/` is a **Python library** (SDK) that provides the core Progent policy engine:
- Framework-agnostic policy enforcement (`check_tool_call`, `@secure`)
- JSON Schema-based argument validation
- Optional adapters (LangChain, MCP)
- Optional analysis/generation modules

It is built and distributed as a **pip-installable package** via `pyproject.toml`

## Adding Tools

Edit `implementations/core/tool_definitions.py`:

```python
ToolDefinition(
    name="my_tool",
    description="What it does",
    parameters=[
        ToolParameter(name="arg1", type="string", description="..."),
    ],
    handler=my_function,
)
```

All frameworks automatically get the new tool.

## Creating New Examples

Copy an existing example and modify:

```bash
cd implementations/examples
cp -r coding_agent my_new_agent
# Edit config.yaml, policies.json, run_agent.py as needed
```

## REPL Commands

| Command | Action |
|---------|--------|
| `exit` | Quit |
| `clear` | Clear conversation |
| `verbose` | Toggle tool output |
