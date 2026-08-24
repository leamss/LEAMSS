"""Seed international and domestic bank accounts for LEAMSS Portal."""
import asyncio
import os
import sys

# Ensure backend root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db

accounts = [
    {
        "id": "default-account",
        "country": "default",
        "currency": "INR",
        "account_name": "SBI",
        "account_number": "1234567890",
        "ifsc_or_swift": "PPOOJJAA",
        "bank_name": "SBI",
        "bank_address": "123, mumbai, india",
        "active": True
    },
    {
        "id": "aus-account",
        "country": "Australia",
        "currency": "AUD",
        "account_name": "Rohit",
        "account_number": "9999999999",
        "ifsc_or_swift": "ROHIT",
        "bank_name": "HDFC",
        "bank_address": "123, Australia",
        "active": True
    },
    {
        "id": "can-account",
        "country": "Canada",
        "currency": "CAD",
        "account_name": "ROHIT ",
        "account_number": "1234567",
        "ifsc_or_swift": "003",
        "bank_name": "Royal Bank of Canada (RBC)",
        "bank_address": "John Doe123 Main Street Apt 4BToronto ON M5V 2N8Canada",
        "active": True
    },
    {
        "id": "uk-account",
        "country": "United Kingdom",
        "currency": "GBP",
        "account_name": "ROHIT",
        "account_number": "12345678",
        "ifsc_or_swift": "ABCDGB2LXXX",
        "bank_name": "Barclays Bank PLC",
        "bank_address": "1 Churchill Place, London, E14 5HP",
        "active": True
    },
    {
        "id": "usa-account",
        "country": "United States",
        "currency": "USD",
        "account_name": "POOJA",
        "account_number": "123456789012",
        "ifsc_or_swift": "BOFAUS3NXXX",
        "bank_name": "Bank of America, N.A.",
        "bank_address": "100 North Tryon Street, Charlotte, NC 28255",
        "active": True
    },
    {
        "id": "nz-account",
        "country": "New Zealand",
        "currency": "NZD",
        "account_name": "puja",
        "account_number": "011234056789000",
        "ifsc_or_swift": "ANZBNZ2WXXX",
        "bank_name": "ANZ Bank New Zealand Limited",
        "bank_address": "170 Featherston Street, Wellington, 6011",
        "active": True
    }
]


async def seed_banks():
    col = db["international_bank_accounts"]
    for acc in accounts:
        await col.update_one({"id": acc["id"]}, {"$set": acc}, upsert=True)
    count = await col.count_documents({})
    print(f"Successfully upserted bank accounts. Total in DB: {count}")
    docs = await col.find({}, {"_id": 0}).to_list(100)
    for d in docs:
        print(f"  - {d.get('id')}: {d.get('country')} ({d.get('currency')}) -> {d.get('bank_name')}")


if __name__ == "__main__":
    asyncio.run(seed_banks())
