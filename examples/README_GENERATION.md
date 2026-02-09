# LLM Policy Generation Example

Run this example to see how LLM-based policy generation works:

```bash
# Set your API key
export OPENAI_API_KEY="your-key-here"

# Run the example
python examples/llm_policy_generation.py
```

The example will:
1. Register three tools (send_email, read_file, delete_file)
2. Generate a security policy from the query: "Send an email to john@example.com about the meeting tomorrow"
3. Ask you to approve the generated policy
4. Test the policy with allowed and blocked calls

## What the LLM generates

For the query above, the LLM typically generates:
```json
{
    "send_email": {
        "to": {"enum": ["john@example.com"]},
        "subject": {"pattern": ".*meeting.*"}
    }
}
```

This allows sending email **only to john@example.com** and **only about meetings**.

## CLI Usage

You can also use the CLI (though you need to register tools programmatically first):

```bash
progent generate --query "Send email to john@example.com" --manual-check
```

## Environment Variables

- `OPENAI_API_KEY` - For OpenAI models (default: gpt-4o)
- `ANTHROPIC_API_KEY` - For Claude models
- `PROGENT_POLICY_MODEL` - Override the model (e.g., "gpt-4o-mini", "claude-3-7-sonnet-20250219")
