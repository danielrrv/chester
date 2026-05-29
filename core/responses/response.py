
import os
import json

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.commands.commands import AgentCommand, AgentCommandOutput
from core.analytics.token_tracker import UsageMetadata


class ChesterResponseException(Exception):
    pass
        
@dataclass
class AgentStep:
    step: int
    description: str
    status: str  # COMPLETED | IN_PROGRESS | PENDING


@dataclass
class AgentEnvironment:
    current_working_directory: str = field(default_factory=lambda:os.getcwd())
    files_created: List[str] = field(default_factory=list)


@dataclass
class SubAgent:
    agent_role: str
    role_description: str
    task: str
    context: str
    required_skills: List[str]
  
@dataclass
class ChesterResponse:
    thought: str = field(default="")
    summary_of_achievement: str = field(default="")
    intent: str = field(default="")
    plan: List[AgentStep] = field(default_factory=list)
    environment: AgentEnvironment = field(default_factory=AgentEnvironment)
    command: Optional[AgentCommand] = field(default_factory=AgentCommand)
    learnings: Dict[str, Any] = field(default_factory=dict)
    next_detected_skill_to_load: List[str] = field(default_factory=list)
    next_subtask: str = ""
    response_to_user: Optional[str] = None
    needs_user_information: bool = False
    needs_approval: bool = False
    is_complete: bool = False
    usage_metadata:UsageMetadata = field(default_factory=lambda: UsageMetadata(0, 0))
    sub_agents: List[SubAgent] = field(default_factory=list) 
    _user_response: str = field(init=False, default="")
    _command_result_output: Optional[AgentCommandOutput] = field(init=False, default_factory=AgentCommandOutput)


    @property   
    def user_response(self):
        return self._user_response
    
    @user_response.setter    
    def user_response(self, value: str):
        self._user_response = value
        
    @property
    def command_result_output(self):
        return self._command_result_output
        
    @command_result_output.setter
    def command_result_output(self, value: AgentCommandOutput):
        self._command_result_output = value
            
           

        
    @classmethod
    def from_text(cls, text: str, metadata:Dict[str, Any]) -> Optional['ChesterResponse']:
        text = text.replace("```json", "").replace("```", "").strip()
        try:

            data = json.loads(text)
            print(data)
            plan = [AgentStep(**s) for s in data.get("plan", [])]
            env = AgentEnvironment(**data.get("environment", {}))
            cmd = AgentCommand.from_dict(data.get("command"))
            sub_agents = [SubAgent(**sa) for sa in data.get("sub_agents", [])]
            usage_metadata = {}
            if hasattr(data,'usage_metadata'):
                usage_metadata = data.get('usage_metadata')
            elif hasattr(metadata, 'usage_metadata'):
                usage_metadata = metadata.get('usage_metadata')
                
            return cls(
                thought=data.get("thought", ""),
                summary_of_achievement=data.get("summary_of_achievement", ""),
                intent=data.get("intent", ""),
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
                usage_metadata = usage_metadata,
                sub_agents=sub_agents
            )
            
        except json.JSONDecodeError:
            raise ChesterResponseException(f"Unparseable entity: {text}")
        except Exception:
            raise

    

class UserResponse:
    def __init__(self, user_message:str, command_output: Optional[AgentCommandOutput], learnings:Optional[Dict[str, str]] = None, plan:Optional[Dict[Any, Any]] = None):
        self.user_message = user_message
        self.command_output = command_output
        self.learnings= learnings
        self.plan = plan
    def __repr__(self):
        text = ""
        if self.command_output:
            text= f"""Continue with the task:{self.user_message}
                    Here are the command's output:
                        {json.dumps({"stdout":self.command_output.stdout, "stderr": self.command_output.stderr}, indent=3)}"            
            """
        
  
        else:        
            text = f"""Continue with the task:{self.user_message}"""
            
            
        if self.learnings:
            text+=f"""\n\n
                    Here's the learnings
                    {json.dumps(self.learnings)}
            """
        return text