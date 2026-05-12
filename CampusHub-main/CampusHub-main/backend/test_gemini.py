import asyncio
import os
from google import genai
_gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAIUfqyW5ExFU5cDyrUmfGVuPU4MHjD1mQ"))

def call_model(model_name):
    try:
        response = _gemini_client.models.generate_content(
            model=model_name,
            contents="What is DSA? Keep it to 1 sentence."
        )
        print("Success", model_name, response.text)
    except Exception as e:
        print("FAILED", model_name, type(e).__name__, str(e))

call_model("gemini-1.5-flash")
call_model("gemini-pro")
