import os
import re
import html
import tempfile
import subprocess
import base64
import unicodedata
from typing import Optional

from faster_whisper import WhisperModel
import edge_tts

# Fast + good for MVP
_WHISPER = None


def get_whisper():
    global _WHISPER
    if _WHISPER is None:
        print("[STT] Loading Whisper model (small, int8, cpu)...")
        _WHISPER = WhisperModel("small", device="cpu", compute_type="int8")
        print("[STT] Whisper model loaded.")
    return _WHISPER


# Comprehensive voice mapping for 18+ languages
VOICE_MAPPING = {
    # English variants
    "en": "en-IN-PrabhatNeural",
    "en-us": "en-US-GuyNeural",
    "en-gb": "en-GB-RyanNeural",
    "en-in": "en-IN-PrabhatNeural",

    # Indian languages
    "hi": "hi-IN-MadhurNeural",
    "hi-in": "hi-IN-MadhurNeural",
    "ta": "ta-IN-ValluvarNeural",
    "ta-in": "ta-IN-ValluvarNeural",
    "te": "te-IN-MohanNeural",
    "te-in": "te-IN-MohanNeural",
    "mr": "mr-IN-ManoharNeural",
    "mr-in": "mr-IN-ManoharNeural",
    "bn": "bn-IN-BashkarNeural",
    "bn-in": "bn-IN-BashkarNeural",
    "gu": "gu-IN-NiranjanNeural",
    "gu-in": "gu-IN-NiranjanNeural",

    # Major world languages
    "es": "es-ES-AlvaroNeural",
    "es-es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    "fr-fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "de-de": "de-DE-ConradNeural",
    "zh": "zh-CN-YunxiNeural",
    "zh-cn": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
    "ja-jp": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
    "ko-kr": "ko-KR-InJoonNeural",
    "pt": "pt-BR-AntonioNeural",
    "pt-br": "pt-BR-AntonioNeural",
    "ru": "ru-RU-DmitryNeural",
    "ru-ru": "ru-RU-DmitryNeural",
    "ar": "ar-SA-HamedNeural",
    "ar-sa": "ar-SA-HamedNeural",
}

# Optional named voice presets you can use directly from backend
VOICE_PRESETS = {
    "default": "en-IN-PrabhatNeural",
    "male_india": "en-IN-PrabhatNeural",
    "male_us": "en-US-GuyNeural",
    "male_uk": "en-GB-RyanNeural",
    "hindi_male": "hi-IN-MadhurNeural",
    "tamil_male": "ta-IN-ValluvarNeural",
    "telugu_male": "te-IN-MohanNeural",
    "marathi_male": "mr-IN-ManoharNeural",
    "bengali_male": "bn-IN-BashkarNeural",
    "gujarati_male": "gu-IN-NiranjanNeural",
}


def get_voice_for_language(lang_code: str) -> str:
    """
    Get the appropriate Edge TTS voice for a given language code.
    Falls back to English (India) if language not supported.
    """
    lang_code = (lang_code or "en").strip().lower()

    if lang_code in VOICE_MAPPING:
        return VOICE_MAPPING[lang_code]

    base_lang = lang_code.split("-")[0]
    if base_lang in VOICE_MAPPING:
        return VOICE_MAPPING[base_lang]

    return "en-IN-PrabhatNeural"


def get_voice(voice: Optional[str] = None, lang_code: Optional[str] = None) -> str:
    """
    Resolve voice from:
    1. explicit voice preset name
    2. explicit Edge voice name
    3. language code
    4. default fallback
    """
    if voice:
        voice_key = voice.strip().lower()

        if voice_key in VOICE_PRESETS:
            return VOICE_PRESETS[voice_key]

        # If caller passes exact Edge voice like en-US-GuyNeural
        return voice.strip()

    if lang_code:
        return get_voice_for_language(lang_code)

    return "en-IN-PrabhatNeural"


def _to_wav_16k_mono(input_path: str, out_path: str):
    """Convert audio to 16kHz mono WAV format for Whisper"""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", "16000",
        out_path
    ]
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )


def stt_transcribe(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes to text using Faster Whisper.
    Supports automatic language detection.
    """
    with tempfile.TemporaryDirectory() as td:
        raw_path = os.path.join(td, "in_audio")
        wav_path = os.path.join(td, "in.wav")

        with open(raw_path, "wb") as f:
            f.write(audio_bytes)

        _to_wav_16k_mono(raw_path, wav_path)

        model = get_whisper()
        segments, info = model.transcribe(
            wav_path,
            vad_filter=True,
            language=None
        )

        text = " ".join([s.text.strip() for s in segments]).strip()

        if info and hasattr(info, "language"):
            print(f"[STT] Detected language: {info.language}")

        return text or ""


def strip_emojis_and_symbols(text: str) -> str:
    """
    Remove emojis and many decorative unicode symbols
    so TTS does not speak names like 'rocket' or 'smiling face'.
    """
    cleaned_chars = []

    for ch in text:
        cat = unicodedata.category(ch)

        # Keep normal letters/numbers/punctuation/separators
        # Remove symbols, surrogate-like pictographs, dingbats, etc.
        if cat.startswith("S"):
            continue

        # Remove variation selectors and zero width joiners used in emoji sequences
        if ch in ("\u200d", "\ufe0f"):
            continue

        cleaned_chars.append(ch)

    return "".join(cleaned_chars)


def normalize_tts_text(text: str) -> str:
    """
    Clean text before sending to TTS.
    """
    if not text:
        return ""

    # HTML entities -> plain text
    text = html.unescape(text)

    # Remove markdown code fences
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)

    # Remove inline code markers
    text = text.replace("`", "")

    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)

    # Replace markdown bullets and separators with pauses
    text = text.replace("•", ". ")
    text = text.replace("—", " ")
    text = text.replace("–", " ")
    text = text.replace("|", ". ")

    # Common chat/status emoji-like decorations
    replacements = {
        "✅": "",
        "❌": "",
        "⚠️": "",
        "⚠": "",
        "🚀": "",
        "🎉": "",
        "🔥": "",
        "💡": "",
        "🤖": "",
        "😊": "",
        "🙂": "",
        "😂": "",
        "👍": "",
        "🔊": "",
        "🎙️": "",
        "🎙": "",
        "📦": "",
        "🧩": "",
        "➕": "",
        "🗑️": "",
        "🗑": "",
        "🛑": "",
        "👂": "",
        "✨": "",
        "⭐": "",
        "❤️": "",
        "❤": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove remaining emojis / symbols
    text = strip_emojis_and_symbols(text)

    # Remove bracketed icon-like labels if desired
    text = re.sub(r"\[(ok|error|warning|info|success)\]", " ", text, flags=re.I)

    # Clean repeated punctuation
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", ". ", text)
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    text = re.sub(r"([.,!?]){2,}", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


async def tts_speak_mp3(
    text: str,
    voice: str = None,
    lang_code: str = None,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> bytes:
    """
    Convert text to speech using Edge TTS.

    Args:
        text: Text to synthesize
        voice: Specific voice preset or exact Edge voice
        lang_code: Language code to auto-select voice
        rate: TTS speaking rate (example: '+0%', '-10%', '+15%')
        volume: TTS volume (example: '+0%', '+20%')
        pitch: TTS pitch (example: '+0Hz', '+20Hz', '-10Hz')

    Returns:
        MP3 audio bytes
    """
    clean_text = normalize_tts_text(text)

    if not clean_text:
        clean_text = "Sorry, I have no response to speak."

    selected_voice = get_voice(voice=voice, lang_code=lang_code)
    print(f"[TTS] Voice selected: {selected_voice}")
    print(f"[TTS] Clean text: {clean_text[:120]}{'...' if len(clean_text) > 120 else ''}")

    with tempfile.TemporaryDirectory() as td:
        out_mp3 = os.path.join(td, "out.mp3")

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=selected_voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
        await communicate.save(out_mp3)

        with open(out_mp3, "rb") as f:
            return f.read()


def b64(b: bytes) -> str:
    """Encode bytes to base64 string"""
    return base64.b64encode(b).decode("utf-8")


async def tts_speak_mp3_with_lang(text: str, lang_code: str = "en") -> bytes:
    """
    Simplified TTS function that takes language code directly.
    """
    return await tts_speak_mp3(text, lang_code=lang_code)


async def tts_speak_mp3_with_voice(text: str, voice: str = "default") -> bytes:
    """
    Simplified TTS function that takes a voice preset or exact voice directly.
    Examples:
      - default
      - male_india
      - male_us
      - male_uk
      - hi-IN-MadhurNeural
    """
    return await tts_speak_mp3(text, voice=voice)