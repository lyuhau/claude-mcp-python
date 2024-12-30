import asyncio
import time
from typing import List

import mcp.types as types

from repl.tools.base import BaseTool, CodeOutput


class ShellTool(BaseTool):
    """Tool for executing shell commands"""

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return """Execute shell commands in a sandboxed environment.

The 'shell' tool is ideal for:
- Quick, one-off shell command execution
- System information queries
- File operations
- Process management
- Network diagnostics
- Pipeline commands

Key features:
- Fresh environment for each execution
- Non-sandboxed environment
- Command output capture
- Timing information
- Error handling

REMEMBER: Be cautious when executing shell commands, as they can have side effects on the system. With great power comes great responsibility!
"""

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                },
                "shell": {
                    "type": "string",
                    "description": "Shell to use (bash/sh/zsh)",
                    "default": "bash",
                    "enum": ["bash", "sh", "zsh"]
                }
            },
            "required": ["command"]
        }

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        command = arguments.get("command")
        if not command:
            raise ValueError("Missing command parameter")

        shell = arguments.get("shell", "bash")
        output = await self._execute_command(command, shell)
        return output.format_output()

    async def _execute_command(self, command: str, shell: str = "bash") -> CodeOutput:
        """Execute shell command and capture output"""
        output = CodeOutput()
        start_time = time.time()

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                shell,
                "-c",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for the command to complete and capture output
            stdout, stderr = await process.communicate()

            # Decode output
            output.stdout = stdout.decode() if stdout else ""
            output.stderr = stderr.decode() if stderr else ""

            # Store return code
            output.result = process.returncode

        except Exception as e:
            output.stderr = f"Error executing command: {str(e)}"
        finally:
            output.execution_time = time.time() - start_time

        return output
