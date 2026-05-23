"""Smart Sales Helper — Phase 6 v2 Part 2: Eligibility Calculator API.

Single endpoint that takes a profile + country + visa, returns deterministic
points breakdown + visa eligibility verdicts + recommendation. NO LLM.

Fast (<50ms). Stateless. No DB writes (calculations are not persisted unless the
sales person explicitly saves them via the parent profile endpoints).
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.sales_calculator import calculate
from core.template_calculator import template_status as _template_status

router = APIRouter(prefix="/sales/calculator", tags=["Smart Sales Helper - Calculator"])

ROLE_SALES = {
    "admin", "admin_owner", "sales_executive", "sr_sales_executive",
    "sales_manager", "sales_head", "partner", "case_manager",
}


def _user_role(user: dict) -> str:
    return user.get("rbac_role") or user.get("role") or ""


def _can_access(user: dict) -> bool:
    return _user_role(user) in ROLE_SALES or "*" in (user.get("permissions") or [])


class CalculateRequest(BaseModel):
    profile: Dict[str, Any] = Field(..., description="Profile with primary_applicant + optional spouse + marital_status")
    country: str = Field(..., description="AU | CA | NZ")
    visa_subclass: Optional[str] = Field(None, description="AU only: 189 | 190 | 491")


@router.post("/calculate")
async def calculate_points(req: CalculateRequest, current_user: dict = Depends(get_current_user)):
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    result = calculate(req.profile, req.country, req.visa_subclass)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    # Phase 6.10.1 — expose template verification status
    status = await _template_status(req.country)
    result["template_status"] = status
    result["template_in_use"] = status == "verified"
    return result


class BatchCalculateRequest(BaseModel):
    profile: Dict[str, Any]
    targets: List[Dict[str, str]] = Field(..., description="List of {country, visa_subclass?} to calculate")


@router.post("/calculate-batch")
async def calculate_batch(req: BatchCalculateRequest, current_user: dict = Depends(get_current_user)):
    """Calculate the same profile against multiple country/visa combos in one call.
    Useful for the Compare Top 3 mode (AU 189 + CA EE-FSWP + NZ SMC).
    """
    if not _can_access(current_user):
        raise HTTPException(status_code=403, detail="Not authorised")
    out = []
    for t in req.targets:
        country = t.get("country")
        if not country:
            continue
        r = calculate(req.profile, country, t.get("visa_subclass"))
        # Phase 6.10.1 — surface template status per result
        if "error" not in r:
            status = await _template_status(country)
            r["template_status"] = status
            r["template_in_use"] = status == "verified"
        out.append(r)
    return {"results": out, "count": len(out)}
