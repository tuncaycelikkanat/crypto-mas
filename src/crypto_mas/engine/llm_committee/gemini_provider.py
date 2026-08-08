import json
import time
from typing import Any
import google.generativeai as genai
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from crypto_mas.engine.llm_committee.provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def complete_json(self, prompt: str, schema: type[BaseModel],
                             model: str = "gemini-1.5-flash", timeout_s: float = 8.0) -> tuple[BaseModel, dict[str, Any]]:
        start_time = time.time()
        
        generative_model = genai.GenerativeModel(
            model_name=model,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # We must use asyncio properly, google-generativeai supports async generate_content_async
        response = await generative_model.generate_content_async(prompt)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Parse JSON
        raw_json = response.text
        parsed_data = json.loads(raw_json)
        
        # Validate with Pydantic
        validated_data = schema(**parsed_data)
        
        # TODO: Add accurate token counting with tiktoken/Google API for cost estimation
        cost_usd = 0.0001
        
        metadata = {
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "model_version": model,
            "raw_response": raw_json
        }
        
        return validated_data, metadata
