import json
from core.openrouter_llm import openrouter_llm

class CodingAgent:
    def __init__(self):
        self.model = "meta-llama/llama-3.3-70b-instruct:free"

    async def analyze_code(self, code: str, question: str) -> str:
        prompt = f"""You are an expert AI software engineer. Analyze the following code and answer the question.
Question: {question}
Code:
```
{code[:8000]}
```"""
        
        response = await openrouter_llm.complete(
            prompt=prompt,
            model=self.model,
            max_tokens=1000,
            temperature=0.2
        )
        return response.strip() if response else "Failed to analyze code."

coding_agent = CodingAgent()
