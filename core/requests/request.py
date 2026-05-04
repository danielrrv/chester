from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Union
from google import genai
from core.clients.clients import LLMClient
from core.mcp.mcp_client import StdioMCPClient
from core.mcp.mcp_manager import MCPManager
from core.models.model import Model
from core.skill.skill import Skill

@dataclass
class ChesterRequest:
    user_response: Union[str,None]
    mcp_manager: MCPManager
    master_client: Model
    clients:Dict[Model, LLMClient]
    user_task:str = field(default="")
    system_prompt: str  = field(default="")
    provider: str = field(default='gemini')
    model: str = field(default='gemini-2.5-flash')
    parts: List[genai.types.Part] = field(default_factory=list),
    user_approval: bool = field(default=True)
    resources: List[str] = field(default_factory= list)
    turn:int = field(default=0)
    
    def set_system_instructions(self, value:str):
        self.system_prompt = value
        
    def set_user_task(self, value:str):
        self.user_task = value
    
@dataclass
class SessionRequest:
    user_task: str
  