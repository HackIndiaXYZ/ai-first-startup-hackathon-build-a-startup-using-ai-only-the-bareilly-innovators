import os

try:
    from google import genai
    _genai_available = True
except ImportError:
    genai = None
    _genai_available = False


class MedicalAssistant:
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        if key and _genai_available:
            self.client = genai.Client(api_key=key)
            self.model_name = 'gemini-2.5-flash'
        else:
            self.client = None
            self.model_name = None
            if not _genai_available:
                print(" google.genai not installed. Medical AI offline.")

    def get_advice(self, query: str) -> str:
        if not self.client:
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
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            # Strip markdown and newlines for clean voice output
            text = response.text.replace("*", "").replace("#", "").replace("\n", " ")
            return " ".join(text.split())  # Collapse multiple spaces
        except Exception as e:
            return f"Failed to get medical advice: {e}"


medical_assistant = MedicalAssistant()
