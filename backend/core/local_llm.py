"""
TITAN AI  Local LLM Module (Ollama)
Provides offline AI responses as a fallback to Gemini.
Requires: Ollama installed + pip install ollama
"""

import os

try:
    import ollama as ollama_sdk
    _ollama_available = True
except ImportError:
    _ollama_available = False


class LocalLLM:
    def __init__(self):
        self.model = os.getenv("LOCAL_MODEL", "llama3.2:3b")
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.mode = os.getenv("AI_MODE", "auto")  # cloud, local, auto
        self.system_prompt = (
            "You are Sivi, an advanced AI assistant. "
            "Be concise, helpful, and speak like a professional British butler. "
            "Keep answers under 3 sentences for voice output."
        )

    def is_available(self) -> bool:
        if not _ollama_available:
            return False
        try:
            ollama_sdk.list()
            return True
        except Exception:
            return False

    def chat(self, query: str) -> str:
        if not _ollama_available:
            return "Ollama not installed. Run: pip install ollama"

        try:
            response = ollama_sdk.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query},
                ],
            )
            return response["message"]["content"].strip()
        except Exception as e:
            return f"Local AI error: {e}"

    def switch_mode(self, command: str) -> str:
        if "local" in command:
            self.mode = "local"
            return "Switched to Local AI (Ollama). Internet not required."
        elif "cloud" in command:
            self.mode = "cloud"
            return "Switched to Cloud AI (Gemini)."
        else:
            self.mode = "auto"
            return "AI mode set to auto (Cloud first, Local fallback)."


local_llm = LocalLLM()
