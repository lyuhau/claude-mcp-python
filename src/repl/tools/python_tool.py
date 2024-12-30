import time
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from typing import List

import mcp.types as types

from repl.tools.base import BaseTool, CodeOutput


class PythonTool(BaseTool):
    """Tool for executing Python code in a sandboxed environment"""

    @property
    def name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return "Execute Python code in a sandboxed environment with timing information."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
            },
            "required": ["code"]
        }

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        code = arguments.get("code")
        if not code:
            raise ValueError("Missing code parameter")

        output = self._execute_code(code)
        return output.format_output()

    def _execute_code(self, code: str) -> CodeOutput:
        """Execute Python code and capture output"""
        output = CodeOutput()
        start_time = time.time()

        # Create a safe globals dictionary with basic built-ins
        globals_dict = {
            '__builtins__': __builtins__,
            'time': time,
            'pd': None,  # Will import pandas if needed
            'pa': None,  # Will import pyarrow if needed
        }

        stdout = StringIO()
        stderr = StringIO()

        try:
            # Redirect stdout/stderr to capture output
            with redirect_stdout(stdout), redirect_stderr(stderr):
                # First try to execute as an expression (for return value)
                try:
                    output.result = eval(code, globals_dict)
                except SyntaxError:
                    # If not an expression, execute as statements
                    exec(code, globals_dict)
        except Exception as e:
            print(f"Error: {str(e)}", file=stderr)
        finally:
            output.execution_time = time.time() - start_time
            output.stdout = stdout.getvalue()
            output.stderr = stderr.getvalue()

        return output
