import re
import json
from typing import Any
def _extract_first_json_object(text: str) -> str:
    """
    Robustly extracts the first JSON object from model output.
    Handles markdown fences and extra text around JSON.
    """
    if not text:
        raise ValueError("Empty model response")

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "```")
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # direct parse first
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        pass

    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(cleaned)):
        ch = cleaned[i]

        if escape:
            escape = False
            continue

        if ch == "\\":
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start:i + 1]
                json.loads(candidate)  # validate
                return candidate

    raise ValueError("Could not extract valid JSON object")


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _fast_voice_text(full_text: str, max_chars: int = 220) -> str:
    if not full_text:
        return "Okay!"
    t = full_text.strip()
    first_line = (t.split("\n")[0] or "").strip()
    if not first_line:
        first_line = t.replace("\n", " ").strip()
    return (first_line[:max_chars].strip() or "Okay!")


def _pick_voice(lang: str) -> str:
    lang = (lang or "en").lower()
    if lang.startswith("hi"):
        return "hi-IN-MadhurNeural"
    return "en-IN-PrabhatNeural"
