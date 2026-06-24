"""Phase 21 Slice 3 Days 3-5 — Content Studio + SEO/AEO/GEO tools.

Powered by Claude Sonnet 4.5 via emergentintegrations + EMERGENT_LLM_KEY.

Endpoints under:
- /api/content-studio/* — generate/save/regenerate/publish drafts
- /api/seo/* — keyword research / meta optimize / internal link suggest
- /api/aeo/* — FAQ schema / voice search / featured snippet
- /api/geo/* — LLM content audit / structured data / citation optimizer
"""
import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.database import db
from core.auth import get_current_user

router = APIRouter(prefix="", tags=["Content Studio + SEO/AEO/GEO"])

drafts_col = db["content_drafts"]
seo_runs_col = db["seo_runs"]
geo_runs_col = db["geo_runs"]
llm_cache_col = db["llm_cache"]


def _is_marketing_or_admin(user: dict) -> bool:
    role = (user.get("role") or "").lower()
    rbac = (user.get("rbac_role") or "").lower()
    if role == "admin" or "*" in (user.get("permissions") or []):
        return True
    return any(k in rbac for k in ["marketing", "admin", "owner", "head", "content"])


CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


async def _llm_call(system_prompt: str, user_prompt: str, session_id: str = None, max_tokens: int = 2500) -> str:
    """Single call to Claude Sonnet 4.5 via emergentintegrations.

    Caches identical prompts for 1 hour to avoid double-billing.
    """
    cache_key = hashlib.sha256(f"{system_prompt}|||{user_prompt}".encode()).hexdigest()
    cached = await llm_cache_col.find_one({"cache_key": cache_key}, {"_id": 0, "response": 1, "created_at": 1})
    if cached:
        created_at = cached["created_at"]
        # Motor may return naive datetime — normalize to UTC-aware for safe subtraction
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
        if age_seconds < 3600:
            return cached["response"]

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM library not available: {e}")

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="EMERGENT_LLM_KEY not configured")

    chat = (
        LlmChat(
            api_key=api_key,
            session_id=session_id or str(uuid.uuid4()),
            system_message=system_prompt,
        )
        .with_model("anthropic", CLAUDE_MODEL)
    )
    msg = UserMessage(text=user_prompt)
    try:
        response = await chat.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    # Persist cache
    await llm_cache_col.insert_one({
        "cache_key": cache_key,
        "model": CLAUDE_MODEL,
        "response": response,
        "created_at": datetime.now(timezone.utc),
    })
    return response


def _extract_json(text: str) -> dict:
    """Best-effort JSON extraction from Claude's response."""
    text = text.strip()
    if text.startswith("```"):
        # strip markdown code fence
        first = text.find("\n")
        if first != -1:
            text = text[first + 1:]
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find first { ... last }
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b != -1 and b > a:
            return json.loads(text[a:b+1])
        raise HTTPException(status_code=502, detail=f"LLM returned non-JSON output (truncated): {text[:200]}")


def _serialize(d: dict) -> dict:
    out = dict(d)
    out.pop("_id", None)
    for k in ("created_at", "updated_at", "last_edited_at"):
        if isinstance(out.get(k), datetime):
            out[k] = out[k].isoformat()
    return out


# ════════════════════════════════════════════════════
# CONTENT STUDIO
# ════════════════════════════════════════════════════

VALID_CONTENT_TYPES = {"blog", "email", "social_post", "landing_copy", "press_release", "ad_copy"}
VALID_VOICES = {"professional", "conversational", "authoritative", "empathetic", "witty"}
VALID_LANGS = {"en", "hi", "hinglish"}


class ContentGenRequest(BaseModel):
    brief: str
    content_type: str = "email"
    target_audience: str = "general"
    keywords: List[str] = Field(default_factory=list)
    brand_voice: str = "professional"
    language: str = "en"
    variants_count: int = 3


class DraftSave(BaseModel):
    title: str
    type: str
    brief: str
    variants: List[dict]
    selected_variant: Optional[int] = None
    final_content: Optional[str] = None
    campaign_id: Optional[str] = None


@router.post("/content-studio/generate")
async def content_generate(payload: ContentGenRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    if payload.content_type not in VALID_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid content_type. Allowed: {sorted(VALID_CONTENT_TYPES)}")
    if payload.brand_voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid brand_voice. Allowed: {sorted(VALID_VOICES)}")
    if payload.language not in VALID_LANGS:
        raise HTTPException(status_code=400, detail=f"Invalid language. Allowed: {sorted(VALID_LANGS)}")
    n = max(1, min(payload.variants_count or 3, 5))

    system = (
        "You are LEAMSS Marketing's senior content strategist. "
        "LEAMSS is an Australian immigration & overseas-education consulting firm based in India. "
        "Generate marketing content variants tailored for prospective Indian clients seeking PR/visa/study opportunities in Australia. "
        "Respond ONLY with valid JSON. No markdown, no explanations outside JSON."
    )
    user = (
        f"Generate {n} unique variants of {payload.content_type.upper()} content.\n"
        f"BRIEF: {payload.brief}\n"
        f"AUDIENCE: {payload.target_audience}\n"
        f"KEYWORDS to weave in: {', '.join(payload.keywords) if payload.keywords else '(none specified)'}\n"
        f"BRAND VOICE: {payload.brand_voice}\n"
        f"LANGUAGE: {payload.language} ('hi'=Hindi, 'hinglish'=mix of Hindi+English)\n\n"
        "Return strict JSON in this exact schema:\n"
        "{\n"
        '  "variants": [\n'
        '    {\n'
        '      "variant_number": 1,\n'
        '      "subject_or_headline": "compelling subject/headline",\n'
        '      "body": "full body content (2-5 paragraphs for email/blog, 1-2 sentences for social_post/ad_copy)",\n'
        '      "suggested_image_prompt": "one-sentence image generation prompt that matches the content",\n'
        '      "cta": "primary call-to-action button text (3-6 words)",\n'
        '      "estimated_reading_time_min": 1\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Each variant must be distinctly different in angle (different hook, framing, or pitch). Ensure each is ready-to-publish quality."
    )
    raw = await _llm_call(system, user)
    parsed = _extract_json(raw)
    variants = parsed.get("variants", [])
    for v in variants:
        v["model_used"] = CLAUDE_MODEL
        v["generated_at"] = datetime.now(timezone.utc).isoformat()
    return {"variants": variants[:n], "model": CLAUDE_MODEL}


@router.post("/content-studio/save-draft")
async def save_draft(payload: DraftSave, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    if payload.type not in VALID_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid type")
    draft = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "type": payload.type,
        "brief": payload.brief,
        "variants": payload.variants,
        "selected_variant": payload.selected_variant,
        "final_content": payload.final_content,
        "campaign_id": payload.campaign_id,
        "published": False,
        "published_url": None,
        "created_by": current_user["id"],
        "created_by_name": current_user.get("name"),
        "created_at": datetime.now(timezone.utc),
        "last_edited_at": datetime.now(timezone.utc),
        "audit_log": [{
            "action": "created",
            "actor_id": current_user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
    }
    await drafts_col.insert_one(draft)
    return _serialize(draft)


@router.get("/content-studio/drafts")
async def list_drafts(
    type: Optional[str] = None,
    campaign_id: Optional[str] = None,
    published: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    q: dict = {}
    if type:
        q["type"] = type
    if campaign_id:
        q["campaign_id"] = campaign_id
    if published is not None:
        q["published"] = published
    items = []
    async for d in drafts_col.find(q, {"_id": 0}).sort("created_at", -1):
        items.append(_serialize(d))
    return items


class DraftEdit(BaseModel):
    final_content: Optional[str] = None
    selected_variant: Optional[int] = None
    published: Optional[bool] = None
    published_url: Optional[str] = None
    campaign_id: Optional[str] = None


@router.patch("/content-studio/drafts/{draft_id}")
async def edit_draft(draft_id: str, payload: DraftEdit, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return {"message": "No changes"}
    updates["last_edited_at"] = datetime.now(timezone.utc)
    res = await drafts_col.update_one(
        {"id": draft_id},
        {"$set": updates, "$push": {"audit_log": {
            "action": "edited",
            "actor_id": current_user["id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fields": list(updates.keys()),
        }}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"message": "Updated", "fields": list(updates.keys())}


@router.post("/content-studio/drafts/{draft_id}/regenerate")
async def regenerate_draft(draft_id: str, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    d = await drafts_col.find_one({"id": draft_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    # Re-run generation using the original brief
    req = ContentGenRequest(
        brief=d.get("brief", ""),
        content_type=d.get("type", "email"),
        target_audience="general",
        keywords=[],
        brand_voice="professional",
        language="en",
        variants_count=3,
    )
    result = await content_generate(req, current_user)
    await drafts_col.update_one(
        {"id": draft_id},
        {"$set": {"variants": result["variants"], "last_edited_at": datetime.now(timezone.utc)},
         "$push": {"audit_log": {"action": "regenerated", "actor_id": current_user["id"],
                                 "timestamp": datetime.now(timezone.utc).isoformat()}}},
    )
    return result


# ════════════════════════════════════════════════════
# SEO TOOLS
# ════════════════════════════════════════════════════

class KeywordResearch(BaseModel):
    seed_keyword: str


@router.post("/seo/keyword-research")
async def seo_keyword_research(payload: KeywordResearch, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    system = "You are an SEO research analyst. Reply ONLY with valid JSON."
    user = (
        f"For the seed keyword '{payload.seed_keyword}', return 15 related keywords with difficulty estimates "
        "and search intents. Strict JSON schema:\n"
        "{\n"
        '  "keywords": [\n'
        '    {"keyword": "...", "difficulty_pct": 0-100, "intent": "informational|navigational|transactional|commercial", "monthly_searches_estimate": int}\n'
        "  ]\n"
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


class MetaOptimize(BaseModel):
    page_url: Optional[str] = None
    raw_content: Optional[str] = None
    target_keywords: List[str] = Field(default_factory=list)


@router.post("/seo/meta-optimize")
async def seo_meta_optimize(payload: MetaOptimize, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    if not payload.page_url and not payload.raw_content:
        raise HTTPException(status_code=400, detail="Provide page_url OR raw_content")
    content = payload.raw_content or f"(content from {payload.page_url})"
    system = "You are an SEO meta-tag optimization specialist. Reply ONLY with valid JSON."
    user = (
        f"For the following content snippet, generate 3 optimized meta tag combinations.\n"
        f"CONTENT: {content[:2000]}\n"
        f"TARGET KEYWORDS: {', '.join(payload.target_keywords) if payload.target_keywords else '(infer)'}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "options": [\n'
        '    {"meta_title": "<=60 chars", "meta_description": "<=155 chars", "h1": "<=70 chars", "rationale": "why this is optimised"}\n'
        "  ]\n"
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


class InternalLinkRequest(BaseModel):
    page_content: str
    available_pages: List[dict] = Field(default_factory=list)  # [{url, title, summary}]


@router.post("/seo/internal-link-suggestions")
async def seo_internal_link(payload: InternalLinkRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    system = "You are an internal linking strategist. Reply ONLY with valid JSON."
    pages_brief = json.dumps(payload.available_pages or [{"url": "/au/atlas", "title": "AU State Atlas", "summary": "Per-state vacancy data"}])
    user = (
        f"Given the page content below, suggest 5-7 internal link insertions from available pages.\n"
        f"PAGE CONTENT (excerpt): {payload.page_content[:1500]}\n"
        f"AVAILABLE PAGES: {pages_brief}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "suggestions": [\n'
        '    {"anchor_text": "...", "target_url": "...", "placement_hint": "after which sentence/paragraph", "relevance_score": 0-10}\n'
        "  ]\n"
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


# ════════════════════════════════════════════════════
# AEO TOOLS (Answer Engine Optimization)
# ════════════════════════════════════════════════════

class FAQSchemaRequest(BaseModel):
    questions: List[str]
    topic: Optional[str] = ""


@router.post("/aeo/faq-schema-generate")
async def aeo_faq_schema(payload: FAQSchemaRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    if not payload.questions:
        raise HTTPException(status_code=400, detail="At least one question required")
    system = "You are an AEO/Schema.org expert. Reply ONLY with valid JSON."
    user = (
        f"For the following questions about '{payload.topic or 'LEAMSS immigration services'}', "
        "generate concise, helpful answers (each 2-4 sentences) AND wrap them in valid Schema.org FAQPage JSON-LD.\n\n"
        f"QUESTIONS: {json.dumps(payload.questions)}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "answers": [{"q": "...", "a": "..."}],\n'
        '  "json_ld": {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [...]}\n'
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


class VoiceSearchRequest(BaseModel):
    content: str


@router.post("/aeo/voice-search-optimize")
async def aeo_voice_search(payload: VoiceSearchRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    system = "You are a voice-search optimization specialist. Reply ONLY with valid JSON."
    user = (
        f"Optimize the following content for voice search.\n"
        f"CONTENT: {payload.content[:1500]}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "natural_language_phrasings": ["sentence-style answers ready for Siri/Alexa"],\n'
        '  "question_variants": ["Who/What/Why/How/Where questions users would ask"],\n'
        '  "conversational_tone_rewrite": "the same content rewritten conversationally"\n'
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


class FeaturedSnippetRequest(BaseModel):
    topic: str


@router.post("/aeo/featured-snippet-target")
async def aeo_featured_snippet(payload: FeaturedSnippetRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    system = "You are a featured-snippet optimization expert. Reply ONLY with valid JSON."
    user = (
        f"For the topic '{payload.topic}', identify the most likely featured-snippet type "
        "(paragraph / list / table / definition / step-by-step) and generate draft content ready to be inserted.\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "best_snippet_type": "paragraph|list|table|definition|steps",\n'
        '  "rationale": "why this type",\n'
        '  "draft_content": "ready-to-use HTML (with <ol>/<table>/<p> as appropriate)",\n'
        '  "target_query": "the search query this snippet would win"\n'
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


# ════════════════════════════════════════════════════
# GEO TOOLS (Generative Engine Optimization)
# ════════════════════════════════════════════════════

class GEOAuditRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None


@router.post("/geo/llm-content-audit")
async def geo_llm_audit(payload: GEOAuditRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    if not payload.url and not payload.content:
        raise HTTPException(status_code=400, detail="Provide url OR content")
    content = payload.content or f"(content from {payload.url})"
    system = "You are a Generative Engine Optimization (GEO) auditor. Reply ONLY with valid JSON."
    user = (
        f"Audit the following content for LLM-citation worthiness (how likely ChatGPT/Claude/Perplexity cite it).\n"
        f"CONTENT: {content[:2500]}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "clarity_score": 1-10,\n'
        '  "citation_worthiness_score": 1-10,\n'
        '  "structure_quality_score": 1-10,\n'
        '  "factual_specificity_score": 1-10,\n'
        '  "overall_score": 1-10,\n'
        '  "strengths": ["..."],\n'
        '  "improvements": ["concrete actionable suggestions"],\n'
        '  "recommended_additions": ["e.g., add a TL;DR, add a numbered list, add date stamps, add source citations"]\n'
        "}"
    )
    raw = await _llm_call(system, user)
    parsed = _extract_json(raw)
    # Persist for analytics
    await geo_runs_col.insert_one({
        "id": str(uuid.uuid4()),
        "type": "llm_content_audit",
        "input": {"url": payload.url, "content_excerpt": (content or "")[:300]},
        "result": parsed,
        "actor_id": current_user["id"],
        "created_at": datetime.now(timezone.utc),
    })
    return parsed


class StructuredDataRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None


@router.post("/geo/structured-data-validator")
async def geo_structured_data(payload: StructuredDataRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    if not payload.url and not payload.html:
        raise HTTPException(status_code=400, detail="Provide url OR html")
    snippet = payload.html or f"(fetch {payload.url})"
    system = "You are a Schema.org compliance validator. Reply ONLY with valid JSON."
    user = (
        f"Analyze the following HTML snippet for JSON-LD / microdata Schema.org compliance.\n"
        f"HTML (excerpt): {snippet[:2500]}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "found_schemas": [{"type": "Article|Organization|FAQ|...", "valid": true|false}],\n'
        '  "errors": ["..."],\n'
        '  "warnings": ["..."],\n'
        '  "missing_recommended_schemas": ["Organization", "BreadcrumbList", ...],\n'
        '  "compliance_score": 1-10\n'
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)


@router.get("/geo/llm-crawl-tracker")
async def geo_crawl_tracker(current_user: dict = Depends(get_current_user)):
    """Placeholder — would parse access logs for GPTBot/ClaudeBot/PerplexityBot UAs."""
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    # Stub data — real implementation would scan nginx/uvicorn logs
    return {
        "tracking_period": "last_7_days",
        "bots_detected": [
            {"user_agent": "GPTBot", "visits": 0, "last_seen": None},
            {"user_agent": "ClaudeBot", "visits": 0, "last_seen": None},
            {"user_agent": "PerplexityBot", "visits": 0, "last_seen": None},
            {"user_agent": "CCBot", "visits": 0, "last_seen": None},
        ],
        "note": "Log integration arrives in Slice 4 — IT department tools.",
    }


class CitationOptimizeRequest(BaseModel):
    content: str


@router.post("/geo/citation-optimizer")
async def geo_citation_optimizer(payload: CitationOptimizeRequest, current_user: dict = Depends(get_current_user)):
    if not _is_marketing_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Marketing/admin only")
    system = "You are a GEO citation-quality optimizer. Reply ONLY with valid JSON."
    user = (
        f"Suggest concrete improvements to make this content more 'quotable' by LLMs.\n"
        f"CONTENT: {payload.content[:2000]}\n\n"
        "Strict JSON schema:\n"
        "{\n"
        '  "issues_found": ["..."],\n'
        '  "suggestions": [\n'
        '    {"issue": "...", "fix": "concrete rewrite or addition", "expected_impact": "high|medium|low"}\n'
        '  ],\n'
        '  "rewritten_intro_paragraph": "an LLM-friendly opening 2-3 sentences",\n'
        '  "key_facts_to_add": ["1-line factual statements LLMs love to cite"]\n'
        "}"
    )
    raw = await _llm_call(system, user)
    return _extract_json(raw)
