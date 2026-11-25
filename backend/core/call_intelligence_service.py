"""
LEAMSS CRM - Centralized Call Intelligence Service
Handles AI-powered structured call summarization, genuine transcript tracking,
sentiment detection, and permanent CRM synchronization across all call channels.

Rules:
- Never generate fake or hallucinated transcripts. If audio is missing or carrier
  transcription stream is unavailable, clearly record the exact status.
- Highlight 4 core pillars in summaries:
  1. Main Discussion
  2. Client Requirements
  3. Concerns & Objections
  4. Next Steps & Action Items
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from core.database import db

logger = logging.getLogger(__name__)

crm_calls_col = db["crm_calls"]
leads_col = db["leads"]


def resolve_transcription_status(call_doc: Dict[str, Any]) -> Dict[str, str]:
    """
    Evaluates whether genuine transcript content exists or what the clear status is.
    Zero hallucination policy: if unavailable, states the exact operational reason.
    """
    transcript = (call_doc.get("transcript") or "").strip()
    recording_url = (call_doc.get("recording_url") or "").strip()

    if transcript:
        return {
            "transcription_status": "completed",
            "transcription_status_reason": "Full conversation transcript recorded"
        }
    elif recording_url:
        return {
            "transcription_status": "unavailable",
            "transcription_status_reason": "Audio recording attached; carrier SIM transcription stream unavailable"
        }
    else:
        return {
            "transcription_status": "unavailable",
            "transcription_status_reason": "No audio or speech stream captured for this session"
        }


def _heuristic_summary_extraction(call_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic rule-based summary extractor that parses real notes, outcomes,
    lead preferences, and duration when external AI service is unreachable or key is not set.
    Never produces fake dialogues.
    """
    notes = str(call_doc.get("notes") or "").strip()
    transcript = str(call_doc.get("transcript") or "").strip()
    outcome = str(call_doc.get("outcome") or call_doc.get("status") or "connected").replace("_", " ").title()
    client_name = call_doc.get("lead_name") or call_doc.get("client_name") or "Client"
    salesperson_name = call_doc.get("sales_person_name") or "Advisor"
    duration = int(call_doc.get("duration_seconds") or 0)
    dur_str = f"{duration // 60}m {duration % 60}s" if duration > 0 else "0s"
    direction = str(call_doc.get("direction") or "outgoing").title()

    # Extract requirements from notes, transcript or outcome
    requirements = []
    concerns = []
    next_steps = []
    main_points = []

    # Parse both notes and transcript lines (stripping dialogue prefixes like "Sales Rep:", "Client:")
    combined_content = f"{transcript}\n{notes}".strip()
    raw_lines = [ln.strip() for ln in re.split(r"[\n;]+", combined_content) if ln.strip()]

    for line in raw_lines:
        clean_line = re.sub(r"^(sales\s*(rep|person|executive)?|advisor|client|customer)\s*:\s*", "", line, flags=re.IGNORECASE).strip()
        lower = clean_line.lower()
        if not clean_line or len(clean_line) < 4:
            continue
        if any(w in lower for w in ["concern", "doubt", "hesitant", "worry", "worried", "price", "fee", "cost", "delay", "issue", "problem", "budget", "objection"]):
            concerns.append(clean_line)
        elif any(w in lower for w in ["next", "follow up", "send", "call back", "schedule", "meeting", "share", "action", "submit", "invite", "demo"]) or "next step" in lower:
            next_steps.append(clean_line)
        elif any(w in lower for w in ["require", "want", "interested in", "target", "seeking", "visa", "study", "work", "eligibility", "points", "draw", "process"]) or re.search(r"\bpr\b", lower):
            requirements.append(clean_line)
        else:
            main_points.append(clean_line)

    if not requirements:
        if "interested" in outcome.lower():
            requirements.append(f"Inquired about migration pathway opportunities ({outcome})")
        else:
            requirements.append(f"Discussion on consultation pathway options ({outcome})")

    if not concerns:
        if "not interested" in outcome.lower() or "rejected" in outcome.lower():
            concerns.append("Client indicated timing or eligibility constraints at present")
        else:
            concerns.append("No critical blockers or pricing objections noted during this call")

    if not next_steps:
        if "follow up" in outcome.lower() or "call back" in outcome.lower():
            next_steps.append("Schedule follow-up call with client to review application documents")
        elif "converted" in outcome.lower() or "payment" in outcome.lower():
            next_steps.append("Generate client service agreement and invoice for retainer")
        else:
            next_steps.append("Continue tracking via CRM timeline and maintain communication cadence")

    main_discussion = (
        "; ".join(main_points[:3])
        if main_points
        else f"{direction} consultation call between {salesperson_name} and {client_name} (Duration: {dur_str}). Call outcome logged as: {outcome}."
    )

    sentiment = "Neutral"
    out_lower = outcome.lower()
    if any(pos in out_lower for pos in ["interested", "converted", "payment", "positive", "agreed"]):
        sentiment = "Positive"
    elif any(neg in out_lower for pos in ["not interested", "wrong", "rejected", "declined", "negative"]):
        sentiment = "Negative"

    first_req = requirements[0] if requirements else f"Consultation on {outcome}"
    first_step = next_steps[0] if next_steps else "Follow up via CRM"
    exec_summary = f"{direction} call with {client_name} ({outcome}, {dur_str}). {first_req}. Next: {first_step}."

    return {
        "main_discussion": main_discussion,
        "client_requirements": requirements[:5],
        "concerns_objections": concerns[:5],
        "concerns": concerns[:5],
        "next_steps": next_steps[:5],
        "sentiment": sentiment,
        "executive_summary": exec_summary,
        "engine": "heuristic_fallback"
    }


async def generate_call_ai_summary(call_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesizes a structured AI call summary highlighting:
    - Main Discussion
    - Client Requirements
    - Concerns & Objections
    - Next Steps & Action Items
    - Executive Summary & Sentiment
    Uses Perplexity Sonar when configured, with a smart heuristic fallback.
    """
    transcript = (call_doc.get("transcript") or "").strip()
    notes = (call_doc.get("notes") or "").strip()
    client_name = call_doc.get("lead_name") or call_doc.get("client_name") or "Client"
    salesperson_name = call_doc.get("sales_person_name") or "Salesperson"
    outcome = call_doc.get("outcome") or call_doc.get("status") or "connected"
    duration = call_doc.get("duration_seconds") or 0

    content_to_analyze = transcript or notes
    if not content_to_analyze:
        # If neither notes nor transcript exist, return heuristic outline based on metadata
        return _heuristic_summary_extraction(call_doc)

    # Attempt Perplexity / LLM Synthesis if key is configured
    try:
        from core.perplexity_client import call_perplexity, _get_api_key
        if _get_api_key():
            prompt = f"""You are an expert CRM Call Analyst for LEAMSS Immigration & Consulting Portal.
Analyze the following call interaction and produce a concise, strictly structured JSON summary.

CALL METADATA:
- Client Name: {client_name}
- Advisor / Salesperson: {salesperson_name}
- Call Outcome: {outcome}
- Duration: {duration} seconds

CONVERSATION CONTENT / CONSULTATION NOTES:
\"\"\"
{content_to_analyze}
\"\"\"

CRITICAL INSTRUCTIONS:
1. Do NOT invent or hallucinate facts that are not present.
2. Return ONLY valid JSON with no markdown wrapping and no explanation.
3. Structure:
{{
  "main_discussion": "Brief factual summary of what was discussed during the call",
  "client_requirements": ["Specific requirement or target country/visa mentioned", "Qualification/experience criteria"],
  "concerns_objections": ["Any doubts, budget constraints, timing worries, or None mentioned"],
  "next_steps": ["Exact action items or follow-up agreed upon"],
  "sentiment": "Positive" | "Neutral" | "Negative",
  "executive_summary": "1-2 sentence overall summary for quick CRM scanning"
}}"""

            response_text, model_used = await call_perplexity(
                prompt=prompt,
                system_msg="You extract factual structured CRM call summaries in JSON.",
                max_tokens=600,
                temperature=0.1,
                timeout=12.0
            )

            # Robust JSON extraction: match the first outermost JSON object in the response
            parsed = None
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                except Exception:
                    pass

            if not parsed:
                clean_json = re.sub(r"^```(json)?\s*", "", response_text.strip(), flags=re.IGNORECASE)
                clean_json = re.sub(r"\s*```$", "", clean_json.strip())
                parsed = json.loads(clean_json)

            # Ensure lists
            reqs = parsed.get("client_requirements")
            if isinstance(reqs, str):
                reqs = [reqs]
            elif not isinstance(reqs, list):
                reqs = []

            concerns = parsed.get("concerns_objections")
            if isinstance(concerns, str):
                concerns = [concerns]
            elif not isinstance(concerns, list):
                concerns = []

            steps = parsed.get("next_steps")
            if isinstance(steps, str):
                steps = [steps]
            elif not isinstance(steps, list):
                steps = []

            return {
                "main_discussion": str(parsed.get("main_discussion") or f"Consultation between {salesperson_name} and {client_name}"),
                "client_requirements": reqs or ["General immigration inquiry"],
                "concerns_objections": concerns or ["No major concerns noted"],
                "concerns": concerns or ["No major concerns noted"],
                "next_steps": steps or ["Follow up via CRM"],
                "sentiment": str(parsed.get("sentiment") or "Neutral"),
                "executive_summary": str(parsed.get("executive_summary") or parsed.get("main_discussion") or ""),
                "engine": f"ai_{model_used}"
            }
    except Exception as e:
        logger.info("Perplexity call summary fallback triggered: %s", e)

    # Fallback heuristic
    return _heuristic_summary_extraction(call_doc)


async def process_call_intelligence(call_id: str, update_db: bool = True) -> Optional[Dict[str, Any]]:
    """
    Loads call record by ID, resolves genuine transcription status,
    generates structured AI summary, and permanently updates MongoDB.
    """
    query_conditions = [{"id": call_id}]
    try:
        from bson import ObjectId
        query_conditions.append({"_id": ObjectId(call_id)})
    except Exception:
        pass

    call_doc = await crm_calls_col.find_one({"$or": query_conditions})
    if not call_doc:
        logger.warning("Call record not found for intelligence processing: %s", call_id)
        return None

    resolved_id = call_doc.get("id") or str(call_doc.get("_id") or call_id)

    # 1. Resolve genuine transcription status (no dummy transcripts)
    trans_meta = resolve_transcription_status(call_doc)

    # 2. Generate structured AI summary
    try:
        summary_data = await generate_call_ai_summary(call_doc)
    except Exception as e:
        logger.warning(f"generate_call_ai_summary failed: {e}, falling back to heuristic")
        summary_data = _heuristic_summary_extraction(call_doc)

    concerns_list = summary_data.get("concerns_objections") or summary_data.get("concerns") or ["No major concerns noted"]
    next_steps_list = summary_data.get("next_steps") or ["Follow up with client"]
    next_action = next_steps_list[0] if (isinstance(next_steps_list, list) and next_steps_list) else "Follow up with client"

    updates = {
        "transcription_status": trans_meta["transcription_status"],
        "transcription_status_reason": trans_meta["transcription_status_reason"],
        "ai_summary": summary_data.get("executive_summary", ""),
        "ai_summary_structured": {
            "main_discussion": summary_data.get("main_discussion", ""),
            "client_requirements": summary_data.get("client_requirements", []),
            "concerns_objections": concerns_list,
            "concerns": concerns_list,
            "next_steps": next_steps_list,
            "sentiment": summary_data.get("sentiment", "Neutral"),
            "executive_summary": summary_data.get("executive_summary", ""),
            "engine": summary_data.get("engine", "ai"),
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "ai_sentiment": summary_data.get("sentiment", "Neutral"),
        "next_best_action": next_action,
        "updated_at": datetime.now(timezone.utc)
    }

    if update_db:
        up_query = {"$or": [{"id": resolved_id}]}
        try:
            from bson import ObjectId
            up_query["$or"].append({"_id": ObjectId(resolved_id)})
        except Exception:
            pass
        await crm_calls_col.update_one(up_query, {"$set": updates})

    clean_doc = {**call_doc, **updates}
    if "_id" in clean_doc:
        clean_doc["_id"] = str(clean_doc["_id"])
    if "id" not in clean_doc:
        clean_doc["id"] = resolved_id

    return clean_doc
