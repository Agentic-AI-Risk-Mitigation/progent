# TODO - Weak Spots & Next Steps

## Weak (Exists but Needs Work)

| Area | File | Issue |
|------|------|-------|
| **MCP Adapter** | `progent/adapters/mcp.py` | Code exists but no real-world testing (currently I use local python tools, no MCP server) |
| **LangChain Adapter** | `progent/adapters/langchain.py` | Basic implementation, edge cases untested |
| **ADK Agent** | `implementations/frameworks/adk_agent.py` | Less tested than LangChain |
| **Raw SDK Agent** | `implementations/frameworks/raw_sdk_agent.py` | Less tested than LangChain |
| **Z3 Regex Conversion** | `progent/analysis.py` | Complex regex-to-Z3 may fail on edge cases (actually we can discuss using a different language for policy definition) |
| **Policy Type Checking** | `progent/validation.py` | Missing: validation against `available_tools_dict`, full JSON Schema structure checks (secagent/policy_type_check.py is more comprehensive) |

## Not Working / Untested

| Area | File | Issue |
|------|------|-------|
| **LLM Policy Generation** | `progent/generation.py` | Not tested, not integrated into agent loop |
| **State/History Tracking** | N/A | Not implemented - policies are stateless, no conditional rules like "if tool A used, block tool B" (This is not a feature of Progent) |
| **Declarative Policy Updates** | `progent/core.py` | The `"update"` field in policy rules is not implemented |

## Missing Tests

- [x] Integration tests for full agent loop (user prompt → tool call → policy check → result)
- [ ] Tests for `progent/generation.py`
- [ ] Tests for `progent/adapters/mcp.py` with real MCP server
- [ ] Tests for `progent/adapters/langchain.py`
- [ ] Security benchmarks (does policy actually block attacks?)
- [ ] Utility benchmarks (does policy break legitimate tasks?)

## Improvements Needed

- [ ] **Better error messages** - When policy blocks, explain why clearly
- [ ] **Policy debugging tool / traceability** - "Why was this call blocked?"
- [ ] **Policy conflict detection UI** - Make Z3 analysis accessible
- [ ] **Documentation** - API reference for `progent` library

- [ ] `implementations/core/progent_enforcer.py` duplicates some logic from `progent/core.py`
- [ ] Logging is scattered - could be centralized
- [x] No CI/CD pipeline for running tests (`.github/workflows/ci.yml`)

