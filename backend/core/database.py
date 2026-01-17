"""
Database configuration and connection management for LEAMSS Portal
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Database connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
fs = AsyncIOMotorGridFSBucket(db)

async def shutdown_db():
    """Close database connection on shutdown"""
    client.close()
