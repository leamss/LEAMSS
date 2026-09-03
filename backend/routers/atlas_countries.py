from fastapi import APIRouter
from core.database import db

router = APIRouter(prefix="/atlas", tags=["Atlas Countries"])


@router.get("/countries")
async def get_countries():
    countries = await db["atlas_countries"].find(
        {"enabled": True},
        {"_id": 0}
    ).sort("name", 1).to_list(None)

    return {
        "countries": countries
    }