from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any
from app.services.crawler import CleanedWebsiteContent

@dataclass
class LLMResult:
    data: Dict[str, Any]
    provider: str
    model: str
    is_mock: bool
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: float

class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier string (e.g., 'gemini', 'openai', 'claude', 'mock')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier string."""
        pass

    @abstractmethod
    async def analyze(self, content: CleanedWebsiteContent) -> LLMResult:
        """Analyze cleaned website content and return structured JSON result."""
        pass
