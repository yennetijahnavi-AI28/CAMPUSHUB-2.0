import os
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAIUfqyW5ExFU5cDyrUmfGVuPU4MHjD1mQ"))
with open('model_list.log', 'w') as f:
    for m in client.models.list():
        f.write(f"{m.name}\n")
