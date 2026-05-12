import asyncio
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAIUfqyW5ExFU5cDyrUmfGVuPU4MHjD1mQ"))

async def test():
    primary_model_name = "gemini-1.5-flash-latest"
    primary_model = genai.GenerativeModel(primary_model_name)
    try:
        response = await asyncio.to_thread(primary_model.generate_content, "what is binary search")
        with open("debug_ai.log", "w") as f:
            f.write("Success: " + response.text)
    except Exception as e:
        with open("debug_ai.log", "w") as f:
            f.write("Error: " + type(e).__name__ + " " + str(e))

if __name__ == "__main__":
    asyncio.run(test())
