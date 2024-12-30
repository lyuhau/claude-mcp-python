import asyncio
import code
import io
import sys
import time
import uuid
from typing import Dict, Optional


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


class InterpreterManager:
    """Manages multiple interpreter sessions"""

    _instance: Optional['InterpreterManager'] = None  # Define _instance class variable

    @classmethod
    def get_instance(cls, timeout_seconds: int = 300) -> 'InterpreterManager':
        """Get or create the singleton instance"""
        if not cls._instance:
            cls._instance = cls(timeout_seconds)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance"""
        if cls._instance:
            asyncio.create_task(cls._instance.stop())
            cls._instance = None

    def __init__(self, timeout_seconds: int = 300):  # 5 minute default timeout
        self.interpreters: Dict[str, AsyncInterpreter] = {}
        self.timeout_seconds = timeout_seconds
        self.cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def start(self):
        """Start the cleanup task"""
        if not self._initialized:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._initialized = True

    async def stop(self):
        """Stop the cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self._initialized = False

    async def _cleanup_loop(self):
        """Periodically clean up inactive sessions"""
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
        """Create a new interpreter session"""
        session_id = str(uuid.uuid4())
        self.interpreters[session_id] = AsyncInterpreter(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[AsyncInterpreter]:
        """Get an existing interpreter session"""
        return self.interpreters.get(session_id)

    async def execute_code(self, session_id: str, code: str) -> tuple[str, str, float]:
        """Execute code in a specific session"""
        interpreter = self.get_session(session_id)
        if not interpreter:
            raise ValueError(f"No session found with id: {session_id}")
        return await interpreter.execute(code)
