"""Module for tracking token usage and calculating costs for language model interactions.

This module provides the `TokenTracker` class, which helps monitor prompt and candidate
token counts and estimates the associated costs based on the model used.
"""
from dataclasses import dataclass, field
from typing import Optional
from google.genai import types
from core.models.model import Model


@dataclass 
class UsageMetadata:
    total_input: int = 0
    total_output:int  = 0

@dataclass
class TokenTracker:
    """Tracks token usage for language model interactions and calculates associated costs.

    Attributes:
        total_prompt (int): The cumulative count of tokens used in prompts.
        total_candidates (int): The cumulative count of tokens generated in candidates/responses.
        model (Model): The language model currently being tracked, used for cost calculation.
                       Defaults to Model.gemini_2_5_flash.
    """
    total_prompt: int = 0
    total_candidates: int = 0
    model: Model = field(default=Model.gemini_2_5_flash)

    def update(self, metadata: UsageMetadata):
        """Updates the token counts based on the provided usage metadata.

        Args:
            metadata (Optional[types.GenerateContentResponseUsageMetadata]): 
                Usage metadata containing prompt and candidate token counts from a
                language model generation response.
        """
        if metadata:
            self.total_prompt += metadata.total_input
            self.total_candidates += metadata.total_output

    def report(self):
        """Prints a summary report of the session's token usage and estimated costs.

        The report includes total prompt tokens, total candidate tokens, and their
        respective and combined estimated costs.
        """
        input_cost, output_cost, total_cost = self.calculate()
        print(f'--- Session Usage ---')
        print(f'Input: {self.total_prompt}, ${input_cost:.6f} | Output: {self.total_candidates}, ${output_cost:.6f}')
        print(f'Total: {self.total_prompt + self.total_candidates}, ${total_cost:.6f}')

    def set_model(self, model: Model) -> None:
        """Sets the language model for token tracking and cost calculation.

        Args:
            model (Model): The new language model to be used.
        """
        self.model = model

    def calculate(self):
        """Calculates the estimated input, output, and total costs based on token usage.

        Returns:
            tuple[float, float, float]: A tuple containing the input cost, output cost,
                                      and total cost, respectively.
        """
        input_cost = self.total_prompt / 1000000 * self.model.prices().input
        output_cost = self.total_candidates / 1000000 * self.model.prices().output
        return (input_cost, output_cost, input_cost + output_cost)

    def to_dict(self) -> dict:
        """Converts the TokenTracker instance to a dictionary for serialization."""
        return {'total_prompt': self.total_prompt, 'total_candidates': self.total_candidates, 'model': self.model.value}

    @classmethod
    def from_dict(cls, data: dict):
        """Reconstructs a TokenTracker instance from a dictionary."""
        return cls(total_prompt=data['total_prompt'], total_candidates=data['total_candidates'], model=Model(data['model']))