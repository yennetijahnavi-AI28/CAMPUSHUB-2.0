import os
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAIUfqyW5ExFU5cDyrUmfGVuPU4MHjD1mQ"))

with open('model_test_2.log', 'w') as f:
    for m in ["gemini-2.0-flash-lite-001", "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-pro-latest", "gemini-2.5-flash-lite"]:
        try:
            resp = client.models.generate_content(model=m, contents="hi")
            f.write(f"SUCCESS: {m}\n")
        except Exception as e:
            f.write(f"FAILED: {m} -> {type(e).__name__} {str(e)}\n")
