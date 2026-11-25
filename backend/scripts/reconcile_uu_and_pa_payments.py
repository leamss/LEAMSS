import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

async def reconcile():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["leamss"]
    
    # 1. Reconcile PA-20261023-6F635C
    # Sale id: 2820a49c-5d2c-4a16-a4ac-faf2e563b640 (amount_received: 107006.54, fee: 107006.54, status: paid)
    # Linked case: 896316c9-820d-48ec-8e54-66974f9be671 (active)
    pa_target = await db["pre_assessments"].find_one({"pa_number": "PA-20261023-6F635C"})
    if pa_target:
        parts = pa_target.get("proposal_payment_parts") or []
        for p in parts:
            p["status"] = "paid"
            if not p.get("paid_at"):
                p["paid_at"] = datetime.now(timezone.utc).isoformat()
        
        await db["pre_assessments"].update_one(
            {"_id": pa_target["_id"]},
            {"$set": {
                "stage": "case_created",
                "proposal_status": "paid",
                "proposal_amount_paid": 107006.54,
                "proposal_amount_pending": 0.0,
                "proposal_payment_parts": parts,
                "sale_id": "2820a49c-5d2c-4a16-a4ac-faf2e563b640",
                "case_id": "896316c9-820d-48ec-8e54-66974f9be671",
                "pending_installment_unlock": False,
                "payment_method_configured": True,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        print("✅ Reconciled PA-20261023-6F635C: marked fully paid (107,006.54) and stage=case_created.")

    # 2. Reconcile PA-20261019-9FEB82
    # Remove the misattributed payment (it only paid step 1 fee of 236)
    pa_older = await db["pre_assessments"].find_one({"pa_number": "PA-20261019-9FEB82"})
    if pa_older:
        older_parts = pa_older.get("proposal_payment_parts") or []
        for idx, p in enumerate(older_parts):
            p["status"] = "pending" if idx == 0 else "locked"
            p.pop("paid_at", None)
            p.pop("payment_ref", None)
            
        await db["pre_assessments"].update_one(
            {"_id": pa_older["_id"]},
            {"$set": {
                "stage": "proposal_sent",
                "proposal_status": "sent",
                "proposal_amount_paid": 0.0,
                "proposal_amount_pending": float(pa_older.get("proposal_fee") or 82577.0),
                "proposal_payment_parts": older_parts,
                "payment_method_configured": True,
                "pending_installment_unlock": False,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        print("✅ Reconciled PA-20261019-9FEB82: reset misattributed payment and transitioned to proposal_sent.")

    # 3. Check any other PAs where linked sale is fully paid but PA is still package_selected
    cursor = db["pre_assessments"].find({"stage": "package_selected"})
    async for p in cursor:
        paid = float(p.get("proposal_amount_paid") or 0)
        fee = float(p.get("proposal_fee") or 0)
        pending = p.get("proposal_amount_pending")
        if (paid > 0 and (pending == 0 or paid >= fee)) or p.get("payment_method_configured"):
            new_stage = "proposal_paid" if (pending == 0 or paid >= fee) else "proposal_sent"
            await db["pre_assessments"].update_one(
                {"_id": p["_id"]},
                {"$set": {
                    "stage": new_stage,
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            print(f"✅ Auto-reconciled PA {p.get('pa_number')} to {new_stage}.")

if __name__ == "__main__":
    asyncio.run(reconcile())
