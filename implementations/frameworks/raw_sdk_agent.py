"""Raw SDK agent implementation using OpenAI-compatible APIs directly."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openai import OpenAI

from frameworks.base_agent import BaseAgent
from core.logging_utils import get_logger
from core.progent_enforcer import init_progent, enforce_policy
from tools.file_tools import (
    read_file as _read_file,
    write_file as _write_file,
    edit_file as _edit_file,
    list_directory as _list_directory,
)
from tools.command_tools import run_command as _run_command
from tools.communication_tools import send_email as _send_email


class RawSDKAgent(BaseAgent):
    """
    Agent implementation using the raw OpenAI SDK.
    
    This is the most explicit implementation showing exactly how
    tool calling works. Compatible with OpenRouter and other
    OpenAI-compatible APIs.
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
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
        )
        
        # Create tool functions with policy enforcement
        self.tool_functions = self._create_tool_functions()
        
        # Create tool schemas for the API
        self.tools_schema = self._create_tools_schema()
        
        # Initialize Progent
        if policies_path:
            tool_definitions = [
                {"name": name, "description": func.__doc__ or "", "args": {}}
                for name, func in self.tool_functions.items()
            ]
            init_progent(policies_path, tool_definitions)
        
        # System prompt
        self.system_prompt = config.get("agent", {}).get(
            "system_prompt",
            "You are a helpful coding assistant."
        )
        
        # Conversation history
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def _create_tool_functions(self) -> dict[str, Callable]:
        """Create tool functions with policy enforcement."""
        logger = get_logger()
        
        def read_file(file_path: str) -> str:
            """Read the contents of a file."""
            logger.tool_call("read_file", {"file_path": file_path})
            allowed, reason = enforce_policy("read_file", {"file_path": file_path})
            if not allowed:
                result = f"Policy blocked: {reason}"
                logger.tool_result("read_file", result, success=False)
                return result
            try:
                result = _read_file(file_path)
                logger.tool_result("read_file", f"Read {len(result)} chars", success=True)
                return result
            except Exception as e:
                result = f"Error: {e}"
                logger.tool_result("read_file", result, success=False)
                return result
        
        def write_file(file_path: str, content: str) -> str:
            """Create or overwrite a file with the given content."""
            logger.tool_call("write_file", {"file_path": file_path, "content": f"[{len(content)} chars]"})
            allowed, reason = enforce_policy("write_file", {"file_path": file_path, "content": content})
            if not allowed:
                result = f"Policy blocked: {reason}"
                logger.tool_result("write_file", result, success=False)
                return result
            try:
                result = _write_file(file_path, content)
                logger.tool_result("write_file", result, success=True)
                return result
            except Exception as e:
                result = f"Error: {e}"
                logger.tool_result("write_file", result, success=False)
                return result
        
        def edit_file(file_path: str, old_string: str, new_string: str) -> str:
            """Edit a file by replacing a specific string with a new string."""
            logger.tool_call("edit_file", {
                "file_path": file_path,
                "old_string": f"[{len(old_string)} chars]",
                "new_string": f"[{len(new_string)} chars]"
            })
            allowed, reason = enforce_policy("edit_file", {
                "file_path": file_path,
                "old_string": old_string,
                "new_string": new_string
            })
            if not allowed:
                result = f"Policy blocked: {reason}"
                logger.tool_result("edit_file", result, success=False)
                return result
            try:
                result = _edit_file(file_path, old_string, new_string)
                logger.tool_result("edit_file", result, success=True)
                return result
            except Exception as e:
                result = f"Error: {e}"
                logger.tool_result("edit_file", result, success=False)
                return result
        
        def list_directory(path: str = ".") -> str:
            """List the contents of a directory."""
            logger.tool_call("list_directory", {"path": path})
            allowed, reason = enforce_policy("list_directory", {"path": path})
            if not allowed:
                result = f"Policy blocked: {reason}"
                logger.tool_result("list_directory", result, success=False)
                return result
            try:
                result = _list_directory(path)
                logger.tool_result("list_directory", result, success=True)
                return result
            except Exception as e:
                result = f"Error: {e}"
                logger.tool_result("list_directory", result, success=False)
                return result
        
        def run_command(command: str) -> str:
            """Execute a shell command in the workspace directory."""
            logger.tool_call("run_command", {"command": command})
            allowed, reason = enforce_policy("run_command", {"command": command})
            if not allowed:
                result = f"Policy blocked: {reason}"
                logger.tool_result("run_command", result, success=False)
                return result
            try:
                result = _run_command(command)
                logger.tool_result("run_command", result, success=True)
                return result
            except Exception as e:
                result = f"Error: {e}"
                logger.tool_result("run_command", result, success=False)
                return result
        
        def send_email(to: str, subject: str, body: str) -> str:
            """Send an email notification."""
            logger.tool_call("send_email", {"to": to, "subject": subject, "body": f"[{len(body)} chars]"})
            allowed, reason = enforce_policy("send_email", {"to": to, "subject": subject, "body": body})
            if not allowed:
                result = f"Policy blocked: {reason}"
                logger.tool_result("send_email", result, success=False)
                return result
            try:
                result = _send_email(to, subject, body)
                logger.tool_result("send_email", result, success=True)
                return result
            except Exception as e:
                result = f"Error: {e}"
                logger.tool_result("send_email", result, success=False)
                return result
        
        return {
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "list_directory": list_directory,
            "run_command": run_command,
            "send_email": send_email,
        }
    
    def _create_tools_schema(self) -> list[dict[str, Any]]:
        """Create OpenAI-compatible tool schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read (relative to workspace)"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or overwrite a file with the given content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to write (relative to workspace)"
                            },
                            "content": {
                                "type": "string",
                                "description": "The content to write to the file"
                            }
                        },
                        "required": ["file_path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edit a file by replacing a specific string with a new string. The old_string must exist exactly once in the file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to edit (relative to workspace)"
                            },
                            "old_string": {
                                "type": "string",
                                "description": "The exact string to find and replace"
                            },
                            "new_string": {
                                "type": "string",
                                "description": "The string to replace it with"
                            }
                        },
                        "required": ["file_path", "old_string", "new_string"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List the contents of a directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the directory to list (relative to workspace, defaults to workspace root)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Execute a shell command in the workspace directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send an email notification",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "The recipient email address"
                            },
                            "subject": {
                                "type": "string",
                                "description": "The email subject line"
                            },
                            "body": {
                                "type": "string",
                                "description": "The email body content"
                            }
                        },
                        "required": ["to", "subject", "body"]
                    }
                }
            }
        ]
    
    def _execute_tool_call(self, tool_call) -> str:
        """Execute a tool call and return the result."""
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {tool_call.function.arguments}"
        
        if name in self.tool_functions:
            return self.tool_functions[name](**args)
        else:
            return f"Unknown function: {name}"
    
    def run(self, user_input: str) -> str:
        """Process user input and return response."""
        try:
            # Add user message to history
            self.messages.append({"role": "user", "content": user_input})
            
            # Call the API
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
                
                # Add assistant message to history
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
                
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    result = self._execute_tool_call(tool_call)
                    
                    # Add tool result to history
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                
                # Get next response
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools_schema,
                    tool_choice="auto",
                    temperature=0.1,
                )
                
                assistant_message = response.choices[0].message
            
            # Get final text response
            final_response = assistant_message.content or "No response generated."
            
            # Add final assistant message to history
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
