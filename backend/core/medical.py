import os
import json

try:
    from google import genai
    _genai_available = True
except ImportError:
    genai = None
    _genai_available = False


def _get_api_key():
    key = os.getenv("GEMINI_API_KEY")
    if key: return key
    try:
        settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sivi_settings.json")
        with open(settings_path, "r") as f:
            return json.load(f).get("api_key")
    except Exception:
        return None


class MedicalAssistant:
    def __init__(self):
        self.model_name = 'gemini-flash-latest'
        if not _genai_available:
            print(" google.genai not installed. Medical AI offline.")

    def _get_client(self):
        if not _genai_available: return None
        key = _get_api_key()
        return genai.Client(api_key=key) if key else None

    def get_advice(self, query: str) -> str:
        client = self._get_client()
        if not client:
            return "Medical AI offline. Missing Gemini API key or package."

        print(f" Consulting Medical AI for: {query}")
        prompt = f"""
        You are a helpful AI health advisor named TITAN Medical.
        The user is reporting the following symptom or health query: '{query}'
        Provide brief, general advice. You can understand both Hindi and English.
        IMPORTANT: Always start with a clear disclaimer that you are not a doctor
        and they should consult a real physician for proper diagnosis.
        Keep the response under 3 sentences for voice output.
        Do not use markdown formatting.
        """

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            # Strip markdown and newlines for clean voice output
            text = response.text.replace("*", "").replace("#", "").replace("\n", " ")
            return " ".join(text.split())  # Collapse multiple spaces
        except Exception as e:
            return f"Failed to get medical advice: {e}"


medical_assistant = MedicalAssistant()
