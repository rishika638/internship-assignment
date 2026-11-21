from typing import Optional
from app.config import get_settings
from app.services.llm.base import BaseLLMProvider, LLMResult
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider
from app.services.llm.claude_provider import ClaudeProvider
from app.services.crawler import CleanedWebsiteContent
from app.utils.logger import logger

class LLMProviderFactory:
    def __init__(self):
        self.settings = get_settings()

    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """Create provider instance based on name or environment settings."""
        target_provider = (provider_name or self.settings.PRIMARY_LLM_PROVIDER).lower()

        if self.settings.MOCK_MODE or target_provider == "mock":
            logger.info("Initializing MockLLMProvider (Mock mode active).")
            return MockLLMProvider()

        if target_provider == "gemini":
            if self.settings.GEMINI_API_KEY:
                return GeminiProvider(
                    api_key=self.settings.GEMINI_API_KEY,
                    model_name=self.settings.GEMINI_MODEL
                )
            logger.warning("GEMINI_API_KEY is not set. Falling back to MockLLMProvider.")
            return MockLLMProvider()

        if target_provider == "openai":
            if self.settings.OPENAI_API_KEY:
                return OpenAIProvider(
                    api_key=self.settings.OPENAI_API_KEY,
                    model_name=self.settings.OPENAI_MODEL
                )
            logger.warning("OPENAI_API_KEY is not set. Falling back to MockLLMProvider.")
            return MockLLMProvider()

        if target_provider == "claude":
            if self.settings.ANTHROPIC_API_KEY:
                return ClaudeProvider(
                    api_key=self.settings.ANTHROPIC_API_KEY,
                    model_name=self.settings.ANTHROPIC_MODEL
                )
            logger.warning("ANTHROPIC_API_KEY is not set. Falling back to MockLLMProvider.")
            return MockLLMProvider()

        # Unknown provider fallback
        logger.warning(f"Unknown provider '{target_provider}'. Falling back to MockLLMProvider.")
        return MockLLMProvider()

    async def execute_analysis(self, content: CleanedWebsiteContent) -> LLMResult:
        """
        Execute analysis with primary provider and fallback mechanisms.
        Ensures clear error tracking and never masks errors as silent successes.
        """
        primary_provider = self.get_provider()
        logger.info(f"Executing website analysis with provider: {primary_provider.provider_name} [{primary_provider.model_name}]")

        try:
            return await primary_provider.analyze(content)
        except Exception as primary_error:
            logger.error(f"Primary provider '{primary_provider.provider_name}' failed: {primary_error}")

            # Determine fallback provider
            fallback_name = self.settings.FALLBACK_LLM_PROVIDER.lower()
            if primary_provider.provider_name != fallback_name:
                logger.warning(f"Attempting graceful fallback to '{fallback_name}' provider...")
                try:
                    fallback_provider = self.get_provider(fallback_name)
                    result = await fallback_provider.analyze(content)
                    
                    # Annotate fallback notice in ai_generated_suggestions for auditability
                    notice = (
                        f"[SYSTEM FALLBACK NOTICE] Primary provider '{primary_provider.provider_name}' failed: "
                        f"{str(primary_error)}. Successfully recovered using fallback '{fallback_provider.provider_name}'."
                    )
                    result.data.setdefault("competitor_analysis", {}).setdefault("ai_generated_suggestions", []).append(notice)
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback provider '{fallback_name}' also failed: {fallback_error}")
                    raise RuntimeError(f"Both primary ('{primary_provider.provider_name}') and fallback ('{fallback_name}') failed. Error: {primary_error}")

            raise primary_error

llm_factory = LLMProviderFactory()
