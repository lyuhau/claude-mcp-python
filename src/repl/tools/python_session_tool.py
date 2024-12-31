import asyncio
import code
import io
import sys
import time
import uuid
from typing import Dict, List, Optional

import mcp.types as types

from repl.tools.base import BaseTool


class AsyncInterpreter:
    """Async wrapper around code.InteractiveInterpreter"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.interpreter = code.InteractiveInterpreter()
        self.locals = self.interpreter.locals
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.last_used = time.time()

    async def execute(self, code_str: str) -> tuple[str, str, float]:
        """Execute code and return (stdout, stderr, execution_time)"""
        self.last_used = time.time()
        start_time = time.time()

        # Redirect stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = self.stdout
        sys.stderr = self.stderr

        try:
            # Try to compile the code first
            try:
                compiled_code = compile(code_str, "<input>", "exec")
                if compiled_code is None:
                    self.stderr.write("Incomplete input\n")
                else:
                    exec(compiled_code, self.locals)
            except Exception as e:
                self.stderr.write(f"Error: {str(e)}\n")
                # Try running as separate statements
                for statement in code_str.split('\n'):
                    statement = statement.strip()
                    if statement and not statement.startswith('#'):
                        try:
                            self.interpreter.runsource(statement, "<input>", "single")
                        except Exception as e:
                            self.stderr.write(f"Error in statement '{statement}': {str(e)}\n")
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        exec_time = time.time() - start_time
        stdout = self.stdout.getvalue()
        stderr = self.stderr.getvalue()

        # Clear buffers for next execution
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

        return stdout, stderr, exec_time


class SessionManager:
    """Manages interpreter sessions with timeout cleanup"""

    _instance: Optional['SessionManager'] = None

    @classmethod
    def get_instance(cls, timeout_seconds: int = 300) -> 'SessionManager':
        if not cls._instance:
            cls._instance = cls(timeout_seconds)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        if cls._instance:
            asyncio.create_task(cls._instance.stop())
            cls._instance = None

    def __init__(self, timeout_seconds: int = 300):
        self.interpreters: Dict[str, AsyncInterpreter] = {}
        self.timeout_seconds = timeout_seconds
        self.cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def start(self):
        if not self._initialized:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._initialized = True

    async def stop(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self._initialized = False

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(60)  # Check every minute
            current_time = time.time()
            to_remove = []

            for session_id, interpreter in self.interpreters.items():
                if current_time - interpreter.last_used > self.timeout_seconds:
                    to_remove.append(session_id)

            for session_id in to_remove:
                del self.interpreters[session_id]

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.interpreters[session_id] = AsyncInterpreter(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[AsyncInterpreter]:
        return self.interpreters.get(session_id)


class PythonSessionTool(BaseTool):
    """Tool for executing Python code in persistent sessions"""

    def __init__(self):
        self.session_manager = SessionManager.get_instance()

    @property
    def name(self) -> str:
        return "python_session"

    @property
    def description(self) -> str:
        return """Execute Python code in a persistent interpreter session.
    
The 'python_session' tool is best for:
- Interactive data analysis sessions where state needs to be maintained
- Multi-step calculations where results need to be reused
- Building up complex objects or data structures incrementally
- Debugging sessions where you want to inspect intermediate states
- Scenarios where importing libraries once and reusing them is desired
- Cases where you need to maintain variables between executions

Key features:
- Maintains state between executions
- Session persists for 5 minutes of inactivity
- Full access to Python interpreter features
- Ability to build context over multiple executions
- More flexible execution environment
"""

    @property
    def schema(self) -> dict:
        return {
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

    async def initialize(self):
        """Initialize the session manager"""
        await self.session_manager.start()

    async def shutdown(self):
        """Shutdown the session manager"""
        await self.session_manager.stop()
        SessionManager.reset_instance()

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        code = arguments.get("code")
        if not code:
            raise ValueError("Missing code parameter")

        session_id = arguments.get("session_id")
        response = []

        if not session_id:
            # Create new session
            session_id = self.session_manager.create_session()
            response.append(f"Created new session: {session_id}")

        try:
            stdout, stderr, exec_time = await self.session_manager.execute_code(
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
