import os
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAIUfqyW5ExFU5cDyrUmfGVuPU4MHjD1mQ"))

with open('model_test.log', 'w') as f:
    for m in ["gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro"]:
        try:
            resp = client.models.generate_content(model=m, contents="hi")
            f.write(f"SUCCESS: {m}\n")
        except Exception as e:
            f.write(f"FAILED: {m} -> {type(e).__name__} {str(e)}\n")
