"""LangChain-based agent implementation."""

import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool as langchain_tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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


class LangChainAgent(BaseAgent):
    """
    Agent implementation using LangChain.
    
    Uses ChatOpenAI with OpenRouter as the backend,
    and LangChain's tool calling agent.
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
        model = llm_config.get("model", "meta-llama/llama-3.1-70b-instruct")
        
        # Get API key from environment
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        
        # Initialize the LLM
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.1,
        )
        
        # Create tools with policy enforcement
        self.tools = self._create_tools()
        
        # Initialize Progent
        if policies_path:
            tool_definitions = [
                {"name": t.name, "description": t.description, "args": {}}
                for t in self.tools
            ]
            init_progent(policies_path, tool_definitions)
        
        # Create the agent
        self.agent_executor = self._create_agent(config)
        
        # Conversation history
        self.chat_history = []
    
    def _create_tools(self) -> list:
        """Create LangChain tools with Progent policy enforcement."""
        logger = get_logger()
        
        @langchain_tool
        def read_file(file_path: str) -> str:
            """Read the contents of a file.
            
            Args:
                file_path: Path to the file to read (relative to workspace)
            """
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
        
        @langchain_tool
        def write_file(file_path: str, content: str) -> str:
            """Create or overwrite a file with the given content.
            
            Args:
                file_path: Path to the file to write (relative to workspace)
                content: The content to write to the file
            """
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
        
        @langchain_tool
        def edit_file(file_path: str, old_string: str, new_string: str) -> str:
            """Edit a file by replacing a specific string with a new string.
            
            The old_string must exist in the file exactly once for the replacement to succeed.
            
            Args:
                file_path: Path to the file to edit (relative to workspace)
                old_string: The exact string to find and replace
                new_string: The string to replace it with
            """
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
        
        @langchain_tool
        def list_directory(path: str = ".") -> str:
            """List the contents of a directory.
            
            Args:
                path: Path to the directory to list (relative to workspace, defaults to workspace root)
            """
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
        
        @langchain_tool
        def run_command(command: str) -> str:
            """Execute a shell command in the workspace directory.
            
            Args:
                command: The shell command to execute
            """
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
        
        @langchain_tool
        def send_email(to: str, subject: str, body: str) -> str:
            """Send an email notification.
            
            Args:
                to: The recipient email address
                subject: The email subject line
                body: The email body content
            """
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
        
        return [read_file, write_file, edit_file, list_directory, run_command, send_email]
    
    def _create_agent(self, config: dict[str, Any]) -> AgentExecutor:
        """Create the LangChain agent executor."""
        # Get system prompt
        agent_config = config.get("agent", {})
        system_prompt = agent_config.get("system_prompt", "You are a helpful coding assistant.")
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        # Create executor
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,  # We handle our own logging
            handle_parsing_errors=True,
            max_iterations=10,
        )
        
        return executor
    
    def run(self, user_input: str) -> str:
        """Process user input and return response."""
        try:
            result = self.agent_executor.invoke({
                "input": user_input,
                "chat_history": self.chat_history,
            })
            
            response = result.get("output", "No response generated.")
            
            # Update chat history
            self.chat_history.append(HumanMessage(content=user_input))
            self.chat_history.append(AIMessage(content=response))
            
            return response
            
        except Exception as e:
            self.logger.error("Agent execution error", e)
            return f"Error: {e}"
    
    def get_tools(self) -> list:
        """Get the list of tools."""
        return self.tools
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.chat_history = []
