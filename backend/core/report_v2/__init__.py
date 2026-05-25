"""Phase 8 — Premium PDF Renderer v2 (WeasyPrint + Jinja2).

Replaces the legacy ReportLab renderer with a magazine-quality HTML→PDF
pipeline using the official LEAMSS brand palette extracted from the logo
(teal · warm orange · brand red — no blue/indigo).
"""

from .renderer import render_pdf_v2  # noqa: F401
