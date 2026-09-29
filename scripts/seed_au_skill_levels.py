"""Seed ANZSCO Skill Levels for Australian Occupations in occupation_master.

Based on Australian Bureau of Statistics (ABS) ANZSCO Skill Level Standards (Levels 1 to 5).
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


def get_anzsco_skill_level(code: str) -> int:
    code = str(code).strip()
    if not code:
        return 1

    major = code[0]
    submajor = code[:2] if len(code) >= 2 else code
    unit = code[:4] if len(code) >= 4 else code

    # Major 2: Professionals -> all Skill Level 1
    if major == '2':
        return 1

    # Major 1: Managers
    if major == '1':
        if submajor in ('11', '13'):
            if unit == '1331' and code.startswith('133112'):
                return 2
            return 1
        if submajor == '12':  # Farmers
            if unit in ('1211', '1212', '1214'):
                return 1
            if unit == '1213':
                if code.startswith(('121311', '121316')):
                    return 2
                return 1
            return 1
        if submajor == '14':  # Hospitality, Retail and Service Managers
            return 2
        return 1

    # Major 3: Technicians and Trades
    if major == '3':
        if submajor == '31':  # Engineering, ICT and Science Technicians
            return 2
        return 3  # 32, 33, 34, 35, 36, 39 are trade occupations (Skill Level 3)

    # Major 4: Community and Personal Service Workers
    if major == '4':
        if unit in ('4111', '4112', '4113', '4114', '4117', '4412', '4413'):
            return 2
        if unit in ('4115', '4116', '4511', '4512', '4521', '4522', '4523', '4524'):
            return 3
        return 4

    # Major 5: Clerical and Administrative Workers
    if major == '5':
        if unit in ('5111', '5112'):
            return 2
        if unit in ('5121', '5122'):
            return 3
        if submajor in ('52', '53', '54', '55', '56', '59'):
            return 4
        return 4

    # Major 6: Sales Workers
    if major == '6':
        if unit in ('6111', '6112'):
            return 3
        return 4

    # Major 7: Machinery Operators and Drivers
    if major == '7':
        return 4

    # Major 8: Labourers
    if major == '8':
        return 5

    return 1


async def main():
    client = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db = client["leamss"]

    updated = 0
    cursor = db["occupation_master"].find({"country_code": "AU"})
    async for doc in cursor:
        code = doc.get("code")
        lvl = get_anzsco_skill_level(code)
        await db["occupation_master"].update_one(
            {"_id": doc["_id"]},
            {"$set": {"skill_level": lvl}}
        )
        updated += 1

    print(f"Updated {updated} AU occupations with ANZSCO skill levels.")

    # Show breakdown
    pipeline = [
        {"$match": {"country_code": "AU", "status": "verified"}},
        {"$group": {"_id": "$skill_level", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    breakdown = await db["occupation_master"].aggregate(pipeline).to_list(100)
    print("New AU Skill Level Breakdown:", breakdown)


if __name__ == "__main__":
    asyncio.run(main())
