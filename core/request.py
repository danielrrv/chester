


from dataclasses import dataclass, field
from typing import List, Mapping

from google import genai

from core.skill import Skill


@dataclass
class ChesterRequest:
    system_prompt: str
    skills: Mapping[str, Skill]
    parts: List[genai.types.Part] = field(default_factory=list)
    