import os
from typing import Dict, List

from mcp import StdioServerParameters

from core.mcp_client import StdioMCPClient
from core.mcp_server_config import StdioMCPServerConfiguration, StdioServerParametersWithDescription


class MCPManager:
    def __init__(self, config: StdioMCPServerConfiguration):
        self.config: Dict[str,
                          StdioServerParametersWithDescription] = config.get_available_servers()
        self.active_sessions: Dict[str, StdioMCPClient] = {}

    async def get_session(self, server_name: str):

        if server_name in self.active_sessions:
            return self.active_sessions[server_name]

        # Si no existe, la inicializamos dinámicamente (Lazy Start)
        if server_name not in self.config:
            raise Exception(f"Server {server_name} not found in config")

        print(f"🔌 Starting MCP Server: {server_name}...")
        server_cfg = self.config[server_name]

        # Aquí crearías la sesión y la guardarías
        session = StdioMCPClient(server_name=server_name, server_params=StdioServerParameters(
            command=server_cfg.command, args=server_cfg.args, env=server_cfg.env))
        await session.connect()
        self.active_sessions[server_name] = session
        return session

    async def cleanup(self, ):
        for _, client in self.active_sessions.items():
            if client:
                await client.cleanup()
