import asyncio
import logging
import os
import pathlib
import time
import uuid
from typing import List, Dict, Optional

import mcp.types as types

from repl.tools.base import BaseTool, CodeOutput

# Configure logging
logger = logging.getLogger('shell_tool')


class ShellTask:
    def __init__(self, command: str, shell: str, working_dir: str):
        self.id = str(uuid.uuid4())
        self.command = command
        self.shell = shell
        self.working_dir = working_dir
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status = "pending"  # pending, running, completed, failed
        self.stdout = ""
        self.stderr = ""
        self.result = None
        self.execution_time = None
        self.start_time = None


class ShellTool(BaseTool):
    """Execute shell commands with automatic async mode for long-running commands.

    # Operation Modes
    1. Quick Commands (under 5 seconds):
       - Returns results immediately in the same response
       - Output includes stdout, stderr, execution time, and return value
       Example:
       ```
       Standard Output: hello world
       Standard Error: 
       Execution time: 0.0123 seconds
       Return Value: 0
       ```

    2. Long Commands (over 5 seconds):
       - Switches to async mode automatically
       - Returns a task ID immediately
       - Command continues running in the background
       - Use shell_status tool to check progress
       Example:
       ```
       Task started with ID: 1234-5678-90
       Use shell_status with this task ID to check progress.
       ```

    # Best Practices
    1. Single Commands:
       - Prefer single commands over chained commands
       - Each shell invocation has its own 5-second timeout
       Bad:  "wget file && tar xf file && rm file"  # Might timeout mid-chain
       Good: Run each command separately with status checks

    2. Working Directory:
       - If unspecified, defaults to user's home directory
       - Must exist or command will fail with error
       - Persists only for the single command

    3. Shell Selection:
       - Defaults to 'bash'
       - Available shells: bash, sh, zsh
       - Each command runs in a fresh shell instance
    
    4. Background Operation:
       - Long commands run fully in background
       - Can run multiple async commands in parallel
       - Use shell_status to track each task separately
       
    5. Error Handling:
       - Always check return value for non-zero exit codes
       - stderr may contain important messages even on success
       - Failed commands include error details in stderr

    # Common Patterns
    1. Quick Command:
       ```python
       response = await shell.execute({"command": "echo hello"})
       # Immediate response with output
       ```

    2. Long Command:
       ```python
       task = await shell.execute({"command": "sleep 10"})
       # Returns task ID immediately
       status = await shell_status.execute({"task_id": task_id})
       # Check status after a few seconds
       ```
    """

    SYNC_TIMEOUT = 5.0  # Switch to async mode if command doesn't complete within 5 seconds

    def __init__(self):
        self.tasks: Dict[str, ShellTask] = {}

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return """Execute shell commands with automatic async fallback.

If the command completes within 5 seconds, you'll get the result immediately.
If it takes longer, you'll get a task ID that you can use to check status with shell_status.

Example responses:
1. Quick command:
   Standard Output: <output>
   Standard Error: <error>
   Return Value: 0

2. Long-running command:
   Task started with ID: 1234-5678-90
   Use shell_status with this task ID to check progress."""

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "shell": {
                    "type": "string",
                    "description": "Shell to use (bash/sh/zsh)",
                    "default": "bash",
                    "enum": ["bash", "sh", "zsh"]
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory to execute the command in (defaults to user home)",
                    "default": ""
                },
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        command = arguments.get("command")
        if not command:
            raise ValueError("Missing command parameter")

        shell = arguments.get("shell", "bash")
        working_dir = arguments.get("working_dir")

        if not working_dir:
            working_dir = pathlib.Path.home()

        # Verify working directory exists
        if working_dir and not os.path.exists(working_dir):
            raise ValueError(f"Working directory does not exist: {working_dir}")

        # Create task
        task = ShellTask(command, shell, working_dir)
        self.tasks[task.id] = task
        logger.info(f"Created task {task.id} for command: {command}")

        try:
            # Try to execute synchronously with timeout
            result = await asyncio.wait_for(
                self._execute_task(task.id),
                timeout=self.SYNC_TIMEOUT
            )

            # If we get here, command completed within timeout
            output_text = ""
            if result.stdout:
                output_text += f"Standard Output:\n{result.stdout}\n"
            if result.stderr:
                output_text += f"Standard Error:\n{result.stderr}\n"
            output_text += f"Execution time: {result.execution_time:.4f} seconds\n"
            output_text += f"Return Value:\n{result.result}"

            return [types.TextContent(
                type="text",
                text=output_text
            )]

        except asyncio.TimeoutError:
            # Command is taking too long, switch to async mode
            logger.info(f"Command taking longer than {self.SYNC_TIMEOUT}s, switching to async mode")

            # Make sure the task continues running in the background
            asyncio.create_task(self._execute_task(task.id))

            return [types.TextContent(
                type="text",
                text=f"Task started with ID: {task.id}\nUse shell_status with this task ID to check progress."
            )]

    async def _execute_task(self, task_id: str) -> CodeOutput:
        task = self.tasks[task_id]
        output = CodeOutput()
        task.status = "running"
        task.start_time = time.time()

        try:
            logger.debug(f"Creating subprocess for task {task_id}")
            task.process = await asyncio.create_subprocess_exec(
                task.shell,
                "-c",
                task.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task.working_dir
            )

            logger.info(f"Process created with PID: {task.process.pid}")

            # Wait for the command to complete and capture output
            stdout, stderr = await task.process.communicate()

            # Store results
            output.stdout = stdout.decode() if stdout else ""
            output.stderr = stderr.decode() if stderr else ""
            output.result = task.process.returncode

            # Update task status
            task.stdout = output.stdout
            task.stderr = output.stderr
            task.result = output.result
            task.status = "completed"
            task.execution_time = time.time() - task.start_time
            output.execution_time = task.execution_time

            logger.info(f"Task {task_id} completed with return code: {task.result}")
            if output.stderr:
                logger.warning(f"Task {task_id} stderr output: {output.stderr}")

        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            logger.error(error_msg, exc_info=True)
            output.stderr = error_msg
            task.stderr = error_msg
            task.status = "failed"
            task.execution_time = time.time() - task.start_time
            output.execution_time = task.execution_time
            output.result = -1
            task.result = -1

        return output
