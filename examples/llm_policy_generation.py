#!/usr/bin/env python3
"""
Example: LLM-based Policy Generation

This example demonstrates how to use Progent's LLM-based policy generation.
The LLM automatically creates security policies based on your task description.

Requirements:
    pip install progent[generation]
    export OPENAI_API_KEY="your-key-here"
"""

import os

from progent import (
    ProgentBlockedError,
    check_tool_call,
    generate_policies,
    update_available_tools,
)


# Step 1: Define and register some tools
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}"


def read_file(path: str) -> str:
    """Read a file from disk."""
    return f"Contents of {path}"


def delete_file(path: str) -> str:
    """Delete a file from disk."""
    return f"Deleted {path}"


# Register tools with Progent
tools = [
    {
        "name": "send_email",
        "description": "Send an email",
        "args": {
            "to": {"type": "string", "description": "Recipient email"},
            "subject": {"type": "string", "description": "Email subject"},
            "body": {"type": "string", "description": "Email body"},
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from disk",
        "args": {"path": {"type": "string", "description": "File path"}},
    },
    {
        "name": "delete_file",
        "description": "Delete a file from disk",
        "args": {"path": {"type": "string", "description": "File path"}},
    },
]

update_available_tools(tools)

# Step 2: Generate policy from user query
print("=" * 60)
print("EXAMPLE: Generating security policy with LLM")
print("=" * 60)

user_query = "Send an email to john@example.com about the meeting tomorrow"

print(f"\nUser query: {user_query}")
print("\nGenerating policy...")

if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
    print("\n⚠️  No API key found!")
    print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use policy generation.")
    print("\nExample policy that would be generated:")
    print("""
    {
        "send_email": [
            (100, 0, {
                "to": {"enum": ["john@example.com"]},
                "subject": {"pattern": ".*meeting.*"}
            }, 0)
        ]
    }
    """)
else:
    # Generate with manual confirmation
    generated = generate_policies(
        query=user_query,
        manual_confirm=True,  # Ask user to approve
    )

    if generated:
        print(f"\n✅ Generated policy for {len(generated)} tools")

        # Step 3: Test the policy
        print("\n" + "=" * 60)
        print("Testing generated policy...")
        print("=" * 60)

        # This should be ALLOWED
        print("\n1. Allowed call:")
        try:
            check_tool_call(
                "send_email",
                {
                    "to": "john@example.com",
                    "subject": "Meeting tomorrow",
                    "body": "Let's meet at 2pm",
                },
            )
            print("   ✅ ALLOWED")
        except ProgentBlockedError as e:
            print(f"   ❌ BLOCKED: {e.reason}")

        # This should be BLOCKED (wrong recipient)
        print("\n2. Blocked call (wrong recipient):")
        try:
            check_tool_call(
                "send_email",
                {
                    "to": "attacker@evil.com",
                    "subject": "Meeting tomorrow",
                    "body": "Malicious content",
                },
            )
            print("   ✅ ALLOWED")
        except ProgentBlockedError as e:
            print(f"   ❌ BLOCKED: {e.reason}")

        # This should be BLOCKED (unrelated tool)
        print("\n3. Blocked call (unrelated tool):")
        try:
            check_tool_call("delete_file", {"path": "/etc/passwd"})
            print("   ✅ ALLOWED")
        except ProgentBlockedError as e:
            print(f"   ❌ BLOCKED: {e.reason}")
    else:
        print("\n⚠️  Policy generation cancelled or failed")
