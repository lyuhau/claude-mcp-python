import asyncio
import logging
from typing import List

import mcp.types as types

from repl.tools.base import BaseTool

# Configure logging
logger = logging.getLogger('shell_status_tool')


class ShellStatusTool(BaseTool):
    """Check the status of background shell commands.
    
    # Operation
    1. Automatic Waiting:
       - If task is still running, waits up to 5 seconds for completion
       - Checks status every 100ms
       - Returns latest status even if task isn't finished
       - Can be called multiple times on the same task
    
    2. Status Values:
       - "pending": Task created but not started
       - "running": Task is currently executing
       - "completed": Task finished successfully
       - "failed": Task encountered an error
    
    3. Response Format:
       ```
       Status: completed
       Execution time: 1.2345 seconds
       
       Standard Output:
       <stdout content>
       
       Standard Error:
       <stderr content>
       
       Return Value:
       0
       ```
    
    # Best Practices
    1. Status Checking:
       - No need to wait before checking status
       - Tool automatically waits up to 5 seconds
       - Can check status immediately after getting task ID
       Example:
       ```python
       task = await shell.execute({"command": "long_command"})
       status = await shell_status.execute({"task_id": task_id})
       # Status includes results if completed within 5s
       ```
    
    2. Multiple Checks:
       - Safe to check status multiple times
       - Each check waits up to 5 seconds
       - Previous checks don't affect later ones
       Example:
       ```python
       status1 = await shell_status.execute({"task_id": task_id})
       # Shows "running" if not done
       status2 = await shell_status.execute({"task_id": task_id})
       # Shows results once complete
       ```
    
    3. Task Lifecycle:
       - Task IDs remain valid until server restart
       - Can check old tasks' status and output
       - Failed tasks include error details in stderr
    
    4. Error Handling:
       - Invalid task IDs raise immediate error
       - Check status field to determine completion
       - Non-zero return values indicate command failure
    """

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
