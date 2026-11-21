import json
import re
import time
import asyncio
import random
import warnings
from typing import Dict, Any, Optional

warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from google.api_core.exceptions import (
    GoogleAPIError,
    ServiceUnavailable,
    ResourceExhausted,
    InternalServerError,
    TooManyRequests
)

from app.services.llm.base import BaseLLMProvider, LLMResult
from app.services.llm.prompts import ANALYSIS_SYSTEM_PROMPT, build_user_prompt
from app.services.crawler import CleanedWebsiteContent
from app.utils.pricing import calculate_llm_cost
from app.utils.logger import logger

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", max_retries: int = 3, base_delay: float = 1.0):
        self.api_key = api_key
        self._model_name = model_name
        self.max_retries = max_retries
        self.base_delay = base_delay
        genai.configure(api_key=self.api_key)
        self.client_model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=ANALYSIS_SYSTEM_PROMPT,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.2,
            }
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

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

        response = None
        for attempt in range(self.max_retries + 1):
            try:
                # Generate content asynchronously
                response = await self.client_model.generate_content_async(user_prompt)
                break
            except (ServiceUnavailable, ResourceExhausted, InternalServerError, TooManyRequests) as transient_err:
                if attempt == self.max_retries:
                    logger.error(f"Gemini API transient failure ({type(transient_err).__name__}) after {self.max_retries} retries: {transient_err}")
                    raise RuntimeError(f"Gemini API error after retries: {str(transient_err)}")
                jitter = random.uniform(0.1, 0.5)
                delay = (self.base_delay * (2 ** attempt)) + jitter
                logger.warning(
                    f"Gemini API {type(transient_err).__name__} encountered. Retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries})..."
                )
                await asyncio.sleep(delay)
            except GoogleAPIError as api_err:
                logger.error(f"Gemini non-retryable API error: {api_err}")
                raise RuntimeError(f"Gemini API error: {str(api_err)}")
            except Exception as e:
                logger.error(f"Unexpected error in GeminiProvider: {e}")
                raise RuntimeError(f"Gemini processing error: {str(e)}")

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        raw_text = response.text.strip()
        # Clean possible markdown wrapping if returned
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\n", "", raw_text)
            raw_text = re.sub(r"\n```$", "", raw_text).strip()

        try:
            parsed_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Gemini output could not be parsed as JSON: {e}")
            raise ValueError(f"Gemini returned invalid JSON: {str(e)}")

        # Extract usage metadata
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        if input_tokens == 0:
            input_tokens = len(user_prompt) // 4
        if output_tokens == 0:
            output_tokens = len(raw_text) // 4

        cost = calculate_llm_cost(self._model_name, input_tokens, output_tokens)

        return LLMResult(
            data=parsed_data,
            provider="gemini",
            model=self._model_name,
            is_mock=False,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=cost,
            latency_ms=round(latency_ms, 2)
        )
