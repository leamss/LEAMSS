from datetime import datetime

DEFAULT_COUNTRIES = [
    {
        "code": "AU",
        "name": "Australia",
        "flag": "🇦🇺",
        "classification": "ANZSCO",
        "primary_code_length": 6,
        "benchmark": "https://www.anzscosearch.com/search/",
        "enabled": True,

        "modules": {
            "occupation": True,
            "state_nomination": True,
            "skill_assessment": True,
            "visa": True,
            "salary": True,
            "points": True,
            "pathways": True
        },

        "created_at": datetime.utcnow()
    },

    {
        "code": "CA",
        "name": "Canada",
        "flag": "🇨🇦",
        "classification": "NOC 2021",
        "primary_code_length": 5,
        "benchmark": "https://www.statcan.gc.ca",

        "enabled": True,

        "modules": {
            "occupation": True,
            "express_entry": True,
            "pnp": True,
            "salary": True,
            "teer": True,
            "pathways": True
        },

        "created_at": datetime.utcnow()
    },

    {
        "code": "NZ",
        "name": "New Zealand",
        "flag": "🇳🇿",
        "classification": "ANZSCO",
        "primary_code_length": 6,
        "benchmark": "https://www.immigration.govt.nz",

        "enabled": True,

        "modules": {
            "occupation": True,
            "green_list": True,
            "smc": True,
            "salary": True,
            "pathways": True
        },

        "created_at": datetime.utcnow()
    }
]
async def seed_atlas_countries(db):

    collection = db["atlas_countries"]

    count = await collection.count_documents({})

    if count:
        return

    await collection.insert_many(DEFAULT_COUNTRIES)