import json
from core.text_llm import text_llm

class CodingAgent:
    def __init__(self):
        pass

    async def analyze_code(self, code: str, question: str) -> str:
        prompt = f"""You are an expert AI software engineer. Analyze the following code and answer the question.
Question: {question}
Code:
```
{code[:8000]}
```"""
        
        response = await text_llm.complete(
            prompt=prompt,
            temperature=0.2
        )
        return response.strip() if response else "Failed to analyze code."

coding_agent = CodingAgent()
