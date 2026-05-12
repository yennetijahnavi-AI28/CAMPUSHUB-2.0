import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def test_db():
    url = os.getenv("MONGODB_URL")
    print(f"Testing connection to: {url}")
    client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
    try:
        print("Pinging...")
        await client.admin.command('ping')
        print("✅ MongoDB connection SUCCESSFUL")
    except Exception as e:
        print(f"❌ MongoDB connection FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
