from fastapi import APIRouter, File, UploadFile, Depends
from app.voice_pipeline import stt_transcribe, tts_speak_mp3, b64
from app.tutor_orchestrator import build_messages
from app.core.config import MODEL_TEXT
from app.router_openrouter import OpenRouterClient
from app.core.auth import get_current_user
router_client = OpenRouterClient()
from app.core.utils import _fast_voice_text, _pick_voice
router = APIRouter()

@router.post("/voice")
async def voice(audio: UploadFile = File(...), lang: str = "en", user=Depends(get_current_user)):
    user_id = user["id"]
    print(f"\n[VOICE] Request from user {user_id}")
    print(f"[VOICE] Language: {lang}")
    
    audio_bytes = await audio.read()

    try:
        user_text = stt_transcribe(audio_bytes)
        print(f"[VOICE] Transcribed: {user_text}")
    except Exception as e:
        print(f"[VOICE] STT failed: {repr(e)}")
        return {"text": f"❌ STT failed: {str(e)}", "audio_reply_base64": None}

    if not user_text:
        return {"text": "⚠️ I couldn’t hear clearly. Please try again.", "audio_reply_base64": None}

    messages = build_messages(user_text, image_data_url=None)
    answer = await router_client.chat(model=MODEL_TEXT, messages=messages, temperature=0.4)
    print(f"[VOICE] Generated response: {answer[:100]}...")

    try:
        voice_text = _fast_voice_text(answer, max_chars=240)
        mp3_bytes = await tts_speak_mp3(voice_text, voice=_pick_voice(lang))
        print(f"[VOICE] Generated audio response ({len(mp3_bytes)} bytes)")
        return {
            "heard_text": user_text,
            "text": answer,
            "audio_reply_base64": b64(mp3_bytes),
            "audio_mime": "audio/mpeg"
        }
    except Exception as e:
        print(f"[VOICE] TTS failed: {repr(e)}")
        return {"text": f"{answer}\n\n TTS failed: {str(e)}", "audio_reply_base64": None}
