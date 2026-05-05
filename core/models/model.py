"""models.py

This module defines data structures and enumerations related to pricing models
for various AI/ML services, specifically focusing on Gemini models.
"""
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

# To avoid circular imports, use TYPE_CHECKING for type hints of LLMClient
if TYPE_CHECKING:
    from core.clients.clients import LLMClient, GeminiClient, VertexAIClient


@dataclass
class ModelPrice:
    """Represents the pricing structure for a specific model.

    Attributes:
        input (float): The cost per unit for input tokens/data.
        output (float): The cost per unit for output tokens/data.
    """
    input: float # Corrected type hint to float for prices
    output: float # Corrected type hint to float for prices



# A dictionary mapping model names (strings) to their respective ModelPrice objects.
# These prices are typically in USD per 1M tokens or similar units.
PRICES: dict[str, ModelPrice] = {
    "gemini-2.5-flash-lite": ModelPrice(input=0.10, output=2.5),
    # Gemini 2.0 Flash model pricing
    "gemini-2.5-flash": ModelPrice(input=0.10, output=2.5), # Using ModelPrice dataclass for consistency
    # Gemini 1.5 Pro model pricing
    "gemini-2.5-pro": ModelPrice(input=1.25, output=5.00),
    "gemini-1.5-pro": ModelPrice(input=1.25, output=5.00),
    "gemini-1.5-flash-001": ModelPrice(input=0.10, output=2.5) # Vertex AI Gemini 1.5 Flash pricing (placeholder)
}


class Model(Enum):
    """Enumeration of available AI models.

    Each enum member represents a specific model with a unique identifier.
    """
    gemini_2_5_flash = "gemini-2.5-flash"
    gemini_2_5_flash_lite = "gemini-2.5-flash-lite"
    gemini_2_5_pro = "gemini-2.5-pro"
    gemini_1_5_pro = "gemini-1.5-pro"
    gemini_1_5_flash_vertex = "gemini-1.5-flash-001" # New Vertex AI model
    
    def __dict__(self):
        return {self.name: self.value}
    @classmethod
    def to_value(cls):
        match cls:
            case Model.gemini_2_5_flash: return "gemini-2.5-flash"
            case Model.gemini_2_5_flash_lite: return "gemini-2.5-flash-lite"
            case Model.gemini_2_5_pro: return "gemini-2.5-pro"
            case Model.gemini_1_5_pro: return "gemini-1.5-pro"
            case Model.gemini_1_5_flash_vertex: return "gemini-1.5-flash-001"
            
    def prices(self) -> ModelPrice | None:
        """Retrieves the pricing information for the current model.

        Returns:
            ModelPrice | None: The pricing data if available, otherwise None.
        """
        return PRICES.get(self.value)


def get_llm_client(model: Model) -> 'LLMClient':
    """Factory function to get the appropriate LLM client for a given model."""
    from core.clients.clients import GeminiClient, VertexAIClient # Import inside for factory function to avoid circular imports unless TYPE_CHECKING is used effectively
    match model:
        case Model.gemini_2_5_flash | Model.gemini_2_5_flash_lite | Model.gemini_2_5_pro | Model.gemini_1_5_pro:
            return GeminiClient(model=model)
        case Model.gemini_1_5_flash_vertex:
            return VertexAIClient(model=model)
        # Alternative implementation using direct string matching
        case _:
            raise ValueError(f"Unsupported model: {model.name}")
  
        
