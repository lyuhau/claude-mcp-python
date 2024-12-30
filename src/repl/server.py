import time
import asyncio
import io
import mcp.server.stdio
import mcp.types as types
import os
import sys
from contextlib import redirect_stdout, redirect_stderr
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from typing import Any

REPL_SOURCE_PATH = __file__  # Make path available globally

server = Server("repl")


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
            description="""Execute Python code in a sandboxed environment with timing information.

Special commands:
!hot-swap <new_code>  - Updates the REPL's implementation with new code.
                      - The new code must be the complete Python source.
                      - Use with REPL_SOURCE_PATH to read/modify current implementation.
                      - Example:
                        with open(REPL_SOURCE_PATH, 'r') as f:
                            current = f.read()
                        new_code = current.replace('old', 'new')
                        !hot-swap new_code
                      - Warning: Changes modify source directly, consider git commit before major changes.
                      - Note: Some changes may require server restart (e.g. function signatures).""",
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
        )
    ]


def reload_module():
    """Reload the current module to apply code changes"""
    module = sys.modules[__name__]
    try:
        with open(__file__, 'r') as f:
            new_source = f.read()
        # Create a new module
        import types as pytypes
        new_module = pytypes.ModuleType(__name__)
        # Execute the new source in the new module's namespace
        exec(new_source, new_module.__dict__)
        # Update all items in the current module
        for key in list(module.__dict__.keys()):
            if not key.startswith('__'):
                module.__dict__[key] = new_module.__dict__.get(key)
        print("Successfully reloaded module!")
    except Exception as e:
        print(f"Error reloading module: {e}")


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

        # Check for special hot-swap command
        if code.startswith("!hot-swap"):
            new_code = code[len("!hot-swap"):].strip()
            if new_code:
                # Write new code to file
                try:
                    with open(__file__, 'w') as f:
                        f.write(new_code)
                    # Reload the module
                    reload_module()
                    return [types.TextContent(
                        type="text",
                        text="Successfully hot-swapped REPL implementation!"
                    )]
                except Exception as e:
                    return [types.TextContent(
                        type="text",
                        text=f"Error during hot-swap: {str(e)}"
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text="Error: No new code provided for hot-swap"
                )]

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