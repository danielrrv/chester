import os
import json
import uuid

from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Self, Any

from google.genai import types, chats # Keep types for now as they are used in History

from core.encoders.json_encoder import JsonEncoder
from core.mcp.mcp_server_config import StdioMCPServerConfiguration
from core.models.model import Model
from core.analytics.token_tracker import TokenTracker
from core.requests.request import SessionRequest
from core.responses.response import ChesterResponse
from core.skill.skill import Skill
from core.utils.utils import extract_uuid_from_filename
from ..clients.clients import LLMClient # Import the LLMClient abstraction
import logging 

class SessionNotFound(Exception):
    pass



@dataclass
class Session:
    is_new: bool = field(default=True)
    title: str = field(default_factory=str)
    id: str = field(default_factory=lambda: str(uuid.uuid4())) # Corrected default_factory usage
    is_persisted: bool = field(default=True)
    user_task: str = field(default="")
    history: List[types.ContentOrDict]=field(default_factory=list)
    skills: Dict[str, Skill] = field(default_factory=dict)
    learnings: dict = field(default_factory=dict)
    summary: str = field(default_factory=str) # Changed from dict to str
    pwd: str = field(default=os.getcwd())
    sessions_folders: str = field(default=".sessions")
    client: LLMClient  = None # Changed from `chat: chats.Chat` to a generic `llm_chat`
    system_instructions: str = field(default="")
    token_tracker: TokenTracker = field(default_factory=TokenTracker)
    created_at: str = field(default_factory=lambda: str(datetime.now())) # Corrected default_factory usage
    last_response: ChesterResponse = field(default_factory=lambda: ChesterResponse(is_complete=False))
    last_turn: int = field(default=0)

    
    
   
     
    @property
    def turn(self):
        return self.last_turn
    
    @turn.setter
    def turn(self, value):
        self.last_turn = value
    
    
    @classmethod
    def from_text(cls, json_text):
        try:
            data = json.loads(json_text)
            
            history = [types.Content(role=h['role'], parts=[types.Part(text=p['text']) for p in h['parts'] ]) for h in data.get('history', [])]
            last_response  = ChesterResponse.from_text(text = json.dumps(data.get('last_response', {})), metadata={})
            token_tracker = TokenTracker(**data.get('token_tracker', {}))
            skills ={ skill_name: Skill(**skill) for skill_name, skill in data.get('skills', {}).items()}
            
        
            return cls( 
                       id=data.get('id', ''),
                       is_new = data.get('is_new', False),
                       title = data.get('title', ''),
                       is_persisted = data.get('is_persisted', False),
                       user_task =  data.get('user_task', ''),
                       history = history,
                       skills = skills,
                       learnings = data.get('learnings', {}),
                       summary = data.get('summary', ''),
                       pwd = data.get('pwd', os.getcwd()),
                       sessions_folders =  data.get('sessions_folders',".sessions"),
                       last_response = last_response,
                       token_tracker = token_tracker
                       )
        except json.JSONDecodeError:
            raise
    @classmethod
    def find_or_create(cls, session_id: Optional[str] = None) -> Self: # Changed session_id to Optional[str]
        if session_id:
            try:
                session_path = Path(os.path.join(
                    cls.pwd, cls.sessions_folders, 'session_' + session_id + ".json"))
                if not session_path.exists():
                    raise SessionNotFound(f"Session with ID {session_id} not found.")
                with open(session_path, 'r') as fs:
                    content = fs.read()
                    return Session.from_text(content)                  
            except (json.JSONDecodeError, SessionNotFound) as e:
                import logging
                logging.warning(f"Could not load session {session_id}, creating new one. Error: {e}")
                
            except Exception:
                import logging
                logging.exception("An unexpected error occurred while finding/creating session.")
                raise
        else:
            sessions_path = Path(os.path.join(cls.pwd, cls.sessions_folders))
            sessions_path.mkdir(parents=True, exist_ok=True)
            new_session_id = str(uuid.uuid4())
            session = cls(id=new_session_id, last_response = ChesterResponse(is_complete=False), created_at = str(datetime.now()))
            session.persist()
            return session
        
        
    @staticmethod
    def list_sessions() -> List[dict]: # Changed return type to list[dict] as it returns raw dicts
        session_dir = Path(os.path.join(os.getcwd(), ".sessions")) # Use current working directory
        if not session_dir.exists():
            return []
        session_files = [f for f in session_dir.iterdir() if f.is_file() and f.name.startswith('session_') and f.name.endswith('.json')]
        sessions = []
        for f in session_files:
            try:
                with open(f, 'r') as session_file:
                    session_content = session_file.read()
                    session_data = json.loads(session_content)
                    sessions.append(session_data)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                import logging
                logging.error(f"Error loading session file {f.name}: {e}")
                continue
        return sessions
    
    def __repr__(self):
        return str(self.__dict__)
    
    def add_skill(self, skill: Skill):
        if not self.skills.get(skill.name):
            self.skills[skill.name] = skill
    
   
    def as_dict(self) -> dict:
        return asdict(self)

    def last_message_parts(self) -> List[types.Part]:
        # Ensure history is not empty and has expected structure
        if not self.history or not self.history[-1].parts:
            return types.Part(text="")
        return self.history[-1].parts
    
    def last_assistant_message(self):
        if not self.history or not self.history[-1].parts:
            return types.Part(text="")
        return list(filter(lambda x: x.role == 'model' , self.history))[-1].parts[0].text
        
        
    def append_message_to_last_user_interaction(self, parts:List[types.Part]):
        if self.history and self.history[-1] and len(parts) > 0 :
            for part in parts:
                if isinstance(part, types.Part):
                    self.history[-1].parts.append(part)
                elif isinstance(part, str):
                    self.history[-1].parts.append(types.Part(text=part))
                else:
                    raise ValueError(f"Unsupported part type: {type(part)}")
            self.persist()
    
    def persist(self) -> None:
        try:
            
            filename = 'session_' + self.id + ".json"
            
            session_path = Path(os.path.join(self.pwd, self.sessions_folders, filename))
            
            session_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            
            with open(session_path, 'w') as fs:
                fs.write(json.dumps(self, cls=JsonEncoder, indent=4))
        except Exception as e:
            # Log the exception for debugging
            logging.error(e)
            logging.error(f"Error persisting session {self.id}: {e}")
            raise
    
    
    async def set_client(self, client: LLMClient, system_instructions: str):
        """
        Initializes a new chat session using the provided LLM client.

        Args:
            llm_client (LLMClient): The instantiated LLM client for communication with the model.
            system_instructions (str): The system-level instructions for the chat.
            model (str): The name of the model to use for the chat.
        """
        self.system_instructions = system_instructions
        self.token_tracker.set_model(model=client.model) # Assuming token_tracker uses model name as string
        # For GeminiClient, start_chat will use the client's internal model.
        # The system_instructions can be part of the initial history if required by the LLM.
        # For now, we pass history and client handles system instruction via prompt
        await client.create(system_instructions=system_instructions, history=self.history) 
        self.client = client
        # NOTE: `system_instructions` and `model` are stored but their direct usage for chat configuration
        # is now handled by the `LLMClient`'s `start_chat` method, which encapsulates LLM-specific details.
    

    def update_history(self, role: str, message: str) -> None:
        self.history.append(types.Content(
            role=role, parts=[types.Part(text=message)]))
        self.persist()

    
