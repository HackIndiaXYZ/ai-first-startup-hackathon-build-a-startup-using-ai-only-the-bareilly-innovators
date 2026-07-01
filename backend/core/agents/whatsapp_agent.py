import json
from core.openrouter_llm import openrouter_llm

class WhatsAppAgent:
    def __init__(self):
        self.model = "meta-llama/llama-3.3-70b-instruct:free"

    async def draft_smart_reply(self, contact: str, context: str = "") -> str:
        prompt = f"""You are Sivi, an AI assistant. The user wants to send a WhatsApp message to {contact}.
Context: {context}
Draft a short, natural, and helpful reply in Hindi/Hinglish or English depending on the context.
Do not add any quotes or extra text. Just the message."""
        
        response = await openrouter_llm.complete(
            prompt=prompt,
            model=self.model,
            max_tokens=200,
            temperature=0.7
        )
        return response.strip() if response else "Hello"

whatsapp_agent = WhatsAppAgent()
