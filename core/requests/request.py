from dataclasses import dataclass, field
from typing import List, Mapping
from google import genai
from core.mcp.mcp_client import StdioMCPClient
from core.mcp.mcp_manager import MCPManager
from core.skill.skill import Skill

@dataclass
class ChesterRequest:
    system_prompt: str
    skills: Mapping[str, Skill] 
    mcp_manager: MCPManager
    provider: str = field(default='gemini')
    model: str = field(default='gemini-2.5-flash')
    parts: List[genai.types.Part] = field(default_factory=list)