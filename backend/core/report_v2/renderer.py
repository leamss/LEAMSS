"""Phase 8 — Premium HTML→PDF Renderer (WeasyPrint + Jinja2).

Renders an Assessment Report snapshot into a magazine-quality PDF using
official LEAMSS brand colors (teal · warm orange · brand red).

Public entrypoint: ``render_pdf_v2(snapshot) -> bytes``

The function signature mirrors the legacy ReportLab ``render_pdf`` so
``routers/assessment_reports.py`` can switch implementations with zero
changes elsewhere.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any, Dict

# On Windows, register native library directories for Pango/Cairo/GLib
if sys.platform == "win32":
    _DLL_CANDIDATES = [
        Path(__file__).resolve().parent.parent.parent / "bin" / "weasyprint" / "onedir" / "weasyprint" / "_internal",
        Path(__file__).resolve().parent.parent.parent / "bin" / "_internal",
    ]
    for _cand in _DLL_CANDIDATES:
        if _cand.exists() and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(_cand))
                break
            except Exception:
                pass

from jinja2 import Environment, FileSystemLoader, select_autoescape
try:
    from weasyprint import HTML, CSS
except Exception:
    HTML, CSS = None, None

logger = logging.getLogger(__name__)

# ─── Paths ──────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_TEMPLATES_DIR = _HERE / "templates"
_CSS_PATH = _HERE / "css" / "theme.css"
_ASSETS_DIR = _HERE.parent.parent / "assets"
_LOGO_PATH = _ASSETS_DIR / "leamss-logo.png"

# ─── Jinja env (singleton) ──────────────────────────────────────────────────
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _data_uri(path: Path) -> str | None:
    """Encode an image file as a base64 data URI for inline embedding."""
    if not path.exists():
        return None
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _load_css() -> str:
    """Read the theme CSS once per call (small file, no caching needed)."""
    try:
        return _CSS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Theme CSS missing at %s", _CSS_PATH)
        return ""


def render_pdf_v2(snapshot: Dict[str, Any]) -> bytes:
    """Render the LEAMSS Assessment Report PDF using the v2 (HTML→PDF) engine.

    Args:
        snapshot: Frozen snapshot dict (same shape produced by
            ``_build_snapshot`` in ``routers/assessment_reports.py``).
            Must include ``render_tier`` (teaser | full | proposal).

    Returns:
        PDF bytes ready to stream or persist.
    """
    snap = dict(snapshot)  # shallow copy — never mutate caller's payload
    snap.setdefault("render_tier", "full")

    css_text = _load_css()
    logo_uri = _data_uri(_LOGO_PATH)

    template = _env.get_template("base.html")
    html_str = template.render(
        snap=snap,
        css=css_text,
        logo_data_uri=logo_uri,
    )

    if HTML is None:
        logger.warning("WeasyPrint is not installed or missing native libraries. Falling back to ReportLab (v1) renderer.")
        from core.report_renderer import render_pdf as render_pdf_v1
        return render_pdf_v1(snap)

    try:
        base_url = str(_HERE)  # so relative @font-face url() resolves
        pdf_bytes = HTML(string=html_str, base_url=base_url).write_pdf()
        if not pdf_bytes:
            raise ValueError("WeasyPrint returned empty PDF bytes")
        logger.info(
            "Phase 8 PDF v2 rendered · snapshot=%s · tier=%s · size=%d bytes",
            snap.get("snapshot_id"), snap.get("render_tier"), len(pdf_bytes),
        )
        return pdf_bytes
    except Exception as e:
        logger.warning("WeasyPrint rendering failed (%s). Falling back to ReportLab (v1) renderer.", e)
        from core.report_renderer import render_pdf as render_pdf_v1
        return render_pdf_v1(snap)


__all__ = ["render_pdf_v2"]
