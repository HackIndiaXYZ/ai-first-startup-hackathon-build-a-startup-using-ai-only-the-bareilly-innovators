import json
from core.text_llm import text_llm

class WebAgent:
    def __init__(self):
        pass

    async def summarize_page(self, url: str, content: str) -> str:
        prompt = f"""You are Sivi, a helpful AI assistant. Summarize the following webpage content concisely.
URL: {url}
Content: {content[:8000]}"""
        
        response = await text_llm.complete(
            prompt=prompt,
            temperature=0.3
        )
        return response.strip() if response else "Failed to summarize webpage."

web_agent = WebAgent()
