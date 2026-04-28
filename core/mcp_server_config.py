
import json

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp import StdioServerParameters

class StdioServerParametersWithDescription(StdioServerParameters):
    description: str

class StdioMCPServerConfiguration:
    def __init__(self,config_json:str):
       self._config_json_path: Path = Path(config_json)
   
    @staticmethod
    def get_descriptions(servers:Dict[str, Optional[StdioServerParametersWithDescription]]):
        return [{"server_name":server_name, "description":params.description } for server_name, params in servers.items()]
    
    def get_available_servers(self)-> Dict[str, Optional[StdioServerParametersWithDescription]]:
        servers: Dict[str, StdioServerParameters] = {}
        with open(self._config_json_path.absolute(), 'r') as fs:
            content = fs.read()
            servers_configuration: Dict[str, Any] = json.loads(content)
            mcp_servers: Dict[str, Any] = servers_configuration.get('mcpServers', {})
            for server_name, params in mcp_servers.items():
                servers[server_name] = StdioServerParametersWithDescription(command=params['command'], description=params['description'], args=params['args'] or [], env=params['env'] or {} )
        return servers
