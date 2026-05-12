import asyncio
import os
import sys

# Hack to fix paths for running arbitrary backend service scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.ai_service import get_study_ai_response, generate_ai_response

async def test_cases():
    test_1 = await get_study_ai_response("hi", [])
    print("TEST 1 (hi):", test_1)
    
    test_2 = await get_study_ai_response("what is binary search", [])
    print("TEST 2 (binary search):", test_2)
    
    test_3 = await get_study_ai_response("explain DSA", [])
    print("TEST 3 (DSA):", test_3)

if __name__ == "__main__":
    asyncio.run(test_cases())
