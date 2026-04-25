"""models.py

This module defines data structures and enumerations related to pricing models
for various AI/ML services, specifically focusing on Gemini models.
"""
from dataclasses import dataclass
from enum import Enum


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
    # Gemini 2.0 Flash model pricing
    "gemini-2.5-flash": ModelPrice(input=0.10, output=0.40), # Using ModelPrice dataclass for consistency
    # Gemini 1.5 Pro model pricing
    "gemini-2.5-pro": ModelPrice(input=1.25, output=5.00)
}


class Model(Enum):
    """Enumeration of available AI models.

    Each enum member represents a specific model with a unique identifier.
    """
    gemini_2_5_flash = "gemini-2.5-flash"

    def prices(self) -> ModelPrice | None:
        """Retrieves the pricing information for the current model.

        Returns:
            ModelPrice | None: The pricing data if available, otherwise None.
        """
        return PRICES.get(self.value)

