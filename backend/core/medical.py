import os
import json

try:
    from google import genai
    _genai_available = True
except ImportError:
    genai = None
    _genai_available = False


from genai_runner import run_with_key_pool

class MedicalAssistant:
    def __init__(self):
        self.model_name = 'gemini-2.0-flash' # upgraded model since flash-latest was deprecated
        if not _genai_available:
            print(" google.genai not installed. Medical AI offline.")

    def get_advice(self, query: str) -> str:
        print(f" Consulting Medical AI for: {query}")
        prompt = f"""
        You are a helpful AI health advisor named SIVI Medical.
        The user is reporting the following symptom or health query: '{query}'
        Provide brief, general advice. You can understand both Hindi and English.
        IMPORTANT: Always start with a clear disclaimer that you are not a doctor
        and they should consult a real physician for proper diagnosis.
        Keep the response under 3 sentences for voice output.
        Do not use markdown formatting.
        """

        try:
            def make_call(client):
                return client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            response = run_with_key_pool(make_call)
            
            if response is None:
                return "Failed to get medical advice due to quota limits."
                
            # Strip markdown and newlines for clean voice output
            text = response.text.replace("*", "").replace("#", "").replace("\n", " ")
            return " ".join(text.split())  # Collapse multiple spaces
        except Exception as e:
            return f"Failed to get medical advice: {e}"


medical_assistant = MedicalAssistant()
