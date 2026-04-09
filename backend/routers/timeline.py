"""Case Timeline Router — Visual timeline of all case events"""
from fastapi import APIRouter, Depends
from core.database import (
    cases_col, case_steps_col, documents_col, audit_logs_col,
    chat_messages_col, chat_conversations_col, case_transfers_col,
    case_notes_col, notifications_col
)
from core.auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get("/case/{case_id}")
async def get_case_timeline(case_id: str, current_user: dict = Depends(get_current_user)):
    """Get complete timeline of events for a case"""
    events = []

    # 1. Case steps events
    steps = await case_steps_col.find({"case_id": case_id}, {"_id": 0}).to_list(100)
    for s in steps:
        if s.get("started_at"):
            ts = s["started_at"]
            events.append({
                "type": "step_started", "icon": "play",
                "title": f"Step Started: {s['step_name']}",
                "description": f"Step {s.get('step_order', 0)} initiated",
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "color": "blue"
            })
        if s.get("completed_at"):
            ts = s["completed_at"]
            events.append({
                "type": "step_completed", "icon": "check",
                "title": f"Step Completed: {s['step_name']}",
                "description": s.get("notes", ""),
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "color": "green"
            })
        if s.get("deadline"):
            events.append({
                "type": "deadline_set", "icon": "clock",
                "title": f"Deadline Set: {s['step_name']}",
                "description": f"Due: {s['deadline'][:10]}",
                "timestamp": s["deadline"][:19],
                "color": "amber"
            })

    # 2. Documents uploaded
    docs = await documents_col.find({"case_id": case_id}, {"_id": 0}).to_list(200)
    for d in docs:
        ts = d.get("uploaded_at") or d.get("created_at")
        if ts:
            events.append({
                "type": "document_uploaded", "icon": "upload",
                "title": f"Document Uploaded: {d.get('filename', '')}",
                "description": f"Type: {d.get('document_type', 'general')} | Status: {d.get('status', 'pending')}",
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "color": "purple"
            })
        if d.get("reviewed_at"):
            ts = d["reviewed_at"]
            events.append({
                "type": "document_reviewed", "icon": "eye",
                "title": f"Document Reviewed: {d.get('filename', '')}",
                "description": f"{d.get('status', '')} by {d.get('reviewer_name', '')}",
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "color": "green" if d.get("status") == "approved" else "red"
            })

    # 3. Chat messages
    convo = await chat_conversations_col.find_one({"case_id": case_id}, {"_id": 0})
    if convo:
        msgs = await chat_messages_col.find({"conversation_id": convo["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
        for m in msgs[:5]:
            ts = m.get("created_at")
            events.append({
                "type": "chat_message", "icon": "message",
                "title": f"Chat: {m.get('sender_name', '')}",
                "description": m.get("message", "")[:100],
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
                "color": "teal"
            })

    # 4. Transfers
    transfers = await case_transfers_col.find({"case_id": case_id}, {"_id": 0}).to_list(20)
    for t in transfers:
        ts = t.get("created_at")
        events.append({
            "type": "case_transfer", "icon": "transfer",
            "title": f"Case Transferred: {t.get('from_cm_name', '')} → {t.get('to_cm_name', '')}",
            "description": t.get("reason", ""),
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            "color": "orange"
        })

    # 5. Notes
    notes = await case_notes_col.find({"case_id": case_id}, {"_id": 0}).to_list(50)
    for n in notes:
        ts = n.get("created_at")
        events.append({
            "type": "note_added", "icon": "note",
            "title": f"Note by {n.get('author_name', '')}",
            "description": n.get("content", "")[:150],
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            "color": "yellow"
        })

    # 6. Case creation
    case = await cases_col.find_one({"id": case_id}, {"_id": 0, "created_at": 1, "client_name": 1, "product_name": 1})
    if case and case.get("created_at"):
        ts = case["created_at"]
        events.insert(0, {
            "type": "case_created", "icon": "plus",
            "title": "Case Created",
            "description": f"{case.get('client_name', '')} — {case.get('product_name', '')}",
            "timestamp": ts.isoformat() if isinstance(ts, datetime) else str(ts),
            "color": "blue"
        })

    # Sort by timestamp descending
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    return {"case_id": case_id, "events": events, "total": len(events)}
