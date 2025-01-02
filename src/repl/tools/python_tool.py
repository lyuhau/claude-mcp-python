import sys
import time
import ast
import asyncio
import mcp.types as types
import os
import tempfile
from typing import List

from repl.tools.base import BaseTool


class PythonTool(BaseTool):
    """Tool for executing Python code in a sandboxed environment"""

    @property
    def name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return """Execute Python code in a sandboxed environment with timing information.

The 'python' tool is ideal for:
- Quick, one-off Python code execution
- Simple calculations or data transformations
- Code that doesn't need to maintain state
- Testing small code snippets
- Using specific Python installations or environments
- Cases where you want guaranteed clean environment for each run

Key features:
- Fresh environment for each execution
- Safe sandboxed environment 
- Support for custom Python installations
- Timing information for performance analysis
- Clean separation between runs
"""

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "python_path": {
                    "type": "string",
                    "description": "Optional path to Python executable (defaults to server interpreter)"
                }
            },
            "required": ["code"]
        }

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        code = arguments.get("code")
        if not code:
            raise ValueError("Missing code parameter")

        python_path = arguments.get("python_path", sys.executable)
        start_time = time.time()

        # Analyze the code to determine if the last statement is an expression
        try:
            parsed = ast.parse(code)
            if parsed.body and isinstance(parsed.body[-1], ast.Expr):
                # Split into statements and final expression
                *statements, last_expr = parsed.body
                if statements:
                    exec_code = ast.unparse(ast.Module(body=statements, type_ignores=[]))
                    eval_code = ast.unparse(last_expr.value)
                else:
                    exec_code = ""
                    eval_code = ast.unparse(last_expr.value)
            else:
                exec_code = code
                eval_code = None
        except Exception:
            # If parsing fails, treat entire code as exec
            exec_code = code
            eval_code = None

        # Create a wrapper script that captures output and handles errors
        wrapper_code = """
import sys
import traceback
from io import StringIO
import time

# Redirect stdout/stderr
stdout = StringIO()
stderr = StringIO()
original_stdout = sys.stdout
original_stderr = sys.stderr
sys.stdout = stdout
sys.stderr = stderr

result = None
try:
    # Execute any statements first
    if __EXEC_CODE__:
        exec(__EXEC_CODE__)
    
    # Then evaluate final expression if present
    if __EVAL_CODE__:
        result = eval(__EVAL_CODE__)
        print(f"__RESULT__:{repr(result)}")
        
except Exception:
    traceback.print_exc()

# Restore stdout/stderr and get output
sys.stdout = original_stdout
sys.stderr = original_stderr

# Print captured output with markers
print("__STDOUT__")
print(stdout.getvalue())
print("__STDERR__")
print(stderr.getvalue())
"""

        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            # Replace the placeholders with actual code
            wrapped_code = wrapper_code.replace("__EXEC_CODE__", repr(exec_code))
            wrapped_code = wrapped_code.replace("__EVAL_CODE__", repr(eval_code))
            f.write(wrapped_code)
            temp_file = f.name

        try:
            # Execute the code in a separate process
            process = await asyncio.create_subprocess_exec(
                python_path,
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            exec_time = time.time() - start_time

            # Process output and extract sections
            output = stdout.decode('utf-8') if stdout else ""
            error_output = stderr.decode('utf-8') if stderr else ""

            # Parse the output sections
            result = None
            stdout_content = ""
            stderr_content = ""

            current_section = None
            for line in output.split('\n'):
                if line == "__STDOUT__":
                    current_section = "stdout"
                    continue
                elif line == "__STDERR__":
                    current_section = "stderr"
                    continue
                elif line.startswith("__RESULT__:"):
                    result = line[len("__RESULT__:"):]
                    continue
                
                if current_section == "stdout":
                    stdout_content += line + '\n'
                elif current_section == "stderr":
                    stderr_content += line + '\n'

            # Add any direct stderr output
            if error_output:
                stderr_content += error_output

            # Format response
            response = []

            if python_path != sys.executable:
                response.append(f"Using Python: {python_path}")

            response.append(f"Execution time: {exec_time:.4f} seconds")

            if stdout_content.strip():
                response.append(f"Standard Output:\n{stdout_content.rstrip()}")
            if stderr_content.strip():
                response.append(f"Standard Error:\n{stderr_content.rstrip()}")
            if result:
                response.append(f"Result: {result}")

            return [types.TextContent(
                type="text",
                text="\n".join(response)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error executing Python code: {str(e)}"
            )]

        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file)
            except Exception:
                pass
