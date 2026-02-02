"""
Google ADK (Agent Development Kit) based agent implementation.

This is a THIN ADAPTER that:
1. Converts unified tool definitions to Gemini FunctionDeclaration format
2. Initializes the Gemini model and handles function calling

Tool definitions and policy enforcement are handled by core modules.
DO NOT define tools or policy logic here.
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

from frameworks.base_agent import BaseAgent
from core.progent_enforcer import init_progent
from core.tool_definitions import TOOL_DEFINITIONS, ToolDefinition
from core.secured_executor import create_secured_handler


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
        
        genai.configure(api_key=api_key)
        
        # Get model from config
        llm_config = config.get("llm", {})
        model_name = llm_config.get("model", "gemini-1.5-flash")
        
        # Convert OpenRouter model names to Gemini
        if "/" in model_name:
            model_name = "gemini-1.5-flash"
        
        # Initialize Progent policies
        if policies_path:
            tool_defs = [
                {"name": t.name, "description": t.description, "args": {}}
                for t in TOOL_DEFINITIONS
            ]
            init_progent(policies_path, tool_defs)
        
        # Create tools (converted from unified definitions)
        self.tool_handlers = self._create_handlers()
        self.tools = self._create_tools()
        
        # Create the model
        self.model = genai.GenerativeModel(
            model_name=model_name,
            tools=self.tools,
            system_instruction=config.get("agent", {}).get("system_prompt", ""),
        )
        
        # Start chat session
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)
    
    def _create_handlers(self) -> dict[str, Any]:
        """Create secured handlers for all tools."""
        return {
            tool_def.name: create_secured_handler(tool_def)
            for tool_def in TOOL_DEFINITIONS
        }
    
    def _create_tools(self) -> list[Tool]:
        """Convert unified tool definitions to Gemini FunctionDeclaration format."""
        declarations = []
        
        for tool_def in TOOL_DEFINITIONS:
            declarations.append(FunctionDeclaration(
                name=tool_def.name,
                description=tool_def.description,
                parameters=tool_def.to_json_schema(),
            ))
        
        return [Tool(function_declarations=declarations)]
    
    def _execute_function_call(self, function_call) -> str:
        """Execute a function call from the model."""
        name = function_call.name
        args = dict(function_call.args)
        
        if name in self.tool_handlers:
            return self.tool_handlers[name](**args)
        return f"Unknown function: {name}"
    
    def run(self, user_input: str) -> str:
        """Process user input and return response."""
        try:
            response = self.chat.send_message(user_input)
            
            # Process function calls
            while response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                
                if hasattr(part, 'function_call') and part.function_call:
                    result = self._execute_function_call(part.function_call)
                    
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
                    break
            
            if response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return "No response generated."
            
        except Exception as e:
            self.logger.error("ADK agent execution error", e)
            return f"Error: {e}"
    
    def get_tools(self) -> list:
        """Get the list of tools."""
        return self.tools
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)
