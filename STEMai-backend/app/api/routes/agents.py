from fastapi import APIRouter
import json

from app.models.schemas import MakeReq
from app.core.utils import _extract_first_json_object
from app.core.config import MODEL_TEXT
from app.router_openrouter import OpenRouterClient
router_client = OpenRouterClient()

# ✅ Blockzie + DSL
from app.stemx_text_to_xml import dsl_to_blockzie_xml
from app.blockzie_agent import load_xml_program
router = APIRouter()

MAKE_SYSTEM = """
You are STEMbotix Blockzie Builder.
Return ONLY valid JSON. No markdown. No extra text.

Schema:
{
  "title": "string",
  "description": "string",
  "blocks_dsl": ["..."],
  "notes": ["..."]
}

Rules:
- blocks_dsl must be a simple Scratch-like DSL.
- Keep it small and beginner friendly.

Allowed DSL (examples):
- when green_flag:
- forever:
- wait 1
- move 10 steps
- move -10 steps
- turn right 15 degrees
- say "Hello"
"""


@router.post("/agent/make")
async def agent_make(req: MakeReq):
    user_prompt = (req.prompt or "").strip()
    if not user_prompt:
        return {"ok": False, "error": "Missing prompt"}

    raw = await router_client.chat(
        model=MODEL_TEXT,
        messages=[
            {"role": "system", "content": MAKE_SYSTEM},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )

    try:
        plan = json.loads(_extract_first_json_object(raw))
    except Exception:
        return {"ok": False, "error": "LLM did not return valid JSON", "raw": raw}

    dsl = plan.get("blocks_dsl", [])
    xml = dsl_to_blockzie_xml(dsl, title=plan.get("title", "Project"))

    inject_res = await load_xml_program(
        xml,
        auto_start=req.auto_start,
        mode="inject"
    )

    return {
        "ok": True,
        "plan": plan,
        "inject": inject_res
    }
