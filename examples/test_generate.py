#!/usr/bin/env python3
"""
Quick test script to demonstrate progent generate with tools.

This script registers tools and then you can use the CLI.
Run this in one terminal, then use `progent generate` in another.
"""

from progent import generate_policies, update_available_tools

# Register some example tools
tools = [
    {
        "name": "send_email",
        "description": "Send an email to a recipient",
        "args": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body text"},
        },
    },
    {
        "name": "read_file",
        "description": "Read contents of a file",
        "args": {"path": {"type": "string", "description": "File path to read"}},
    },
    {
        "name": "write_file",
        "description": "Write content to a file",
        "args": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
        },
    },
    {
        "name": "execute_command",
        "description": "Execute a shell command",
        "args": {"command": {"type": "string", "description": "Shell command to execute"}},
    },
]

update_available_tools(tools)

# Now you can use generation

print("Tools registered. Generating policy...")
print()

generated = generate_policies(
    query="Send an email to john@example.com about the project status", manual_confirm=True
)

if generated:
    print(f"\n✅ Generated policy for {len(generated)} tools:")
    for tool_name in generated.keys():
        print(f"  - {tool_name}")
else:
    print("\n⚠️  No policy generated")
