"""Phase 9.3 — Hybrid LLM Model Router for LEAMSS.

Single source of truth for which Claude model handles which task.

Decision matrix:
  • Sonnet 4.6 (default): quality-critical, low-volume tasks
       - Proposal generation, Country Guide drafting
       - Resume parsing (complex extraction, multi-field)
       - Eligibility AI reasoning
       - KB AI polishing / verification
       - Occupation Master AI seeding
       - Admin AI-Extract (high-stakes)
       - Workflow Builder

  • Haiku 4.5 (NEW): high-volume, low-stakes, simple structured-output tasks
       - Occupation typeahead suggester (Smart Sales Helper)
       - Step-document AI hints
       - General AI Intelligence helpers (short-form)

  • Opus 4.6 / 4.8: premium proposals only (existing path, untouched)

Both Haiku & Sonnet use the same Emergent Universal Key via the
`emergentintegrations` library. Switching models is a single string change.

Cost reference (Anthropic Feb 2026):
  • Sonnet 4.6: ~$3  / 1M input + $15 / 1M output
  • Haiku 4.5:  ~$0.80 / 1M input + $4 / 1M output  (≈4x cheaper, ≈2x faster)

Usage:
    from core.ai_models import MODEL_FOR

    chat = LlmChat(...).with_model("anthropic", MODEL_FOR["occupation_suggester"])
"""

# ─── Task → Model mapping ────────────────────────────────────────────────────
SONNET = "claude-sonnet-4-6"
HAIKU  = "claude-haiku-4-5-20251001"
OPUS   = "claude-opus-4-6"

# Each key is a logical task name; agent code references it by string
MODEL_FOR = {
    # ── HAIKU 4.5 (light, high-frequency tasks) ─────────────────────────────
    "occupation_suggester":     HAIKU,   # Sales — typeahead-style suggestions
    "step_document_helper":     HAIKU,   # Sales — quick doc hints
    "ai_intelligence_quick":    HAIKU,   # Generic short helpers
    "atlas_auto_suggest":       HAIKU,   # Phase 10.3 — free-text → NOC + PNP/EE ranking
    "eligibility_narrative":    HAIKU,   # Narrative for deterministic eligibility scores
    # ── SONNET 4.6 (quality-critical tasks) ─────────────────────────────────
    "resume_extractor":         SONNET,  # Multi-section structured extraction
    "proposal_standard":        SONNET,  # Client-facing proposals
    "country_guide":            SONNET,  # Long-form authored content
    "occupation_master_seed":   SONNET,  # 4-digit ANZSCO master data generation
    "kb_ai_polish":             SONNET,  # KB content polishing
    "ai_verification":          SONNET,  # Verification reasoning
    "ai_workflow_builder":      SONNET,  # Multi-step workflow plans
    "eligibility_reasoning":    SONNET,  # Mission-critical scoring AI
    "ai_extract_admin":         SONNET,  # Admin VETASSESS / state nomination extraction
    # ── OPUS 4.6 (premium only) ─────────────────────────────────────────────
    "proposal_premium":         OPUS,    # Premium proposals (existing flag)
}


def model_for(task: str) -> str:
    """Returns the model ID for a given task name. Falls back to Sonnet."""
    return MODEL_FOR.get(task, SONNET)
