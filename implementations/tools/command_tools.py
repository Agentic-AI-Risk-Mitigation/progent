"""Command execution tools for the coding agent."""

import subprocess

# Import workspace from file_tools to ensure consistency
from .file_tools import get_workspace


def run_command(command: str, timeout: int = 60) -> str:
    """
    Execute a shell command in the workspace directory.

    The command runs with the workspace as the current directory.
    Standard output and error are captured and returned.

    :param command: The shell command to execute
    :param timeout: Maximum execution time in seconds (default: 60)
    :return: The command output (stdout and stderr combined)
    """
    workspace = get_workspace()

    try:
        # Run the command
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Combine stdout and stderr
        output_parts = []

        if result.stdout:
            output_parts.append(result.stdout)

        if result.stderr:
            if output_parts:
                output_parts.append("\n[STDERR]:\n")
            output_parts.append(result.stderr)

        output = "".join(output_parts).strip()

        # Add exit code info if non-zero
        if result.returncode != 0:
            output += f"\n\n[Exit code: {result.returncode}]"

        if not output:
            output = f"Command completed successfully (exit code: {result.returncode})"

        return output

    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Command execution failed: {type(e).__name__}: {e}"
