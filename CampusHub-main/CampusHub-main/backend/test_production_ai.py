import asyncio
import os
from services.ai_service import get_study_ai_response

async def test_cases():
    with open('ai_test_out.log', 'w') as f:
        test_1 = await get_study_ai_response("hi", [])
        f.write(f"TEST 1 (hi): {test_1}\n\n")
        
        test_2 = await get_study_ai_response("what is binary search", [])
        f.write(f"TEST 2 (binary search): {test_2}\n\n")
        
        test_3 = await get_study_ai_response("explain DSA", [])
        f.write(f"TEST 3 (DSA): {test_3}\n\n")

if __name__ == "__main__":
    asyncio.run(test_cases())
