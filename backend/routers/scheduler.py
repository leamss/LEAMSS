"""
Scheduled tasks router for LEAMSS Portal
Handles background jobs and scheduled operations
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from datetime import datetime, timezone

from core.auth import require_role, UserRole
from services.expiry_service import check_expiring_documents, get_expiring_documents_summary

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.post("/check-expiring-documents")
async def trigger_expiry_check(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """
    Manually trigger the document expiry check.
    This can also be called by an external cron/scheduler.
    """
    background_tasks.add_task(check_expiring_documents)
    return {
        "message": "Document expiry check started in background",
        "triggered_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/expiring-documents")
async def get_expiring_docs(
    user: dict = Depends(require_role([UserRole.ADMIN, UserRole.CASE_MANAGER]))
):
    """
    Get a list of all documents expiring within the next 30 days.
    """
    expiring = await get_expiring_documents_summary()
    return {
        "total_expiring": len(expiring),
        "documents": expiring
    }


@router.post("/run-expiry-check-now")
async def run_expiry_check_now(
    user: dict = Depends(require_role([UserRole.ADMIN]))
):
    """
    Run the expiry check immediately (synchronously) and return results.
    Use for testing or immediate verification.
    """
    stats = await check_expiring_documents()
    return {
        "message": "Expiry check completed",
        "stats": stats,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
