import json
from core.openrouter_llm import openrouter_llm

class WebAgent:
    def __init__(self):
        self.model = "meta-llama/llama-3.3-70b-instruct:free"

    async def summarize_page(self, url: str, content: str) -> str:
        prompt = f"""You are Sivi, a helpful AI assistant. Summarize the following webpage content concisely.
URL: {url}
Content: {content[:8000]}"""
        
        response = await openrouter_llm.complete(
            prompt=prompt,
            model=self.model,
            max_tokens=500,
            temperature=0.3
        )
        return response.strip() if response else "Failed to summarize webpage."

web_agent = WebAgent()
