"""Surveys Router — Client Satisfaction Surveys"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from core.database import surveys_col, cases_col, users_col
from core.auth import get_current_user
from core.services import log_activity

router = APIRouter(prefix="/surveys", tags=["Surveys"])


class SurveySubmission(BaseModel):
    case_id: str
    overall_rating: int  # 1-5
    communication_rating: int = 0
    speed_rating: int = 0
    documentation_rating: int = 0
    feedback: str = ""
    would_recommend: bool = True


@router.post("/submit")
async def submit_survey(request: SurveySubmission, current_user: dict = Depends(get_current_user)):
    """Submit satisfaction survey for a completed/active case"""
    if current_user["role"] != "client":
        raise HTTPException(status_code=403, detail="Only clients can submit surveys")
    case = await cases_col.find_one({"id": request.case_id, "client_id": current_user["id"]}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    existing = await surveys_col.find_one({"case_id": request.case_id, "client_id": current_user["id"]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Survey already submitted for this case")
    survey = {
        "id": str(uuid.uuid4()), "case_id": request.case_id,
        "client_id": current_user["id"], "client_name": current_user["name"],
        "case_manager_id": case.get("case_manager_id", ""),
        "overall_rating": max(1, min(5, request.overall_rating)),
        "communication_rating": max(0, min(5, request.communication_rating)),
        "speed_rating": max(0, min(5, request.speed_rating)),
        "documentation_rating": max(0, min(5, request.documentation_rating)),
        "feedback": request.feedback, "would_recommend": request.would_recommend,
        "created_at": datetime.now(timezone.utc)
    }
    await surveys_col.insert_one(survey)
    survey.pop("_id", None)
    survey["created_at"] = survey["created_at"].isoformat()
    await log_activity(current_user["id"], current_user["name"], "submit_survey", "survey", survey["id"], {"rating": request.overall_rating})
    return survey


@router.get("/case/{case_id}")
async def get_survey(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get survey for a case"""
    survey = await surveys_col.find_one({"case_id": case_id}, {"_id": 0})
    if survey and isinstance(survey.get("created_at"), datetime):
        survey["created_at"] = survey["created_at"].isoformat()
    return survey or {"exists": False}


@router.get("/stats")
async def get_survey_stats(current_user: dict = Depends(get_current_user)):
    """Get overall survey statistics (admin/CM)"""
    if current_user["role"] not in ["admin", "case_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    cm_filter = {"case_manager_id": current_user["id"]} if current_user["role"] == "case_manager" else {}
    surveys = await surveys_col.find(cm_filter, {"_id": 0}).to_list(1000)
    if not surveys:
        return {"total": 0, "avg_rating": 0, "avg_communication": 0, "avg_speed": 0, "avg_documentation": 0, "recommend_pct": 0, "ratings_distribution": {}}
    total = len(surveys)
    avg_r = sum(s["overall_rating"] for s in surveys) / total
    avg_c = sum(s.get("communication_rating", 0) for s in surveys) / total
    avg_s = sum(s.get("speed_rating", 0) for s in surveys) / total
    avg_d = sum(s.get("documentation_rating", 0) for s in surveys) / total
    recommend = sum(1 for s in surveys if s.get("would_recommend", True))
    dist = {}
    for s in surveys:
        r = str(s["overall_rating"])
        dist[r] = dist.get(r, 0) + 1
    return {
        "total": total, "avg_rating": round(avg_r, 1), "avg_communication": round(avg_c, 1),
        "avg_speed": round(avg_s, 1), "avg_documentation": round(avg_d, 1),
        "recommend_pct": round(recommend / total * 100), "ratings_distribution": dist
    }
