from abc import ABC, abstractmethod
from typing import List

import mcp.types as types


class BaseTool(ABC):
    """Base class for all REPL tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass

    @property
    @abstractmethod
    def schema(self) -> dict:
        """JSON schema for tool arguments"""
        pass

    def get_tool_definition(self) -> types.Tool:
        """Get the MCP tool definition"""
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.schema
        )

    @abstractmethod
    async def execute(self, arguments: dict) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Execute the tool with given arguments"""
        pass


class CodeOutput:
    """Capture code execution output"""

    def __init__(self):
        self.execution_time = 0.0
        self.stdout = ""
        self.stderr = ""
        self.result = None

    def format_output(self) -> List[types.TextContent]:
        """Format the output as MCP text content"""
        response = [f"Execution time: {self.execution_time:.4f} seconds"]

        if self.stdout:
            response.append(f"Standard Output:\n{self.stdout}")
        if self.stderr:
            response.append(f"Standard Error:\n{self.stderr}")
        if self.result is not None:
            response.append(f"Return Value:\n{repr(self.result)}")

        return [types.TextContent(
            type="text",
            text="\n".join(response) if response else "No output"
        )]
