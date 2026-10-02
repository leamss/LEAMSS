import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'leamss')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    latest = await db['leads'].find().sort('created_at', -1).to_list(10)
    print(f"Total leads retrieved: {len(latest)}")
    for l in latest:
        print(f"ID: {l.get('lead_number')} | Name: {l.get('name')} | Source: {l.get('source')} | Atlas Code: {l.get('atlas_code')} | Date: {l.get('created_at')}")

if __name__ == '__main__':
    asyncio.run(check())
