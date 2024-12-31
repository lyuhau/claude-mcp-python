import logging
import pathlib
import asyncio
from typing import List

import mcp.types as types
from repl.tools.base import BaseTool

# Configure logging
logger = logging.getLogger('shell_status_tool')
logger.setLevel(logging.DEBUG)

# Create handlers
log_file = pathlib.Path('/mnt/d/Users/HauHau/PycharmProjects/claude/repl/logs/shell_status.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Create formatters and add it to handlers
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
file_handler.setFormatter(logging.Formatter(log_format))

# Add handlers to the logger
logger.addHandler(file_handler)

class ShellStatusTool(BaseTool):
    """Tool for checking shell command status"""

    MAX_WAIT = 5.0  # Maximum time to wait for task completion

    def __init__(self, shell_tool):
        self.shell_tool = shell_tool

    @property
    def name(self) -> str:
        return "shell_status"

    @property
    def description(self) -> str:
        return """Check the status of a shell command that switched to async mode.
Provide the task ID that was returned by the shell command.
Will wait up to 5 seconds for task completion."""

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID from shell command"
                }
            },
            "required": ["task_id"]
        }

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        task_id = arguments.get("task_id")
        if not task_id:
            raise ValueError("Missing task_id parameter")

        if task_id not in self.shell_tool.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.shell_tool.tasks[task_id]
        logger.debug(f"Checking status of task {task_id}: {task.status}")

        # If task isn't completed yet, wait up to MAX_WAIT seconds
        if task.status == "running":
            try:
                start_time = asyncio.get_event_loop().time()
                while (asyncio.get_event_loop().time() - start_time) < self.MAX_WAIT:
                    if task.status != "running":
                        break
                    await asyncio.sleep(0.1)  # Check every 100ms
            except Exception as e:
                logger.error(f"Error while waiting for task completion: {e}")

        # Now format the response
        status_text = f"Status: {task.status}\n"
        if task.execution_time:
            status_text += f"Execution time: {task.execution_time:.4f} seconds\n"
        if task.stdout:
            status_text += f"\nStandard Output:\n{task.stdout}\n"
        if task.stderr:
            status_text += f"\nStandard Error:\n{task.stderr}\n"
        if task.result is not None:
            status_text += f"\nReturn Value:\n{task.result}"

        return [types.TextContent(
            type="text",
            text=status_text
        )]