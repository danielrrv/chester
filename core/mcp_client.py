
import os
import json
from typing import Any, Coroutine, Dict, List, Optional, Self, Union
from dataclasses import dataclass, field
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, stdio_client, types

from core.json_encoder import JsonEncoder


@dataclass
class MCPToolCall:
    server_name: str  # ej: "github"
    tool_name: str    # ej: "create_issue"
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    name: str
    description: Union[str, None]
    parameters: Dict[str, Any] = field(default_factory=dict)


class StdioMCPClient:
    """Client for interacting with an MCP server process via stdio, using the mcp library."""

    def __init__(self, server_name: str, server_params: StdioServerParameters):
        self._server_name: str = server_name
        self._server_params: StdioServerParameters = server_params
        self._session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()
        self._stdio_client_context = None  # To hold the async context manager
        self._tools: List[types.Tool] = []

    async def connect(self):
        try:
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(self._server_params))
            self.read, self.write = stdio_transport
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(self.read, self.write))
            await self._session.initialize()
            self._tools = await self.list_tools()
        except Exception:
            raise

    async def list_tools(self) -> List[MCPTool]:
        try:
            if self._tools:
                return self._tools
            if not self._session:
                raise RuntimeError(
                    "MCP Session not initialized. Use 'async with StdioMCPClient(...)'")
                
            _, __,(___,self._tools) = await self._session.list_tools()
            # Assuming `response.tools` is a list of objects with `name`, `description`, `parameters`.
            return [MCPTool(t.name, t.description, t.inputSchema) for t in self._tools]
        except Exception:
            raise

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Union[types.CallToolResult, List[types.Tool]]:
        try:

            if not self._session:
                raise RuntimeError(
                    "MCP Session not initialized. Use 'async with StdioMCPClient(...)'")
            if name not in list(map(lambda x: x.name, self._tools)):
                return self._tools
            result = await self._session.call_tool(name, arguments=arguments)
            return result
        except Exception:
            await self.cleanup()
            raise

    async def cleanup(self):
        await self._exit_stack.aclose()
        
        

    @staticmethod
    def sanitize_mcp_content(raw_content: str) -> str:
        """
        Cleans raw GitHub MCP output:
        1. Decodes escaped characters (\\n, \\t, \\").
        2. Converts tabs to 4 spaces (Standardizes code).
        3. Trims excessive trailing whitespace.
        """
        if not raw_content:
            return ""

        try:
            # Step 1: If the content is wrapped in a JSON string, unwrap it
            # This handles the literal "\\n" -> "\n" conversion
            decoded = raw_content.encode().decode('unicode_escape')

            # Step 2: Clean up tabs (tabs in LLM context are token-heavy and messy)
            decoded = decoded.replace('\\t', '    ').replace('\t', '    ')

            # Step 3: Remove potential double-slash artifacts from JSON-in-JSON
            decoded = decoded.replace('\\\\', '\\')

            return decoded.strip()
        except Exception as e:
            # Fallback: simple string replacement if unicode_escape fails
            return raw_content.replace('\\n', '\n').replace('\\t', '    ')
