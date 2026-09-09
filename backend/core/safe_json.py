"""Resilient JSON parsing utilities for LLM / AI responses.

Handles:
- Thinking blocks (<think>...</think>, <thought>...</thought>)
- Markdown fences (```json ... ``` or ``` ... ```)
- Unescaped control characters and newlines inside strings
- Trailing commas before closing braces/brackets
- Truncated JSON via bracket completion and jiter partial parsing
- Best-effort extraction of nested dictionaries and lists
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Try importing jiter for ultra-fast and partial-tolerant parsing
try:
    import jiter
    _HAS_JITER = True
except ImportError:
    _HAS_JITER = False


def _clean_text_fences(raw: str) -> str:
    """Strip reasoning blocks and markdown fences."""
    text = (raw or "").strip()
    # Strip <think>...</think> or <thought>...</thought> (case-insensitive, DOTALL)
    text = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", text, flags=re.IGNORECASE)
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


def _sanitize_common_json_issues(s: str) -> str:
    """Remove control characters and trailing commas."""
    # Remove control characters except standard whitespace (keep \t, \n, \r)
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)
    # Remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _fix_unescaped_newlines(s: str) -> str:
    """Replace literal unescaped newlines inside quotes."""
    def _replace_inner(match: re.Match) -> str:
        content = match.group(1)
        escaped = content.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
        return f': "{escaped}"'

    return re.sub(r':\s*"([^"\\]*(?:\\.[^"\\]*)*?)"', _replace_inner, s)


def safe_json_loads(
    raw: str,
    default: Optional[Union[Dict[str, Any], List[Any], Callable[[], Any]]] = None,
    allow_partial: bool = True,
) -> Any:
    """Parse JSON from an AI response with multi-layer fault tolerance.

    Args:
        raw: Raw AI response string.
        default: Fallback return value if all parsing attempts fail.
                 If default is None and parsing fails, raises ValueError.
        allow_partial: Attempt jiter partial parsing or bracket repair if True.

    Returns:
        Parsed dict, list, or primitive.
    """
    clean = _clean_text_fences(raw)
    if not clean:
        if default is not None:
            return default() if callable(default) else default
        raise ValueError("Empty string provided to safe_json_loads")

    # Strategy 1: Direct loads with strict=False (allows control chars inside strings)
    try:
        return json.loads(clean, strict=False)
    except Exception:
        pass

    # Strategy 2: Remove non-whitespace control characters & trailing commas
    sanitized = _sanitize_common_json_issues(clean)
    try:
        return json.loads(sanitized, strict=False)
    except Exception:
        pass

    # Strategy 3: Slice between first { and last } (or first [ and last ])
    first_brace = sanitized.find("{")
    last_brace = sanitized.rfind("}")
    first_bracket = sanitized.find("[")
    last_bracket = sanitized.rfind("]")

    target_sub = None
    if first_brace != -1 and last_brace > first_brace:
        if first_bracket != -1 and first_bracket < first_brace and last_bracket > last_brace:
            target_sub = sanitized[first_bracket:last_bracket + 1]
        else:
            target_sub = sanitized[first_brace:last_brace + 1]
    elif first_bracket != -1 and last_bracket > first_bracket:
        target_sub = sanitized[first_bracket:last_bracket + 1]

    if target_sub:
        try:
            return json.loads(target_sub, strict=False)
        except Exception:
            pass

        # Strategy 3b: Fix unescaped newlines inside strings
        fixed_newlines = _fix_unescaped_newlines(target_sub)
        try:
            return json.loads(fixed_newlines, strict=False)
        except Exception:
            pass

    # Strategy 4: Try jiter partial mode if available
    sub_candidate = target_sub or sanitized
    if allow_partial and _HAS_JITER:
        try:
            parsed = jiter.from_json(sub_candidate.encode("utf-8", errors="replace"), partial_mode="trailing-strings")
            if parsed is not None:
                return parsed
        except Exception:
            pass

    # Strategy 5: Truncation recovery by testing closing brackets
    if allow_partial and target_sub:
        tails = [
            "\n  }\n}",
            "\n}",
            '"\n  }\n}',
            '"}\n  }\n}',
            "}\n  }\n}",
            '"]}',
            "]}",
            "\n  ]\n}",
            "\n]",
            '"}',
            "}}",
            '"\n}',
        ]
        for tail in tails:
            try:
                return json.loads(target_sub + tail, strict=False)
            except Exception:
                pass

        # Check if truncated mid-array after a complete object
        last_obj = target_sub.rfind("},")
        if last_obj != -1:
            for tail in ["\n  ]\n}", "\n  }\n}", "\n  ]"]:
                try:
                    return json.loads(target_sub[:last_obj + 1] + tail, strict=False)
                except Exception:
                    pass

    # Strategy 6: Extract individual JSON objects from the text
    recovered_items = []
    pos = 0
    while pos < len(sanitized):
        s_start = sanitized.find("{", pos)
        if s_start == -1:
            break
        depth = 0
        s_end = -1
        for i in range(s_start, len(sanitized)):
            if sanitized[i] == "{":
                depth += 1
            elif sanitized[i] == "}":
                depth -= 1
                if depth == 0:
                    s_end = i
                    break
        if s_end != -1:
            block = sanitized[s_start:s_end + 1]
            try:
                obj = json.loads(block, strict=False)
                if isinstance(obj, dict):
                    # If this block itself has suggestions/occupations list
                    for k in ("suggestions", "occupations", "records", "items"):
                        if k in obj and isinstance(obj[k], list) and obj[k]:
                            return obj
                    recovered_items.append(obj)
            except Exception:
                pass
            pos = s_start + 1
        else:
            pos = s_start + 1

    if recovered_items:
        useful = [o for o in recovered_items if any(k in o for k in ("code", "title", "anzsco", "occupation", "step_name", "degree"))]
        if useful:
            return {"suggestions": useful, "records": useful, "occupations": useful}

    if default is not None:
        return default() if callable(default) else default

    raise ValueError(f"Could not parse JSON response from AI: {clean[:200]}")
