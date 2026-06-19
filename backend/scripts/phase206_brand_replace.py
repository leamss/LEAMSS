"""Phase 20.6 — Brand token replacement script.

Replaces non-brand Tailwind colors (indigo/purple/violet/blue) with `leamss.*`
tokens across priority frontend files. Idempotent — re-running has no effect.

Run: cd /app && python3 backend/scripts/phase206_brand_replace.py
"""
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Tailwind class → leamss token mapping.
# Order matters: process longest/most-specific first.
COLOR_MAP: List[Tuple[str, str]] = [
    # Gradients (must come BEFORE single-color replacements)
    (r"from-indigo-(50|100)\b", "from-leamss-teal_50"),
    (r"from-indigo-(300|400|500|600|700|800|900)\b", "from-leamss-teal"),
    (r"to-indigo-(50|100)\b", "to-leamss-teal_50"),
    (r"to-indigo-(300|400|500|600|700|800|900)\b", "to-leamss-teal"),
    (r"via-indigo-(50|100)\b", "via-leamss-teal_50"),
    (r"via-indigo-(300|400|500|600|700|800|900)\b", "via-leamss-teal"),
    (r"from-purple-(50|100|200)\b", "from-leamss-orange_50"),
    (r"from-purple-(300|400|500|600|700|800|900)\b", "from-leamss-orange"),
    (r"to-purple-(50|100|200)\b", "to-leamss-orange_50"),
    (r"to-purple-(300|400|500|600|700|800|900)\b", "to-leamss-orange"),
    (r"from-blue-(50|100|200)\b", "from-leamss-teal_50"),
    (r"from-blue-(300|400|500|600|700|800|900)\b", "from-leamss-teal"),
    (r"to-blue-(50|100|200)\b", "to-leamss-teal_50"),
    (r"to-blue-(300|400|500|600|700|800|900)\b", "to-leamss-teal"),
    (r"from-violet-(50|100|200)\b", "from-leamss-orange_50"),
    (r"from-violet-(300|400|500|600|700|800|900)\b", "from-leamss-orange"),
    (r"to-violet-(50|100|200)\b", "to-leamss-orange_50"),
    (r"to-violet-(300|400|500|600|700|800|900)\b", "to-leamss-orange"),

    # bg-{color}-{shade} including /opacity suffix
    (r"\bbg-indigo-(50|100|200)(\b|\/[0-9]+)", r"bg-leamss-teal_50\2"),
    (r"\bbg-indigo-(300|400|500|600|700|800|900)(\b|\/[0-9]+)", r"bg-leamss-teal\2"),
    (r"\bbg-purple-(50|100|200)(\b|\/[0-9]+)", r"bg-leamss-orange_50\2"),
    (r"\bbg-purple-(300|400|500|600|700|800|900)(\b|\/[0-9]+)", r"bg-leamss-orange\2"),
    (r"\bbg-blue-(50|100|200)(\b|\/[0-9]+)", r"bg-leamss-teal_50\2"),
    (r"\bbg-blue-(300|400|500|600|700|800|900)(\b|\/[0-9]+)", r"bg-leamss-teal\2"),
    (r"\bbg-violet-(50|100|200)(\b|\/[0-9]+)", r"bg-leamss-orange_50\2"),
    (r"\bbg-violet-(300|400|500|600|700|800|900)(\b|\/[0-9]+)", r"bg-leamss-orange\2"),

    # text-{color}-{shade}
    (r"\btext-indigo-(50|100|200|300|400|500|600|700|800|900)\b", "text-leamss-teal"),
    (r"\btext-purple-(50|100|200|300|400|500|600|700|800|900)\b", "text-leamss-orange"),
    (r"\btext-blue-(50|100|200|300|400|500|600|700|800|900)\b", "text-leamss-teal"),
    (r"\btext-violet-(50|100|200|300|400|500|600|700|800|900)\b", "text-leamss-orange"),

    # border-{color}-{shade}
    (r"\bborder-indigo-(50|100|200|300)\b", "border-leamss-teal_50"),
    (r"\bborder-indigo-(400|500|600|700|800|900)\b", "border-leamss-teal"),
    (r"\bborder-purple-(50|100|200|300)\b", "border-leamss-orange_50"),
    (r"\bborder-purple-(400|500|600|700|800|900)\b", "border-leamss-orange"),
    (r"\bborder-blue-(50|100|200|300)\b", "border-leamss-teal_50"),
    (r"\bborder-blue-(400|500|600|700|800|900)\b", "border-leamss-teal"),
    (r"\bborder-violet-(400|500|600|700|800|900)\b", "border-leamss-orange"),
    (r"\bborder-l-indigo-(\d+)\b", "border-l-leamss-teal"),
    (r"\bborder-l-purple-(\d+)\b", "border-l-leamss-orange"),
    (r"\bborder-l-blue-(\d+)\b", "border-l-leamss-teal"),
    (r"\bborder-l-violet-(\d+)\b", "border-l-leamss-orange"),

    # hover variants
    (r"\bhover:bg-indigo-(50|100|200)\b", "hover:bg-leamss-teal_50"),
    (r"\bhover:bg-indigo-(300|400|500|600|700|800|900)\b", "hover:bg-leamss-teal"),
    (r"\bhover:text-indigo-(\d+)\b", "hover:text-leamss-teal"),
    (r"\bhover:border-indigo-(\d+)\b", "hover:border-leamss-teal"),
    (r"\bhover:bg-purple-(50|100|200)\b", "hover:bg-leamss-orange_50"),
    (r"\bhover:bg-purple-(300|400|500|600|700|800|900)\b", "hover:bg-leamss-orange"),
    (r"\bhover:bg-blue-(50|100|200)\b", "hover:bg-leamss-teal_50"),
    (r"\bhover:bg-blue-(300|400|500|600|700|800|900)\b", "hover:bg-leamss-teal"),
    (r"\bhover:text-blue-(\d+)\b", "hover:text-leamss-teal"),

    # ring-{color}-{shade}
    (r"\bring-indigo-(\d+)\b", "ring-leamss-teal"),
    (r"\bring-purple-(\d+)\b", "ring-leamss-orange"),
    (r"\bring-blue-(\d+)\b", "ring-leamss-teal"),
    (r"\bfocus:ring-indigo-(\d+)\b", "focus:ring-leamss-teal"),
    (r"\bfocus:ring-blue-(\d+)\b", "focus:ring-leamss-teal"),
]

# Priority files (Phase 20.6 G3)
PRIORITY_FILES = [
    "frontend/src/pages/Login.jsx",
    "frontend/src/pages/AIWorkflowBuilder.jsx",
    "frontend/src/pages/admin/VerificationHub.jsx",
    "frontend/src/pages/admin/AuthoritiesAdmin.jsx",
    "frontend/src/components/admin/AuthorityHealthCard.jsx",
    "frontend/src/components/admin/AuthorityEditTimeline.jsx",
    "frontend/src/components/admin/RecentImportsPanel.jsx",
    "frontend/src/pages/admin/ProductsManager.jsx",
    "frontend/src/pages/admin/DataImportHub.jsx",
    "frontend/src/pages/sales/OccupationDetail.jsx",
    "frontend/src/components/sales/PreAssessmentReportButton.jsx",
]


def apply(text: str) -> Tuple[str, int]:
    total = 0
    for pat, repl in COLOR_MAP:
        new_text, n = re.subn(pat, repl, text)
        if n:
            total += n
        text = new_text
    return text, total


def main():
    base = Path("/app")
    out = []
    for rel in PRIORITY_FILES:
        p = base / rel
        if not p.exists():
            out.append((rel, "MISSING", 0))
            continue
        original = p.read_text()
        new, n = apply(original)
        if n > 0 and new != original:
            p.write_text(new)
            out.append((rel, "PATCHED", n))
        else:
            out.append((rel, "no-change", 0))
    # Report
    total_subs = sum(n for _, _, n in out)
    print(f"=== Phase 20.6 brand replace ===")
    for rel, status, n in out:
        print(f"  {status:9s} | {n:3d} subs | {rel}")
    print(f"TOTAL substitutions: {total_subs} across {sum(1 for _,s,_ in out if s=='PATCHED')} files")


if __name__ == "__main__":
    main()
