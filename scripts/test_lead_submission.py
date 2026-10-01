import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient

async def test_lead():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "leamss")
    db = AsyncIOMotorClient(mongo_url)[db_name]
    
    # Check leads in DB
    count = await db["leads"].count_documents({"source": "public_atlas"})
    print(f"Current public_atlas leads in DB: {count}")

if __name__ == "__main__":
    asyncio.run(test_lead())
