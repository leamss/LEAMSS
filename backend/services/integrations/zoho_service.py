"""Zoho CRM & Forms Integration Service.

Supports:
- OAuth2 token exchange and auto-refresh across regional accounts (.com, .in, .eu, .com.au)
- Lead pull synchronization
- Outbound lead export
- Real-time webhook payload parsing
"""
import httpx
from typing import Dict, Any, List, Optional
from services.integrations.encryption_util import decrypt_secret

DEFAULT_ZOHO_ACCOUNTS_URL = "https://accounts.zoho.com"
DEFAULT_ZOHO_API_URL = "https://www.zohoapis.com"


def _get_zoho_urls(credentials: Dict[str, Any]) -> tuple:
    region = (credentials.get("region") or "com").lower()
    accounts_url = credentials.get("accounts_url") or f"https://accounts.zoho.{region}"
    api_url = credentials.get("api_domain") or f"https://www.zohoapis.{region}"
    return accounts_url, api_url


async def refresh_zoho_access_token(credentials: Dict[str, Any]) -> str:
    """Refreshes Zoho OAuth access token using refresh token."""
    client_id = decrypt_secret(credentials.get("client_id"))
    client_secret = decrypt_secret(credentials.get("client_secret"))
    refresh_token = decrypt_secret(credentials.get("refresh_token"))
    accounts_url, _ = _get_zoho_urls(credentials)

    if not client_id or not client_secret or not refresh_token:
        # If API token or direct access token provided
        token = decrypt_secret(credentials.get("access_token"))
        if token:
            return token
        raise ValueError("Zoho client_id, client_secret, and refresh_token are required.")

    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{accounts_url}/oauth/v2/token", params=params)
        data = resp.json()
        if "access_token" in data:
            return data["access_token"]
        error_msg = data.get("error") or data.get("message") or resp.text
        raise ValueError(f"Failed to refresh Zoho access token: {error_msg}")


async def test_zoho_connection(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """Tests connection to Zoho CRM API."""
    try:
        # If simulated credentials or mock mode
        if credentials.get("mode") == "test":
            return {"success": True, "message": "Zoho test connection successful (Mock Verified)."}

        token = await refresh_zoho_access_token(credentials)
        _, api_url = _get_zoho_urls(credentials)

        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{api_url}/crm/v2/users?type=CurrentUser", headers=headers)
            if resp.status_code in [200, 201]:
                user_info = resp.json().get("users", [{}])[0]
                user_name = user_info.get("full_name") or user_info.get("email") or "Zoho User"
                return {
                    "success": True,
                    "message": f"Successfully connected to Zoho CRM as {user_name}."
                }
            return {
                "success": False,
                "message": f"Zoho API responded with status {resp.status_code}: {resp.text}"
            }
    except Exception as e:
        return {"success": False, "message": f"Zoho connection error: {str(e)}"}


async def fetch_zoho_leads(credentials: Dict[str, Any], max_records: int = 50) -> List[Dict[str, Any]]:
    """Pulls recent leads from Zoho CRM Leads module."""
    if credentials.get("mode") == "test":
        return [
            {
                "name": "Arjun Sharma",
                "email": "arjun.sharma@example.com",
                "phone": "+919876543210",
                "city": "Mumbai",
                "country": "Canada",
                "service_interested": "Canada Express Entry",
                "campaign": "Zoho Web Form",
                "source": "Zoho CRM",
                "message": "Interested in express entry profile evaluation."
            }
        ]

    token = await refresh_zoho_access_token(credentials)
    _, api_url = _get_zoho_urls(credentials)
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{api_url}/crm/v2/Leads",
            headers=headers,
            params={"page": 1, "per_page": min(max_records, 100), "sort_by": "Created_Time", "sort_order": "desc"}
        )
        if resp.status_code not in [200, 204]:
            raise ValueError(f"Zoho returned status {resp.status_code}: {resp.text}")

        if resp.status_code == 204:
            return []

        leads_data = resp.json().get("data", [])
        standardized = []
        for l in leads_data:
            full_name = l.get("Full_Name") or f"{l.get('First_Name', '')} {l.get('Last_Name', '')}".strip()
            standardized.append({
                "name": full_name or "Zoho Lead",
                "email": l.get("Email") or "",
                "phone": l.get("Phone") or l.get("Mobile") or "",
                "city": l.get("City") or "",
                "country": l.get("Country") or "",
                "service_interested": l.get("Service_Interested") or l.get("Interest") or "Visa Consultation",
                "campaign": l.get("Lead_Source") or "Zoho CRM",
                "source": "Zoho CRM",
                "message": l.get("Description") or ""
            })
        return standardized


def parse_zoho_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes payload received from Zoho Workflow webhook."""
    # Zoho webhook can deliver lead fields directly or nested under data/lead
    d = payload.get("data") or payload.get("lead") or payload
    if isinstance(d, list) and len(d) > 0:
        d = d[0]

    name = d.get("Full_Name") or d.get("name") or f"{d.get('First_Name', '')} {d.get('Last_Name', '')}".strip()
    return {
        "name": name or "Zoho Webhook Lead",
        "email": d.get("Email") or d.get("email") or "",
        "phone": d.get("Phone") or d.get("Mobile") or d.get("phone") or "",
        "city": d.get("City") or d.get("city") or "",
        "country": d.get("Country") or d.get("country") or "",
        "service_interested": d.get("Service_Interested") or d.get("service") or d.get("Services") or "Immigration",
        "campaign": d.get("Campaign_Name") or d.get("Lead_Source") or "Zoho Webhook",
        "source": "Zoho CRM",
        "message": d.get("Description") or d.get("notes") or d.get("message") or ""
    }
