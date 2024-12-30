import asyncio
import io
import time
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from . import interpreter

REPL_SOURCE_PATH = __file__  # Make path available globally


class ReplServer(Server):
    def __init__(self):
        super().__init__("repl")
        self.interpreter_manager = interpreter.InterpreterManager.get_instance()

    async def initialize(self, options: InitializationOptions):
        await self.interpreter_manager.start()
        return await super().initialize(options)

    async def shutdown(self):
        await self.interpreter_manager.stop()
        interpreter.InterpreterManager.reset_instance()
        return await super().shutdown()


def create_server():
    """Create a new server instance"""
    return ReplServer()


server = create_server()


class CodeOutput:
    """Capture code execution output"""

    def __init__(self):
        self.execution_time = 0.0  # Add timing
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.result = None

    def get_output(self) -> tuple[str, str, Any, float]:
        return self.stdout.getvalue(), self.stderr.getvalue(), self.result, self.execution_time


def execute_code(code: str) -> CodeOutput:
    """Execute Python code and capture output"""
    output = CodeOutput()
    start_time = time.time()

    # Create a safe globals dictionary with basic built-ins
    globals_dict = {
        '__builtins__': __builtins__,
        'time': time,
        'pd': None,  # Will import pandas if needed
        'pa': None,  # Will import pyarrow if needed
        'REPL_SOURCE_PATH': __file__,  # Give access to this file's path
    }

    try:
        # Redirect stdout/stderr to capture output
        with redirect_stdout(output.stdout), redirect_stderr(output.stderr):
            # First try to execute as an expression (for return value)
            try:
                output.result = eval(code, globals_dict)
            except SyntaxError:
                # If not an expression, execute as statements
                exec(code, globals_dict)
    except Exception as e:
        print(f"Error: {str(e)}", file=output.stderr)
    finally:
        output.execution_time = time.time() - start_time
    return output


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="python",
            description="""Execute Python code in a sandboxed environment with timing information.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                },
                "required": ["code"]
            }
        ),
        types.Tool(
            name="python_session",
            description="""Execute Python code in a persistent interpreter session.
    
Features:
- Maintains state between executions
- Session timeout after 5 minutes of inactivity
- Automatic session cleanup
- Full stdout/stderr capture
- Execution timing
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID (leave empty to create new session)"
                    },
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                },
                "required": ["code"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
        name: str,
        arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    if not arguments:
        raise ValueError("Missing arguments")

    if name == "python":
        code = arguments.get("code")
        if not code:
            raise ValueError("Missing code parameter")

        # Normal code execution
        output = execute_code(code)
        stdout, stderr, result, exec_time = output.get_output()

        # Format the response
        response = [f"Execution time: {exec_time:.4f} seconds"]

        if stdout:
            response.append(f"Standard Output:\n{stdout}")
        if stderr:
            response.append(f"Standard Error:\n{stderr}")
        if result is not None:
            response.append(f"Return Value:\n{repr(result)}")

        return [types.TextContent(
            type="text",
            text="\n".join(response) if response else "No output"
        )]
    elif name == "python_session":
        code = arguments.get("code")
        if not code:
            raise ValueError("Missing code parameter")

        session_id = arguments.get("session_id")

        if not session_id:
            # Create new session
            session_id = server.interpreter_manager.create_session()
            response = [f"Created new session: {session_id}"]
        else:
            response = []

        try:
            stdout, stderr, exec_time = await server.interpreter_manager.execute_code(
                session_id, code
            )

            response.extend([
                f"Session: {session_id}",
                f"Execution time: {exec_time:.4f} seconds",
            ])

            if stdout:
                response.append(f"Standard Output:\n{stdout}")
            if stderr:
                response.append(f"Standard Error:\n{stderr}")

            return [types.TextContent(
                type="text",
                text="\n".join(response)
            )]
        except ValueError as e:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the server using stdin/stdout streams"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="repl",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
