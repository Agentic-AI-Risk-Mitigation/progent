# Progent Coding Agent

Secure coding agent with policy enforcement.

## Quick Start

```bash
# 1. Create environment
conda create -n progent python=3.11 -y
conda activate progent

# 2. Install dependencies
cd implementations
pip install -r requirements.txt
pip install -e ..  # Install secagent

# 3. Set API key
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
  "write_file": [{"priority": 1, "effect": "allow", "conditions": {
    "file_path": {"pattern": "^(?!.*\\.env).*$"}
  }}]
}
```

**`.env`** - API keys:
```
OPENROUTER_API_KEY=sk-or-v1-xxx
```

## Structure

```
implementations/
├── run_agent.py          # CLI entry point
├── config.yaml           # LLM and agent config
├── policies.json         # Security policies
├── core/
│   ├── tool_definitions.py   # All tools defined HERE (single source)
│   ├── secured_executor.py   # Policy enforcement wrapper
│   ├── progent_enforcer.py   # Progent integration
│   └── logging_utils.py      # Logging
├── frameworks/
│   ├── base_agent.py         # Shared agent logic
│   ├── langchain_agent.py    # LangChain adapter
│   ├── adk_agent.py          # Google ADK adapter
│   └── raw_sdk_agent.py      # OpenAI SDK adapter
├── tools/
│   ├── file_tools.py         # read/write/edit/list
│   ├── command_tools.py      # run_command
│   └── communication_tools.py # send_email (dummy)
├── sandbox/              # Default workspace
└── logs/                 # Agent logs
```

## Adding Tools

Edit `core/tool_definitions.py`:

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

## REPL Commands

| Command | Action |
|---------|--------|
| `exit` | Quit |
| `clear` | Clear conversation |
| `verbose` | Toggle tool output |
