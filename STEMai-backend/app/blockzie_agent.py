import asyncio
from typing import Optional, Dict, Any

from app.stemx_engine_async import StemXEngineAsync
from app.stemx_text_to_xml import parse_text_to_cmds, build_xml_from_cmds, BlockCmd

# Single engine instance (keeps Chrome open like your Telegram bot)
_engine: Optional[StemXEngineAsync] = None
_lock = asyncio.Lock()

EVENT_PREFIX = "when_"


# ── FIX: _ensure_engine is now wrapped in _lock to prevent race condition
#         where two concurrent requests both see _engine is None and both
#         create a new engine — leaving an orphaned Chrome process.
async def _ensure_engine() -> StemXEngineAsync:
    global _engine
    async with _lock:
        if _engine is None:
            _engine = StemXEngineAsync(keep_open=True)
            if hasattr(_engine, "launch"):
                await _engine.launch()
            elif hasattr(_engine, "start"):
                await _engine.start()
    return _engine


def _has_event_block(cmds: list[BlockCmd]) -> bool:
    return any((c.kind or "").startswith(EVENT_PREFIX) for c in cmds)


async def open_blockzie() -> Dict[str, Any]:
    eng = await _ensure_engine()
    xml = await eng.export_xml()
    return {"ok": True, "msg": "Blockzie opened (or already open).", "xml_len": len(xml)}


async def close_blockzie() -> Dict[str, Any]:
    global _engine
    async with _lock:
        if _engine:
            await _engine.close()
            _engine = None
    return {"ok": True, "msg": "Browser closed."}


async def inject_text_program(text: str, auto_start: bool = True, mode: str = "inject") -> Dict[str, Any]:
    """
    Convert natural-ish text commands -> XML -> inject/append into workspace.

    mode:
      - "inject" = clear then load
      - "append" = add blocks to existing workspace
    """
    if mode not in ("inject", "append"):
        mode = "inject"

    # ── FIX: _ensure_engine already acquires _lock internally, so we must NOT
    #         hold _lock while calling it — that would deadlock.
    #         We acquire _lock only around the engine operation itself.
    eng = await _ensure_engine()

    cmds = parse_text_to_cmds(text)
    if not cmds:
        return {"ok": False, "error": "Could not parse instructions into blocks."}

    # If no hat/event block, auto-add when_flag
    if not _has_event_block(cmds):
        cmds = [BlockCmd("when_flag")] + cmds

    xml = build_xml_from_cmds(cmds)

    res = await eng.load_xml_text(xml, mode=mode)

    started = False
    if auto_start:
        has_green_flag = any(c.kind == "when_flag" for c in cmds)
        if has_green_flag:
            try:
                started = await eng.start_green_flag()
            except Exception:
                started = False

    return {
        "ok": True,
        "loaded": res,
        "auto_started": started,
        "cmds_count": len(cmds),
        "xml_chars": len(xml),
        "mode": mode,
    }


async def stop_all() -> Dict[str, Any]:
    eng = await _ensure_engine()
    stopped = await eng.stop_all()
    return {"ok": True, "stopped": bool(stopped)}


async def clear_workspace() -> Dict[str, Any]:
    eng = await _ensure_engine()
    res = await eng.clear()
    return {"ok": True, "cleared": res}


async def export_xml() -> Dict[str, Any]:
    eng = await _ensure_engine()
    xml = await eng.export_xml()
    return {"ok": True, "xml": xml, "xml_len": len(xml)}


async def remove_type(block_type: str) -> Dict[str, Any]:
    """
    Delete blocks by type.
    Example types depend on editor blocks, e.g.:
      - arduino_digital_output
      - arduino_set_pin_mode
      - control_forever

    ── FIX: duplicate definition of remove_type has been removed.
            Only this single definition exists now.
    """
    block_type = (block_type or "").strip()
    if not block_type:
        return {"ok": False, "error": "Missing block_type"}

    eng = await _ensure_engine()
    res = await eng.remove_type(block_type)
    return {"ok": True, "result": res}


async def load_xml_program(xml_text: str, auto_start: bool = True, mode: str = "inject") -> Dict[str, Any]:
    """
    Load raw Blockzie/ScratchBlocks XML directly into workspace.
    This is required for /agent/make (DSL -> XML).
    """
    if mode not in ("inject", "append"):
        mode = "inject"

    eng = await _ensure_engine()
    res = await eng.load_xml_text(xml_text, mode=mode)

    started = False
    if auto_start:
        try:
            started = await eng.start_green_flag()
        except Exception:
            started = False

    return {
        "ok": True,
        "loaded": res,
        "auto_started": started,
        "xml_chars": len(xml_text),
        "mode": mode,
    }