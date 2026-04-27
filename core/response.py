from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional

from core.commands import AgentCommand, AgentCommandOutput
from core.token_tracker import UsageMetadata


class ChesterResponseException(Exception):
    pass
        
@dataclass
class AgentStep:
    step: int
    description: str
    status: str  # COMPLETED | IN_PROGRESS | PENDING


@dataclass
class AgentEnvironment:
    current_working_directory: str
    files_created: List[str] = field(default_factory=list)


@dataclass
class ChesterResponse:
    thought: str
    summary_of_achievement: str
    plan: List[AgentStep]
    environment: AgentEnvironment
    command: Optional[AgentCommand] = field(default_factory=AgentCommand)
    learnings: Dict[str, Any] = field(default_factory=dict)
    next_detected_skill_to_load: List[str] = field(default_factory=list)
    next_subtask: str = ""
    response_to_user: Optional[str] = None
    needs_user_information: bool = False
    needs_approval: bool = False
    is_complete: bool = False
    usage_metadata:UsageMetadata = field(default_factory=lambda: UsageMetadata(0, 0))
    _user_response: str = field(init=False, default="")
    _command_result_output: Optional[AgentCommandOutput] = field(init=False, default_factory=AgentCommandOutput)

    @classmethod
    def from_text(cls, text: str, metadata:Dict[str, Any]) -> Optional['ChesterResponse']:
        text = text.replace("```json", "").replace("```", "").strip()
        try:

            data = json.loads(text)

            plan = [AgentStep(**s) for s in data.get("plan", [])]
            env = AgentEnvironment(**data.get("environment", {}))
            cmd = AgentCommand.from_dict(data.get("command"))
    
            return cls(
                thought=data.get("thought", ""),
                summary_of_achievement=data.get("summary_of_achievement", ""),
                plan=plan,
                environment=env,
                command = cmd,
                learnings=data.get("learnings", {}),
                next_detected_skill_to_load=data.get(
                    "next_detected_skill_to_load", []),
                next_subtask=data.get("next_subtask", ""),
                response_to_user=data.get("response_to_user"),
                needs_user_information=str(
                    data.get("needs_user_information", "")).lower() == "true",
                needs_approval=str(data.get("needs_approval", "")
                                   ).lower() == "true",
                is_complete=str(data.get("is_complete", "")).lower() == "true",
                usage_metadata = metadata['usage_metadata']
            )
            
        except [json.JSONDecodeError, Exception]:
            raise ChesterResponseException(f"Unparseable entity: {text}")

    
    
    @property   
    def user_response(self):
        return self._user_response
    
    @property
    def command_result_output(self):
        return self._command_result_output
        
    @user_response.setter    
    def user_response(self, value: str):
        self._user_response = value
        
    @command_result_output.setter
    def command_result_output(self, value: AgentCommandOutput):
        self._command_result_output = value
