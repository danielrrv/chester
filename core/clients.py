import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import chats, Client
from google.genai.types import GenerationConfig, Tool, ContentOrDict, Part

from core.model import Model
from core.response import ChesterResponse
from core.token_tracker import UsageMetadata

# NOTE: For OpenAI, you would typically import from `openai` library
# from openai import OpenAI


class LLMClient(ABC):
    """Abstract base class for Language Model (LLM) clients."""

    _model: Model

    @property
    def model(self) -> Model:
        return self._model

    @abstractmethod
    def create(self, system_instructions: str, history: List[genai.types.ContentOrDict]):
        pass

    @abstractmethod
    def send_message(self, messages) -> ChesterResponse:
        """Sends a message to an existing LLM chat session and returns its response."""
        pass

    @abstractmethod
    def generate_content(self, contents: Any, generation_config: Optional[GenerationConfig] = None, tools: Optional[List[Tool]] = None) -> Any:
        """Generates content based on the provided inputs (e.g., for skill creation)."""
        pass


class GeminiClient(LLMClient):
    """Concrete implementation of LLMClient for Google Gemini."""

    def __init__(self, model: Model = Model.gemini_2_5_flash):
        self._client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        self._model = model
        self._chat: chats.Chat = None

    @property
    def model(self) -> Model:
        return self._model

    def create(self, system_instructions: str, history: List[genai.types.ContentOrDict]) -> None:
        self._chat = self._client.chats.create(
            model=self._model.value,
            config={"system_instruction": system_instructions,
                    "response_mime_type": "application/json"},
            history=history)

    def send_message(self, messages: List[Part]) -> ChesterResponse:
        # For Gemini, the chat_session object handles sending messages.
        # The `message` here is expected to be `content` for `send_message`
        raw_response = self._chat.send_message(messages)
        return ChesterResponse.from_text(raw_response.text, {"usage_metadata": UsageMetadata(int(raw_response.usage_metadata.prompt_token_count), int(raw_response.usage_metadata.candidates_token_count))})

    def generate_content(self, contents: Any, generation_config: Optional[GenerationConfig] = None, tools: Optional[List[Tool]] = None) -> Any:
        return self._model.generate_content(
            contents=contents,
            generation_config=generation_config,
            tools=tools
        )


class OpenAIClient(LLMClient):
    """Dummy implementation of LLMClient for OpenAI to demonstrate multi-model support."""

    def __init__(self, model_name: str = "gpt-4"):
        # self._client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) # Uncomment when implementing fully
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def send_message(self, chat_session: Any, message: List[Part], tools: Optional[List[Any]] = None) -> Any:
        raise NotImplementedError(
            f"OpenAI send_message not yet implemented for model {self.model_name}.")

    def generate_content(self, contents: Any, generation_config: Optional[Any] = None, tools: Optional[List[Any]] = None) -> Any:
        raise NotImplementedError(
            f"OpenAI generate_content not yet implemented for model {self.model_name}.")

# NOTE: Add other LLM client implementations here as needed.
