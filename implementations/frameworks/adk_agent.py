"""Google ADK (Agent Development Kit) based agent implementation."""

import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

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


class ADKAgent(BaseAgent):
    """
    Agent implementation using Google's Generative AI SDK (ADK).
    
    Uses Gemini models with function calling capabilities.
    """
    
    def __init__(
        self,
        config: dict[str, Any],
        workspace: str | Path,
        policies_path: Optional[str | Path] = None,
    ):
        if not ADK_AVAILABLE:
            raise ImportError(
                "Google Generative AI SDK not installed. "
                "Install with: pip install google-generativeai"
            )
        
        super().__init__(config, workspace)
        
        # Get API key from environment
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set")
        
        # Configure the SDK
        genai.configure(api_key=api_key)
        
        # Get model from config (default to Gemini 1.5 Flash for cost efficiency)
        llm_config = config.get("llm", {})
        model_name = llm_config.get("model", "gemini-1.5-flash")
        
        # If using OpenRouter model name, convert to Gemini
        if "/" in model_name:
            model_name = "gemini-1.5-flash"  # Default for non-Gemini models
        
        # Create tool declarations
        self.tool_functions = self._create_tool_functions()
        self.tools = self._create_tools()
        
        # Initialize Progent
        if policies_path:
            tool_definitions = [
                {"name": name, "description": func.__doc__ or "", "args": {}}
                for name, func in self.tool_functions.items()
            ]
            init_progent(policies_path, tool_definitions)
        
        # Create the model with tools
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=self.tools,
            system_instruction=config.get("agent", {}).get("system_prompt", ""),
        )
        
        # Start a chat session
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)
    
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
    
    def _create_tools(self) -> list:
        """Create Gemini tool declarations."""
        return [
            Tool(function_declarations=[
                FunctionDeclaration(
                    name="read_file",
                    description="Read the contents of a file",
                    parameters={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read (relative to workspace)"
                            }
                        },
                        "required": ["file_path"]
                    }
                ),
                FunctionDeclaration(
                    name="write_file",
                    description="Create or overwrite a file with the given content",
                    parameters={
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
                ),
                FunctionDeclaration(
                    name="edit_file",
                    description="Edit a file by replacing a specific string with a new string",
                    parameters={
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
                ),
                FunctionDeclaration(
                    name="list_directory",
                    description="List the contents of a directory",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the directory to list (relative to workspace)"
                            }
                        },
                        "required": []
                    }
                ),
                FunctionDeclaration(
                    name="run_command",
                    description="Execute a shell command in the workspace directory",
                    parameters={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                ),
                FunctionDeclaration(
                    name="send_email",
                    description="Send an email notification",
                    parameters={
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
                ),
            ])
        ]
    
    def _execute_function_call(self, function_call) -> str:
        """Execute a function call from the model."""
        name = function_call.name
        args = dict(function_call.args)
        
        if name in self.tool_functions:
            return self.tool_functions[name](**args)
        else:
            return f"Unknown function: {name}"
    
    def run(self, user_input: str) -> str:
        """Process user input and return response."""
        try:
            # Send message to the model
            response = self.chat.send_message(user_input)
            
            # Process function calls if any
            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                
                if hasattr(part, 'function_call') and part.function_call:
                    # Execute the function
                    result = self._execute_function_call(part.function_call)
                    
                    # Send the result back to the model
                    response = self.chat.send_message(
                        genai.protos.Content(
                            parts=[genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=part.function_call.name,
                                    response={"result": result}
                                )
                            )]
                        )
                    )
                else:
                    # No more function calls, get the text response
                    break
            
            # Extract text response
            if response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            else:
                return "No response generated."
                
        except Exception as e:
            self.logger.error("ADK agent execution error", e)
            return f"Error: {e}"
    
    def get_tools(self) -> list:
        """Get the list of tools."""
        return self.tools
    
    def clear_history(self) -> None:
        """Clear conversation history by starting a new chat."""
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)
