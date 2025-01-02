from typing import Dict, Type

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from repl.tools import PythonTool, PythonSessionTool, ShellTool, PerlTool
from repl.tools.base import BaseTool
from repl.tools.shell_status_tool import ShellStatusTool


class ReplServer(Server):
    def __init__(self):
        super().__init__("repl")
        # Initialize all tools
        self.tools: Dict[str, BaseTool] = {}

        # Create shell tool first since status tool needs reference to it
        self.shell_tool = ShellTool()
        self.tools[self.shell_tool.name] = self.shell_tool
        self.tools["shell_status"] = ShellStatusTool(self.shell_tool)

        # Add other tools
        for tool_class in self._get_tool_classes():
            if tool_class != ShellTool:  # Skip ShellTool since we already created it
                tool = tool_class()
                self.tools[tool.name] = tool

    @staticmethod
    def _get_tool_classes() -> list[Type[BaseTool]]:
        """Get all available tool classes"""
        return [
            PythonTool,
            PythonSessionTool,
            ShellTool,
            PerlTool,
        ]

    async def initialize(self, options: InitializationOptions):
        """Initialize the server and all tools"""
        # Initialize any tools that need it
        for tool in self.tools.values():
            if hasattr(tool, 'initialize'):
                await tool.initialize()
        return await super().initialize(options)

    async def shutdown(self):
        """Shutdown the server and all tools"""
        # Shutdown any tools that need it
        for tool in self.tools.values():
            if hasattr(tool, 'shutdown'):
                await tool.shutdown()
        return await super().shutdown()


server = ReplServer()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [tool.get_tool_definition() for tool in server.tools.values()]


@server.call_tool()
async def handle_call_tool(
        name: str,
        arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    if not arguments:
        raise ValueError("Missing arguments")

    tool = server.tools.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    return await tool.execute(arguments)


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