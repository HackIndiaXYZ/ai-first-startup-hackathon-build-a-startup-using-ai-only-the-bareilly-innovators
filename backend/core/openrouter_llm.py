import os
import json
import httpx
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
logger = logging.getLogger("sivi.openrouter_llm")

class OpenRouterLLM:
    """
    Client for OpenRouter API to utilize specialized agentic models.
    """

    def __init__(self, default_model: str = "meta-llama/llama-3.3-70b-instruct:free"):
        self.default_model = default_model
        self.api_key = os.getenv("OPENROUTER_API_KEY")

    async def complete(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = None,
        image_b64: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.5,
        response_format: dict = None
    ) -> str:
        if not self.api_key:
            logger.error("[OpenRouterLLM] OPENROUTER_API_KEY not found in environment.")
            return None

        actual_model = model or self.default_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        if image_b64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sivi.ai",
            "X-Title": "Sivi AI"
        }

        payload = {
            "model": actual_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=45.0
                )
                if response.status_code != 200:
                    logger.error(f"[OpenRouterLLM] Error {response.status_code}: {response.text}")
                    return None
                    
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                return None
            except Exception as e:
                logger.error(f"[OpenRouterLLM] Exception: {e}")
                return None

openrouter_llm = OpenRouterLLM()
