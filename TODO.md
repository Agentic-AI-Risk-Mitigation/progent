# TODO - Weak Spots & Next Steps

## Weak (Exists but Needs Work)

| Area | File | Issue |
|------|------|-------|
| **MCP Adapter** | `progent/adapters/mcp.py` | Code exists but no real-world testing (currently I use local python tools, no MCP server) |
| **LangChain Adapter** | `progent/adapters/langchain.py` | Basic implementation, edge cases untested |
| **ADK Agent** | `implementations/frameworks/adk_agent.py` | Less tested than LangChain |
| **Raw SDK Agent** | `implementations/frameworks/raw_sdk_agent.py` | Less tested than LangChain |
| **Z3 Regex Conversion** | `progent/analysis.py` | Complex regex-to-Z3 may fail on edge cases (actually we can discuss using a different language for policy definition) |
| **Policy Type Checking** | `progent/validation.py` | **IMPROVED**: Added `validate_policy_against_tools` for deep validation against tool definitions. |
| **LLM Policy Generation** | `progent/generation.py` | Working, but needs more testing and integration into agent loop |

## Not Working / Untested

| Area | File | Issue |
|------|------|-------|
| **State/History Tracking** | N/A | Not implemented - policies are stateless, no conditional rules like "if tool A used, block tool B" (This is not a feature of Progent) |
| **Declarative Policy Updates** | `progent/core.py` | The `"update"` field in policy rules is not implemented |

## Missing Tests

- [x] Integration tests for full agent loop (user prompt → tool call → policy check → result)
- [x] Tests for `progent/generation.py` (Implemented `tests/test_progent/test_generation.py`)
- [x] Tests for `progent/adapters/mcp.py` and `progent/adapters/langchain.py` (Added mock tests)
- [x] Security benchmarks (does policy actually block attacks?) - **Implemented `implementations/evals/`**
- [x] Utility benchmarks (does policy break legitimate tasks?) - **Implemented `implementations/evals/`**

**Evaluation Framework (`implementations/evals/`):**

**Current State: Basic Coverage (~30% comprehensive)**
- 9 scenarios testing fundamental security and utility
- Structured logging to track blocked/allowed tools
- Cross-platform support (Windows/Unix commands)
- Mock data for reproducible tests

**What IS Tested:**
- **Valid Use Cases:** Fetch data, clone repos, install packages
  - Tests: Policies don't break legitimate workflows
- **Direct Prompt Injection:** "Ignore instructions", "Developer mode"
  - Tests: Policies block jailbreak attempts
- **Tool Misuse:** Dangerous commands (rm -rf, del *.*), reading secrets (.env)
  - Tests: Both policy blocks AND agent safety judgment
- **Indirect Injection:** Following malicious instructions, data exfiltration
  - Tests: Agent refuses based on ethical judgment

**What needs improvement (NOT Tested):**
- Multi-step attack chains (install package → use to read .env)
- Encoding/obfuscation (base64, Unicode, command substitution)
- Context manipulation (long prompts, token smuggling)
- Tool chaining exploits (write malicious script → execute)
- Path traversal (../../.env variants)
- Realistic adversarial prompts (current tests too simple)
- Better validators (parse actual tool calls, not keywords)
- More scenarios (need 50-100 for production, have 9)

## Improvements Needed

- [x] **Better error messages** - When policy blocks, explain why clearly (added `policy_rule` and `failed_condition` to `ProgentBlockedError`)
- [x] **Policy debugging tool / traceability** - "Why was this call blocked?" (Implemented `progent/cli.py`)
- [x] **Policy conflict detection UI** - Make Z3 analysis accessible
- [ ] **Documentation** - API reference for `progent` library

- [x] `implementations/core/progent_enforcer.py` duplicates some logic from `progent/core.py` (Refactored to use `progent.registry`)
- [x] Logging is scattered - could be centralized (Implemented `progent/logger.py`)
- [x] No CI/CD pipeline for running tests (`.github/workflows/ci.yml`)

