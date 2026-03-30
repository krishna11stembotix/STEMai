# app/api/routes/simulator.py
from fastapi import APIRouter
import json

from app.models.schemas import SimAIReq
from app.ai_planner import build_agentic_prompt, validate_project_json
from app.core.utils import _extract_first_json_object
from app.core.config import MODEL_TEXT
from app.router_openrouter import OpenRouterClient

router_client = OpenRouterClient()
router = APIRouter()


@router.post("/sim_ai")
# FIX: was "/api/sim_ai" — Vercel strips the /api/ prefix before forwarding
# to the VPS, so the VPS only sees /sim_ai.  All other routes in this project
# (e.g. /chat, /voice, /blockzie/open) correctly omit the /api/ prefix.
async def sim_ai(req: SimAIReq):
    """
    Agentic simulator planner.

    Request:
      { "mode": "agent_build", "prompt": "...", "circuit": {} }

    Response:
      { "reply": "...", "project": { "title", "components", "connections", "code", ... } }
    """
    prompt = (req.prompt or "").strip()
    if not prompt:
        return {"ok": False, "reply": "Prompt is required.", "project": {}}

    system_prompt = build_agentic_prompt()
    user_payload  = {
        "mode":    req.mode,
        "prompt":  prompt,
        "circuit": req.circuit or {},
    }

    try:
        raw = await router_client.chat(
            model=MODEL_TEXT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.2,
        )

        raw_json = _extract_first_json_object(raw)
        parsed   = json.loads(raw_json)
        parsed   = validate_project_json(parsed)

        project = parsed.get("project", {})
        if not project.get("components"):
            return {
                "ok":     False,
                "reply":  parsed.get("reply", "AI did not generate a valid simulator plan."),
                "project": project,
            }

        return {
            "ok":     True,
            "reply":  parsed.get("reply", "Project generated."),
            "project": project,
        }

    except Exception as e:
        return {
            "ok":     False,
            "reply":  f"Simulator AI generation failed: {type(e).__name__}: {e}",
            "project": {},
        }