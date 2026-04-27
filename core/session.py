import os
import json
import uuid

from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Self, Any

from google.genai import types, chats # Keep types for now as they are used in History

from core.model import Model
from core.token_tracker import TokenTracker
from .clients import LLMClient # Import the LLMClient abstraction


class SessionNotFound(Exception):
    pass


class HistoryEnconder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, History):
            return obj.as_list()
        if isinstance(obj, Session):
            return {
                "id": (obj.id),
                "system_instructions": obj.system_instructions,
                "title": (obj.title),
                "user_task": (obj.user_task),
                "history": (obj.history),
                "summary": (obj.summary),
                "skill_names": (obj.skill_names),
                "token_tracker": obj.token_tracker,
                "created_at": (obj.created_at),
                "learnings": (obj.learnings)
            }
        if isinstance(obj, types.Content):
            return {"role": obj.role, "parts": obj.parts}
        if isinstance(obj, types.Part):
            return {"text": obj.text}
        if isinstance(obj, TokenTracker):
            return [{"total_candidates": obj.total_candidates, "total_prompt": obj.total_prompt}]
        else:
            return super().default(obj)


class History:
    _history: list[types.ContentOrDict] = []

    def append(self, interaction: types.ContentOrDict):
        self._history.append(interaction)

    def as_list(self) -> List[types.ContentOrDict]:
        return self._history

    def __iter__(self):
        return iter(self._history)

    def __getitem__(self, key) -> types.ContentOrDict:
        return self._history[key]


@dataclass()
class Session:
    is_new: bool = field(default=True)
    title: str = field(default_factory=str)
    id: str = field(default_factory=lambda: str(uuid.uuid4())) # Corrected default_factory usage
    is_persisted: bool = field(default=True)
    user_task: str = field(default="")
    history: History = field(default_factory=History)
    learnings: dict = field(default_factory=dict)
    summary: str = field(default_factory=str) # Changed from dict to str
    pwd: str = field(default=os.getcwd())
    sessions_folders: str = field(default=".sessions")
    client: LLMClient  = field(init=False) # Changed from `chat: chats.Chat` to a generic `llm_chat`
    skill_names: list[str] = field(default_factory=list)
    system_instructions: str = field(default="")
    token_tracker: TokenTracker = field(default_factory=TokenTracker)
    created_at: str = field(default_factory=lambda: str(datetime.now())) # Corrected default_factory usage

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
        return list(filter(lambda x: x.role == 'model' , self.history.as_list()))[-1].parts[0].text
        
        
    def append_message_to_last_user_interaction(self, parts:List[types.Part]):
        if self.history and self.history[-1] and len(parts) > 0 :
            self.history[-1].parts.append(*parts)
            self.persist()
    
    def persist(self) -> None:
        try:
            filename = 'session_' + self.id + ".json"
            session_path = Path(os.path.join(self.pwd, self.sessions_folders, filename))
            session_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            with open(session_path, 'w') as fs:
                fs.write(json.dumps(self, cls=HistoryEnconder, indent=4))
        except Exception as e:
            # Log the exception for debugging
            import logging
            logging.error(f"Error persisting session {self.id}: {e}")
            raise

    def set_client(self, client: LLMClient, system_instructions: str):
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
        client.create(system_instructions=system_instructions, history=self.history.as_list()) 
        self.client = client
        # NOTE: `system_instructions` and `model` are stored but their direct usage for chat configuration
        # is now handled by the `LLMClient`'s `start_chat` method, which encapsulates LLM-specific details.

    @staticmethod
    def list_sessions() -> list[dict]: # Changed return type to list[dict] as it returns raw dicts
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

    def update_history(self, role: str, message: str) -> None:
        self.history.append(types.Content(
            role=role, parts=[types.Part(text=message)]))
        
        self.persist()

    @classmethod
    def find_or_create(cls, is_new: bool, session_id: Optional[str] = None) -> Self: # Changed session_id to Optional[str]
        if is_new:
            sessions_path = Path(os.path.join(cls.pwd, cls.sessions_folders))
            sessions_path.mkdir(parents=True, exist_ok=True)
            new_session_id = str(uuid.uuid4())
            session = cls(id=new_session_id, created_at=str(datetime.now()))
            session.persist()
            return session

        if session_id:
            try:
                session_path = Path(os.path.join(
                    cls.pwd, cls.sessions_folders, 'session_' + session_id + ".json"))
                if not session_path.exists():
                    raise SessionNotFound(f"Session with ID {session_id} not found.")
                with open(session_path, 'r') as fs:
                    content = fs.read()
                    session_data = json.loads(content)[0] # Assuming JSONEncoder returns list of one item
                    # Reconstruct history and token_tracker objects from raw data
                    session_data['history'] = History()
                    session_data['history'].history = session_data['history'][0] # Adjust for how HistoryEncoder saves
                    session_data['token_tracker'] = TokenTracker(**session_data['token_tracker'][0])
                    return cls(**session_data)
            except (json.JSONDecodeError, SessionNotFound) as e:
                import logging
                logging.warning(f"Could not load session {session_id}, creating new one. Error: {e}")
                return Session.find_or_create(is_new=True)
            except Exception:
                import logging
                logging.exception("An unexpected error occurred while finding/creating session.")
                raise
        else:
            # If not new and no session_id is provided, create a new one.
            return Session.find_or_create(is_new=True)
