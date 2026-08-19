"""GSM enrichment: add 189/190/491/485 (MLTSSL) pathways to the CSOL-seeded records
that are also on the MLTSSL (ANZSCO 2013). Matched by 2022 code == 2013 code, or
normalised title. Updates pathway_list -> 'MLTSSL;CSOL' and stores the 2013 dual code.
"""
import asyncio, os, json, re
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
ISO = datetime.now(timezone.utc).isoformat()

csol_missing = [x["code"] for x in json.load(open("/tmp/csol_missing.json"))["csol_missing"]]
hier = json.load(open("/tmp/hier2022.json"))
mltssl = json.load(open("/tmp/mltssl.json"))


def norm(t):
    t = (t or "").lower()
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"[^a-z ]", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    w = t.split()
    if w and w[-1].endswith("s") and len(w[-1]) > 3:
        w[-1] = w[-1][:-1]
    return " ".join(w)


mlt_titles = {norm(v): k for k, v in mltssl.items()}

GSM_VISAS = [
    {"visa_subclass": "189", "notes": "Skilled Independent  (subclass 189) - Points-Tested", "eligible": True, "list": "MLTSSL"},
    {"visa_subclass": "190", "notes": "Skilled Nominated   (subclass 190)", "eligible": True, "list": "MLTSSL"},
    {"visa_subclass": "491", "notes": "Skilled Work Regional (provisional) visa (subclass 491) State or Territory nominated", "eligible": True, "list": "MLTSSL"},
    {"visa_subclass": "491", "notes": "Skilled Work Regional (provisional) visa (subclass 491) Family Sponsored", "eligible": True, "list": "MLTSSL"},
    {"visa_subclass": "485", "notes": "Temporary Graduate (subclass 485)", "eligible": True, "list": "MLTSSL"},
]

NOTE = ("Employer-sponsored pathways use ANZSCO 2022 / CSOL. GSM points-tested pathways "
        "(189/190/491/485) use the ANZSCO 2013 equivalent code {c2013} on the MLTSSL.")


async def main():
    c = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = c[os.environ["DB_NAME"]]
    col = db["occupation_master"]
    updated = []
    for code in csol_missing:
        title = hier.get(code, {}).get("title", "")
        m = None
        if code in mltssl:
            m = code
        else:
            for v in [norm(title)] + [norm(p) for p in re.split(r"[/\\]", title)]:
                if v in mlt_titles:
                    m = mlt_titles[v]
                    break
        if not m:
            continue
        doc = await col.find_one({"code": code, "country_code": "AU", "source": "csol_2022_gap_seed"})
        if not doc:
            continue
        visas = doc["visa_pathways"]["visa_eligibility"]
        existing = {v["visa_subclass"] for v in visas}
        new_visas = [dict(v) for v in GSM_VISAS if v["visa_subclass"] not in existing]
        # keep GSM first (points-tested PR), then existing CSOL
        merged = new_visas + visas
        await col.update_one({"_id": doc["_id"]}, {"$set": {
            "visa_pathways.visa_eligibility": merged,
            "visa_pathways.pathway_lists": ["MLTSSL", "CSOL"],
            "pathway_lists": ["MLTSSL", "CSOL"],
            "pathway_list": "MLTSSL;CSOL",
            "classification_dual_code": {"2022": code, "2013": m},
            "compliance_note": NOTE.format(c2013=m),
            "updated_at": ISO,
        }})
        updated.append(f"{code} {title} (MLTSSL 2013={m})")
    print(f"GSM-enriched: {len(updated)}")
    for u in updated:
        print("  +", u)


if __name__ == "__main__":
    asyncio.run(main())
