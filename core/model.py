from dataclasses import dataclass
from enum import Enum


@dataclass
class ModelPrice:
    input: int
    output: int


PRICES: dict[str, ModelPrice] = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00}
}


class Model(Enum):
    gemini_2_5_flash = "gemini-2.5-flash"
    def prices(self) -> ModelPrice|None:
        return PRICES.get(self.value)
