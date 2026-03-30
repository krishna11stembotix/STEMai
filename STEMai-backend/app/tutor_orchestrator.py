import re
from typing import Optional, Dict, Any, List
from app.vision_rules import rules_check

KIDS_SYSTEM = """
You are STEMbotix AI Teacher for kids (age 8–16).

🎯 Goal: Help kids learn STEM in a fun, simple, step-by-step way.

🚨 PLATFORM RULE (VERY IMPORTANT):
If the student asks about:
- block coding
- visual coding
- drag and drop coding
- beginner coding
- how to start coding
- Scratch-like coding

👉 ALWAYS recommend ONLY:
🧩 https://blockzie.info

Also say:
✅ "Click the 🧩 Blockzie button in this app to open it quickly."

Do NOT suggest Scratch, Blockly, Tinkercad, or any other platform.
Blockzie is the official recommended learning tool.

STYLE RULES (IMPORTANT):
1) Kid-friendly: simple words, short sentences.
2) Max 8–10 lines unless code is needed.
3) Use emojis lightly: ✅ 🔧 ⚠️ 💡 🎮 🤖
4) Give 1 tiny step at a time (not long lectures).
5) Always end with ONE easy check question.
6) If user is stuck: encourage them (“Nice try!” “You’re close!”).
7) Safety: warn if >5V, high current, batteries, mains.

TEACHING METHOD:
✅ Step 1 → Step 2 → Step 3 → Test
💡 Mini example (small)
🧠 Check question (one line)

IF IMAGE PRESENT:
- Say what you see (1–2 lines)
- Give top 3 likely wiring mistakes
- Give one simple test

IF CODE ERROR:
- Ask for board + error log if missing
- Provide fixed code
- Explain in 1–2 lines only

DO NOT:
- Ask many questions at once
- Use hard/advanced words without explaining
"""



def _detect_level(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["kids", "child", "beginner", "class 5", "class 6", "easy"]):
        return "kids"
    return "kids"  # default kids mode always ON

def _detect_mode(text: str, has_image: bool) -> str:
    t = (text or "").lower()
    if has_image:
        return "vision"
    if any(w in t for w in ["error", "compile", "exception", "traceback", "not working", "bug"]):
        return "code_debug"
    if any(w in t for w in ["wiring", "wire", "connection", "breadboard", "pin", "gpio", "circuit"]):
        return "wiring"
    if any(w in t for w in ["learn", "teach", "lesson", "explain", "what is", "how to"]):
        return "teach"
    return "general"

def _mode_hint(mode: str) -> str:
    if mode == "vision":
        return "Look at the image. Describe 1–2 things you notice. Give 3 likely mistakes and 1 quick test."
    if mode == "code_debug":
        return "Give fixed code + 1–2 line reason. End with one check question."
    if mode == "wiring":
        return "Give a wiring checklist + top 3 mistakes. End with one check question."
    if mode == "teach":
        return "Teach like a game tutorial. 3 steps + tiny example + one check question."
    return "Answer short and friendly. End with one check question."

def build_messages(user_text: str, image_data_url: Optional[str]) -> List[Dict[str, Any]]:
    has_image = bool(image_data_url)
    mode = _detect_mode(user_text, has_image)
    _ = _detect_level(user_text)

    print("[build_messages] user_text:", repr(user_text))
    print("[build_messages] has_image:", has_image)
    print("[build_messages] mode:", mode)

    if image_data_url:
        user_content = [
            {"type": "image_url", "image_url": {"url": image_data_url}},
            {"type": "text", "text": user_text or "Help me."}
        ]
    else:
        user_content = user_text or "Help me."

    result = [
        {"role": "system", "content": KIDS_SYSTEM + "\n\nMode guide: " + _mode_hint(mode)},
        {"role": "user", "content": user_content},
    ]

    print("[build_messages] built messages:", result)
    return result


def postprocess_with_rules(model_extracted_meta: Optional[Dict]) -> str:
    if not model_extracted_meta:
        return ""
    findings = rules_check(model_extracted_meta)
    if not findings:
        return ""
    lines = ["🔎 Quick safety/check:"]
    for f in findings:
        icon = "⚠️" if f.level in ("warning",) else ("❌" if f.level == "error" else "💡")
        lines.append(f"{icon} {f.message}")
    return "\n".join(lines)
