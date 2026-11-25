"""Meta (Facebook & Instagram) Lead Ads Integration Service.

Supports:
- Webhook subscription handshake verification (hub.verify_token & hub.challenge)
- Real-time leadgen event parsing for both Facebook Pages & Instagram Professional accounts
- Automatic field extraction via Meta Graph API v19.0
- Page and Ad Account token validation
"""
import httpx
from typing import Dict, Any, List, Optional
from services.integrations.encryption_util import decrypt_secret

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def verify_meta_webhook(mode: Optional[str], token: Optional[str], challenge: Optional[str], expected_token: str) -> Optional[str]:
    """Validates Meta Webhook subscription verification request."""
    if mode == "subscribe" and token == expected_token:
        return challenge
    return None


async def test_meta_connection(credentials: Dict[str, Any], provider: str = "facebook") -> Dict[str, Any]:
    """Validates Page or System Access Token against Meta Graph API."""
    if credentials.get("mode") == "test":
        entity = "Instagram Business Account" if provider == "instagram" else "Facebook Page"
        return {"success": True, "message": f"{entity} access token verified successfully (Test Mode)."}

    token = decrypt_secret(credentials.get("page_access_token") or credentials.get("access_token"))
    if not token:
        return {"success": False, "message": "Access token is required for Meta integration."}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{GRAPH_API_BASE}/me", params={"access_token": token, "fields": "id,name"})
            if resp.status_code == 200:
                data = resp.json()
                page_name = data.get("name", "Meta Page")
                return {"success": True, "message": f"Successfully connected to Meta Page: '{page_name}'"}
            return {"success": False, "message": f"Meta Graph API error {resp.status_code}: {resp.text[:150]}"}
    except Exception as e:
        return {"success": False, "message": f"Meta connection failed: {str(e)}"}


async def fetch_meta_leadgen_details(leadgen_id: str, access_token: str, provider: str = "facebook") -> Dict[str, Any]:
    """Fetches submitted form field data from Meta Graph API using leadgen_id."""
    clean_token = decrypt_secret(access_token)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_API_BASE}/{leadgen_id}",
            params={"access_token": clean_token}
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to fetch leadgen {leadgen_id} from Meta: {resp.text}")

        lead_data = resp.json()
        field_data = lead_data.get("field_data", [])

        extracted: Dict[str, Any] = {
            "name": "",
            "email": "",
            "phone": "",
            "city": "",
            "country": "",
            "service_interested": "",
            "message": "",
            "campaign": lead_data.get("ad_name") or f"{provider.capitalize()} Lead Ad",
            "source": provider.capitalize()
        }

        for f in field_data:
            fname = str(f.get("name", "")).lower()
            vals = f.get("values", [])
            val = str(vals[0]).strip() if vals else ""

            if any(k in fname for k in ["full_name", "name", "first_name"]):
                extracted["name"] = val
            elif "email" in fname:
                extracted["email"] = val
            elif any(k in fname for k in ["phone", "mobile", "contact"]):
                extracted["phone"] = val
            elif any(k in fname for k in ["city", "location"]):
                extracted["city"] = val
            elif any(k in fname for k in ["country", "destination"]):
                extracted["country"] = val
            elif any(k in fname for k in ["service", "interest", "program", "visa"]):
                extracted["service_interested"] = val
            else:
                if val:
                    extracted["message"] += f"{f.get('name')}: {val}; "

        return extracted
