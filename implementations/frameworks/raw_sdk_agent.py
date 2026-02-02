"""
Raw SDK agent implementation using OpenAI-compatible APIs directly.

This is a THIN ADAPTER that:
1. Converts unified tool definitions to OpenAI function format
2. Handles the tool calling loop manually

Tool definitions and policy enforcement are handled by core modules.
DO NOT define tools or policy logic here.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openai import OpenAI

from frameworks.base_agent import BaseAgent
from core.progent_enforcer import init_progent
from core.tool_definitions import TOOL_DEFINITIONS, ToolDefinition
from core.secured_executor import create_secured_handler


class RawSDKAgent(BaseAgent):
    """
    Agent implementation using the raw OpenAI SDK.
    
    Compatible with OpenRouter and other OpenAI-compatible APIs.
    """
    
    def __init__(
        self,
        config: dict[str, Any],
        workspace: str | Path,
        policies_path: Optional[str | Path] = None,
    ):
        super().__init__(config, workspace)
        
        # Get LLM config
        llm_config = config.get("llm", {})
        api_base = llm_config.get("api_base", "https://openrouter.ai/api/v1")
        self.model = llm_config.get("model", "meta-llama/llama-3.1-70b-instruct")
        
        # Get API key from environment
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY or OPENAI_API_KEY environment variable not set")
        
        # Initialize the client
        self.client = OpenAI(api_key=api_key, base_url=api_base)
        
        # Initialize Progent policies
        if policies_path:
            tool_defs = [
                {"name": t.name, "description": t.description, "args": {}}
                for t in TOOL_DEFINITIONS
            ]
            init_progent(policies_path, tool_defs)
        
        # Create tools (converted from unified definitions)
        self.tool_handlers = self._create_handlers()
        self.tools_schema = self._create_tools_schema()
        
        # System prompt
        self.system_prompt = config.get("agent", {}).get(
            "system_prompt",
            "You are a helpful coding assistant."
        )
        
        # Conversation history
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def _create_handlers(self) -> dict[str, Any]:
        """Create secured handlers for all tools."""
        return {
            tool_def.name: create_secured_handler(tool_def)
            for tool_def in TOOL_DEFINITIONS
        }
    
    def _create_tools_schema(self) -> list[dict[str, Any]]:
        """Convert unified tool definitions to OpenAI function calling format."""
        tools = []
        
        for tool_def in TOOL_DEFINITIONS:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_def.name,
                    "description": tool_def.description,
                    "parameters": tool_def.to_json_schema(),
                }
            })
        
        return tools
    
    def _execute_tool_call(self, tool_call) -> str:
        """Execute a tool call and return the result."""
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {tool_call.function.arguments}"
        
        if name in self.tool_handlers:
            return self.tool_handlers[name](**args)
        return f"Unknown function: {name}"
    
    def run(self, user_input: str) -> str:
        """Process user input and return response."""
        try:
            self.messages.append({"role": "user", "content": user_input})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.tools_schema,
                tool_choice="auto",
                temperature=0.1,
            )
            
            assistant_message = response.choices[0].message
            
            # Process tool calls in a loop
            max_iterations = 10
            iteration = 0
            
            while assistant_message.tool_calls and iteration < max_iterations:
                iteration += 1
                
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                for tool_call in assistant_message.tool_calls:
                    result = self._execute_tool_call(tool_call)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.1,
                )
                
                assistant_message = response.choices[0].message
            
            final_response = assistant_message.content or "No response generated."
            self.messages.append({"role": "assistant", "content": final_response})
            
            return final_response
            
        except Exception as e:
            self.logger.error("Raw SDK agent execution error", e)
            return f"Error: {e}"
    
    def get_tools(self) -> list:
        """Get the list of tools."""
        return self.tools_schema
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
