
from core.database import db
from fastapi import APIRouter, HTTPException, Body
router = APIRouter(
    prefix="/atlas/admin",
    tags=["Atlas Country Admin"]
)



@router.get("/countries")
async def get_all_countries():
    countries = await db["atlas_countries"].find(
        {},
        {"_id": 0}
    ).sort("name", 1).to_list(None)

    return countries
@router.get("/countries/{code}")
async def get_country(code: str):

    country = await db["atlas_countries"].find_one(
        {"code": code.upper()},
        {"_id": 0}
    )

    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    return country

@router.put("/countries/{code}")
async def update_country(code: str, payload: dict = Body(...)):

    code = code.upper()

    result = await db["atlas_countries"].update_one(
        {"code": code},
        {
            "$set": payload
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Country not found"
        )

    country = await db["atlas_countries"].find_one(
        {"code": code},
        {"_id": 0}
    )

    return {
        "message": "Country updated successfully",
        "country": country
    }