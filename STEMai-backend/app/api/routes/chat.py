from fastapi import APIRouter, Depends
import json
import asyncio

from app.models.schemas import ChatReq
from app.core.config import MODEL_TEXT, MODEL_VISION
from app.core.auth import get_current_user

from app.tutor_orchestrator import build_messages, postprocess_with_rules
from app.storage import get_progress, save_progress
from app.voice_pipeline import tts_speak_mp3, b64
from app.core.utils import _fast_voice_text, _pick_voice
from app.router_openrouter import OpenRouterClient

router = APIRouter()
router_client = OpenRouterClient()


async def call_llm_with_fallback(
    router_client: OpenRouterClient,
    messages: list,
    temperature: float = 0.4,
    preferred_model: str | None = None,
    is_vision: bool = False,
) -> str:
    """
    Try preferred model first, then fallback models.
    Retry only for temporary 500 errors.
    """
    model_candidates = []

    if preferred_model:
        model_candidates.append(preferred_model)

    if is_vision:
        # Keep same vision-capable fallback order if image exists
        extra_models = [
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
        ]
    else:
        extra_models = [
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "meta-llama/3-8b-instruct",
        ]

    for m in extra_models:
        if m not in model_candidates:
            model_candidates.append(m)

    last_error = None

    for model in model_candidates:
        for attempt in range(2):
            try:
                print(f"[LLM] trying model={model}, attempt={attempt + 1}")
                result = await router_client.chat(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                print(f"[LLM] success model={model}")
                return result
            except Exception as e:
                print(f"[LLM] failed model={model}, attempt={attempt + 1}: {repr(e)}")
                last_error = e

                # Retry once only for server-side temporary failures
                if "500" in str(e) and attempt < 1:
                    await asyncio.sleep(1.5)
                    continue

                break

    raise RuntimeError(f"All models failed: {last_error}")


@router.post("/chat")
async def chat(req: ChatReq, user=Depends(get_current_user)):
    print("\n========== /chat called ==========")
    user_id = user["id"]
    role = user["role"]
    print("[chat] user_id:", user_id)
    print("[chat] role:", role)
    print("[chat] req.text:", repr(req.text))
    print("[chat] has image:", bool(req.image_data_url))
    print("[chat] want_voice:", req.want_voice)
    print("[chat] voice_lang:", req.voice_lang)
    print("[chat] incoming history count:", len(req.messages or []))

    model = MODEL_VISION if req.image_data_url else MODEL_TEXT
    print("[chat] selected model:", model)

    latest_messages = build_messages(req.text, req.image_data_url)
    print("[chat] latest_messages built:", json.dumps(latest_messages, indent=2, default=str))

    system_message = latest_messages[0]
    current_user_message = latest_messages[-1]

    history_messages = [
        {"role": m.role, "content": m.content}
        for m in (req.messages or [])
        if m.role in ("user", "assistant") and m.content
    ]

    history_messages = history_messages[-6:]

    print("[chat] filtered history count:", len(history_messages))
    print("[chat] filtered history:", json.dumps(history_messages, indent=2, default=str))

    messages = [system_message, *history_messages, current_user_message]

    if req.image_data_url:
        messages.append({
            "role": "system",
            "content": (
                "If an image is present, include a final line: META_JSON:{...} "
                "with keys: board, has_common_gnd, sensor_voltage, uses_adc_pin, "
                "uses_pwm_pin, breadboard_rails_connected. Use true/false/null."
            )
        })

    print("[chat] final messages being sent to OpenRouter:")
    print(json.dumps(messages, indent=2, default=str))

    try:
        answer = await call_llm_with_fallback(
            router_client=router_client,
            messages=messages,
            temperature=0.4,
            preferred_model=model,
            is_vision=bool(req.image_data_url),
        )
        print("[chat] OpenRouter answer received")
        print("[chat] answer preview:", repr(answer[:500] if isinstance(answer, str) else answer))

    except Exception as e:
        print("[chat] OpenRouter main call failed:", repr(e))

        if req.image_data_url:
            try:
                fallback_latest = build_messages(
                    req.text + "\n\n(If you cannot see the image, tell me what you see.)",
                    image_data_url=None
                )
                fallback_system = fallback_latest[0]
                fallback_current_user = fallback_latest[-1]
                fallback_messages = [fallback_system, *history_messages, fallback_current_user]

                print("[chat] trying fallback text-only model")
                print(json.dumps(fallback_messages, indent=2, default=str))

                answer = await call_llm_with_fallback(
                    router_client=router_client,
                    messages=fallback_messages,
                    temperature=0.4,
                    preferred_model=MODEL_TEXT,
                    is_vision=False,
                )
                answer += "\n\n⚠️ I couldn’t read the image via the vision model."
                print("[chat] fallback answer preview:", repr(answer[:500]))
            except Exception as fallback_error:
                print("[chat] fallback text-only model also failed:", repr(fallback_error))
                return {
                    "text": "⚠️ AI service is busy right now. Please try again in a few seconds.",
                    "meta": None,
                    "audio_reply_base64": None,
                    "audio_mime": None
                }
        else:
            return {
                "text": "⚠️ AI service is busy right now. Please try again in a few seconds.",
                "meta": None,
                "audio_reply_base64": None,
                "audio_mime": None
            }

    meta = None
    if "META_JSON:" in answer:
        print("[chat] META_JSON detected")
        try:
            text_part, meta_part = answer.rsplit("META_JSON:", 1)
            answer = text_part.strip()
            meta = json.loads(meta_part.strip())
            print("[chat] parsed meta:", meta)
        except Exception as e:
            print("[chat] failed to parse META_JSON:", repr(e))
            meta = None
    else:
        print("[chat] no META_JSON found")

    rules_text = postprocess_with_rules(meta)
    print("[chat] rules_text:", repr(rules_text))

    if rules_text:
        answer = answer + "\n\n" + rules_text

    prog = get_progress(user_id) or {}
    prog.setdefault("history", [])
    prog["history"].append({"q": req.text[:300], "has_image": bool(req.image_data_url)})
    prog["history"] = prog["history"][-30:]
    save_progress(user_id, prog)
    print("[chat] progress saved")

    audio_b64 = None
    audio_mime = None
    if req.want_voice:
        print("[chat] generating voice reply...")
        try:
            voice_text = _fast_voice_text(answer)
            print("[chat] voice text preview:", repr(voice_text[:300]))
            mp3_bytes = await tts_speak_mp3(voice_text, voice=_pick_voice(req.voice_lang))
            audio_b64 = b64(mp3_bytes)
            audio_mime = "audio/mpeg"
            print("[chat] voice reply generated")
        except Exception as e:
            print("[chat] voice generation failed:", repr(e))
            audio_b64 = None
            audio_mime = None
    else:
        print("[chat] voice not requested")

    print("[chat] returning response")
    print("========== /chat finished ==========\n")

    return {
        "text": answer,
        "meta": meta,
        "audio_reply_base64": audio_b64,
        "audio_mime": audio_mime
    }
