import asyncio
import os
import sys

# Hack to fix paths for running arbitrary backend service scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.studysync_ai_service import generate_studysync_ai_response

async def test_cases():
    test_1 = await generate_studysync_ai_response("hi", [])
    print("TEST 1 (hi):", test_1[:100] + "...")
    
    test_2 = await generate_studysync_ai_response("what is binary tree", [])
    print("TEST 2 (binary search):", test_2[:200] + "...")

if __name__ == "__main__":
    asyncio.run(test_cases())
