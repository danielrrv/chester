import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import chats, Client as GeminiClientGenAI # Rename to avoid conflict
from google.genai.types import GenerationConfig as GeminiGenerationConfig, Tool as GeminiTool, ContentOrDict, Part

from google.cloud import aiplatform # New import for Vertex AI
from vertexai.preview.generative_models import GenerativeModel, ChatSession, GenerationConfig, Tool # New imports for Vertex AI models

from core.models.model import Model
from core.responses.response import ChesterResponse
from core.analytics.token_tracker import UsageMetadata

# NOTE: For OpenAI, you would typically import from `openai` library
# from openai import OpenAI


class LLMClient(ABC):
    """Abstract base class for Language Model (LLM) clients."""

    _model: Model

    @property
    def model(self) -> Model:
        return self._model

    @abstractmethod
    def create(self, system_instructions: str, history: List[ContentOrDict]):
        pass

    @abstractmethod
    def send_message(self, messages) -> ChesterResponse:
        """Sends a message to an existing LLM chat session and returns its response."""
        pass

    @abstractmethod
    def generate_content(self, contents: Any, generation_config: Optional[Any] = None, tools: Optional[List[Any]] = None) -> Any:
        """Generates content based on the provided inputs (e.g., for skill creation)."""
        pass


class GeminiClient(LLMClient):
    """Concrete implementation of LLMClient for Google Gemini (using google.genai)."""

    def __init__(self, model: Model = Model.gemini_2_5_flash):
        self._client = GeminiClientGenAI(api_key=os.getenv('GEMINI_API_KEY'))
        self._model = model
        self._chat: chats.Chat = None

    @property
    def model(self) -> Model:
        return self._model

    def create(self, system_instructions: str, history: List[ContentOrDict]) -> None:
        self._chat = self._client.chats.create(
            model=self._model.value,
            config={"system_instruction": system_instructions,
                    "response_mime_type": "application/json"},
            history=history)

    def send_message(self, messages: List[Part]) -> ChesterResponse:
        # For Gemini, the chat_session object handles sending messages.
        # The `message` here is expected to be `content` for `send_message`
        raw_response = self._chat.send_message(messages)
        return ChesterResponse.from_text(raw_response.text, {"usage_metadata": UsageMetadata(total_input=int(raw_response.usage_metadata.prompt_token_count), total_output=int(raw_response.usage_metadata.candidates_token_count))})

    def generate_content(self, contents: Any, generation_config: Optional[GeminiGenerationConfig] = None, tools: Optional[List[GeminiTool]] = None) -> Any:
    
        return self._client.models.generate_content(
            model=self._model.value,
            contents=contents,
            config=generation_config)
        


class VertexAIClient(LLMClient):
    """Concrete implementation of LLMClient for Google Vertex AI (using google.cloud.aiplatform)."""

    def __init__(self, model: Model = Model.gemini_1_5_flash_vertex, project: Optional[str] = None, location: Optional[str] = None):
        if project is None:
            project = os.getenv('GCP_PROJECT_ID')
        if location is None:
            location = os.getenv('GCP_LOCATION')

        if not project or not location:
            raise ValueError("GCP_PROJECT_ID and GCP_LOCATION must be set as environment variables or provided.")

        aiplatform.init(project=project, location=location)
        self._model = model
        self._generative_model = GenerativeModel(self._model.value)
        self._chat_session: Optional[ChatSession] = None

    @property
    def model(self) -> Model:
        return self._model

    def create(self, system_instructions: str, history: List[ContentOrDict]) -> None:
        # Vertex AI GenerativeModel's start_chat doesn't directly take system_instructions in the same way.
        # System instructions are typically passed to the model initialization or as part of the first message.
        # For this implementation, we'll initialize the chat session and consider history as the context.
        # If a true 'system instruction' field is needed, it might require a custom model or a different approach.
        self._chat_session = self._generative_model.start_chat(history=history)

    def send_message(self, messages: List[Part]) -> ChesterResponse:
        if not self._chat_session:
            raise ValueError("Chat session not initialized. Call 'create' first.")
        
        raw_response = self._chat_session.send_message(messages)
        # Vertex AI GenerativeModel response doesn't directly expose token counts in usage_metadata like google.genai
        # This part might need adaptation or specific API calls to retrieve token counts if required.
        # For now, we'll return a placeholder or estimate if actual counts are not directly available.
        prompt_tokens = 0 # Placeholder
        candidates_tokens = 0 # Placeholder
        
        # Attempt to extract text from the response parts
        response_text_parts = [part.text for part in raw_response.candidates[0].content.parts if part.text]
        response_text = " ".join(response_text_parts)

        return ChesterResponse.from_text(response_text, {"usage_metadata": UsageMetadata(prompt_tokens, candidates_tokens)})

    def generate_content(self, contents: Any, generation_config: Optional[GenerationConfig] = None, tools: Optional[List[Tool]] = None) -> Any:
        return self._generative_model.generate_content(
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
    def model(self) -> Model:
        # Implement actual model property for OpenAIClient if it's meant to be a full client
        raise NotImplementedError("OpenAIClient model property not fully implemented.")

    def create(self, system_instructions: str, history: List[ContentOrDict]) -> None:
        raise NotImplementedError(
            f"OpenAI create not yet implemented for model {self.model_name}.")

    def send_message(self, messages: List[Part]) -> ChesterResponse:
        raise NotImplementedError(
            f"OpenAI send_message not yet implemented for model {self.model_name}.")

    def generate_content(self, contents: Any, generation_config: Optional[Any] = None, tools: Optional[List[Any]] = None) -> Any:
        raise NotImplementedError(
            f"OpenAI generate_content not yet implemented for model {self.model_name}.")

# NOTE: Add other LLM client implementations here as needed.



# NOTE: The global 'client' and 'model' declarations have been removed.
# LLM client instances are now created and passed dynamically.
# How many repositories do I have in github 
def get_client(provider: str, model: Model) -> LLMClient:
    """
    Dynamically selects and instantiates the appropriate LLM client.

    Args:
        provider (str): The name of the LLM provider (e.g., 'gemini', 'openai').
        model (Model): The specific model name to use (e.g., 'gemini-2.5-flash', 'gpt-4').

    Returns:
        LLMClient: An instance of the selected LLM client.

    Raises:
        ValueError: If an unsupported LLM provider is requested.
    """
    if provider.lower() == 'gemini':
        return GeminiClient(model = model)
    # TODO: Add more LLM providers here (e.g., elif provider.lower() == 'openai': return OpenAIClient(model_name=model))
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
