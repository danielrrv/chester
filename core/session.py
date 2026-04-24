


import os
import json
import uuid

from datetime import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Self
from google.genai import chats, types, Client


class SessionNotFound(Exception):
    pass


class HistoryEnconder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, History):
            return [obj.as_list()]
        if isinstance(obj, Session):
            return [{"id": (obj.id), "title": (obj.title), "user_task": (obj.user_task), "history": (obj.history), "summary": (obj.summary), "skill_names": (obj.skill_names), "created_at": (obj.created_at)}]
        if isinstance(obj, types.Content):
            return [{"role": obj.role, "parts": obj.parts}]
        if isinstance(obj, types.Part):
            return [{"text": obj.text}]
        else:
            return super().default(obj)


class History:

    history: list[types.ContentOrDict] = []

    def append(self, interaction: types.ContentOrDict):
        self.history.append(interaction)

    def as_list(self) -> types.ContentOrDict:
        return self.history

    def __iter__(self):
        return self.history

    def __getitem__(self, key):
        return self.history[key]


@dataclass()
class Session:
    is_new: bool = field(default=True)
    title: str = field(default_factory=str)
    id: int = field(default=str(uuid.uuid4()))
    is_persisted: bool = field(default=True)
    user_task: str = field(default="")
    history: History = field(default_factory=History)
    learnings: dict = field(default_factory=dict)
    summary: str = field(default_factory=dict)
    pwd: str = field(default=os.getcwd())
    sessions_folders: str = field(default=".sessions")
    chat: chats.Chat = field
    skill_names: list[str] = field(default_factory=list)
    system_instructions: str = field(default="")
    created_at: str = field(default_factory=str)

    def as_dict(self) -> dict:
        return asdict(self)

    def last_message(self) ->str:
        # part = types.Part(text="Hello")
        # print(part.model_dump())
        print("Last message:" + self.history[-1].parts[0].model_dump()['text'])
        return self.history[-1].parts[0].model_dump()['text']
    def persist(self) -> None:
        try:
            filename = 'session_' + self.id + ".json"
            with open(os.path.join(Session.pwd, Session.sessions_folders, filename), 'w') as fs:
                fs.write(json.dumps(self, cls=HistoryEnconder, indent=4))
        except Exception:
            raise

    def create_chat(self, client: Client, system_instructions, model="gemini-2.5-flash"):
        self.system_instructions = system_instructions
        self.chat = client.chats.create(
            model=model,
            config={"system_instruction": system_instructions,
                    "response_mime_type": "application/json"},
            history=self.history.as_list()
        )

    @staticmethod
    def list_sessions():
        session_dir = Path(os.path.join(Session.pwd, Session.sessions_folders))
        session_files = [f for f in session_dir.iterdir() if f.is_file()]

        sessions = []
        for f in session_files:
            with open(f.as_uri(), 'r') as session_file:
                session_content = session_file.read()
                session = json.loads(session_content)
                sessions.append(session)
        return [Session(**s) for s in sessions]

    def update_history(self, role: str, message: str) -> None:
        self.history.append(types.Content(
            role=role, parts=[types.Part(text=message)]))
        self.persist()

    @staticmethod
    def find_or_create(is_new: bool, session_id: int) -> Self:
        if is_new:
            os.makedirs(os.path.join(
                Session.pwd, Session.sessions_folders), exist_ok=True)
            id = str(uuid.uuid4())
            filename = 'session_' + id + ".json"
            with open(os.path.join(Session.pwd, Session.sessions_folders, filename), 'w') as fs:
                session = Session(id=id, created_at=str(datetime.now()))
                session.persist()
                return session

        if session_id:
            try:
                session_path = Path(os.path.join(
                    Session.pwd, Session.sessions_folders, 'session_' + session_id + ".json"))
                if not session_path.exists():
                    raise SessionNotFound
                with open(session_path.as_uri(), 'r') as fs:
                    content = fs.read()
                    session = json.loads(content)
                    return session
            except [json.JSONDecodeError, SessionNotFound]:
                return Session.find_or_create(is_new=True)
            except Exception:
                raise
