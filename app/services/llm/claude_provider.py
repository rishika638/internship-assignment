import json
import re
import time
from typing import Dict, Any
from anthropic import AsyncAnthropic, AnthropicError

from app.services.llm.base import BaseLLMProvider, LLMResult
from app.services.llm.prompts import ANALYSIS_SYSTEM_PROMPT, build_user_prompt
from app.services.crawler import CleanedWebsiteContent
from app.utils.pricing import calculate_llm_cost
from app.utils.logger import logger

class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self._model_name = model_name
        self.client = AsyncAnthropic(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def analyze(self, content: CleanedWebsiteContent) -> LLMResult:
        start_time = time.perf_counter()
        user_prompt = build_user_prompt(
            url=content.final_url,
            title=content.title,
            meta_description=content.meta_description,
            meta_keywords=content.meta_keywords,
            headings=content.headings,
            body_text=content.body_text,
            schema_org=content.schema_org,
            open_graph=content.open_graph
        )

        try:
            message = await self.client.messages.create(
                model=self._model_name,
                max_tokens=4096,
                system=ANALYSIS_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            raw_text = message.content[0].text.strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n", "", raw_text)
                raw_text = re.sub(r"\n```$", "", raw_text).strip()

            parsed_data = json.loads(raw_text)

            input_tokens = message.usage.input_tokens if message.usage else len(user_prompt) // 4
            output_tokens = message.usage.output_tokens if message.usage else len(raw_text) // 4
            cost = calculate_llm_cost(self._model_name, input_tokens, output_tokens)

            return LLMResult(
                data=parsed_data,
                provider="claude",
                model=self._model_name,
                is_mock=False,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=cost,
                latency_ms=round(latency_ms, 2)
            )

        except json.JSONDecodeError as e:
            logger.error(f"Claude output failed JSON parsing: {e}")
            raise ValueError(f"Claude returned invalid JSON: {str(e)}")
        except AnthropicError as e:
            logger.error(f"Claude API error: {e}")
            raise RuntimeError(f"Claude API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in ClaudeProvider: {e}")
            raise RuntimeError(f"Claude processing error: {str(e)}")
