import asyncio
from core.database import db, MONGO_URL, DB_NAME

async def main():
    print("Mongo URL:", MONGO_URL)
    print("Database:", DB_NAME)

    cols = await db.list_collection_names()

    print("Collection count:", len(cols))
    print(cols)

asyncio.run(main())