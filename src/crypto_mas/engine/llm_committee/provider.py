from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class AgentVote(BaseModel):
    vote: str          # "LONG" | "SHORT" | "PASS"
    confidence: int    # 0-100
    reasoning: str

class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(self, prompt: str, schema: type[BaseModel],
                             model: str, timeout_s: float = 8.0) -> tuple[BaseModel, dict[str, Any]]:
        """
        Executes a prompt and returns structured JSON validated by Pydantic.
        Returns: (parsed_response, metadata={"latency_ms": int, "cost_usd": float, "model_version": str})
        """
        pass
