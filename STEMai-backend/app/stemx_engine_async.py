# -*- coding: utf-8 -*-
"""
StemXEngineAsync — Playwright-based Blockzie browser controller.

VPS / Linux server support
──────────────────────────
On a headless Linux VPS there is no physical display, so Chrome cannot
open a visible window.  blockzie.info uses canvas-heavy JS that does NOT
work in Playwright's pure headless mode.

Solution: start a lightweight Xvfb virtual framebuffer so Chrome believes
it has a real 1920×1080 display.  This makes blockzie.info run perfectly.

Requirements (one-time server setup):
    apt install -y xvfb
    pip install pyvirtualdisplay

The code below auto-detects whether a real display is available:
  • DISPLAY env var set  → real GUI (dev machine / CI with display) → run as-is
  • No DISPLAY           → VPS/headless → start Xvfb automatically
"""

from pathlib import Path
import asyncio
import os
import sys
import platform
from typing import Callable, Awaitable, Optional

from playwright.async_api import async_playwright

# ── Virtual display for headless Linux (VPS) ─────────────────────────────────
_vdisplay = None   # pyvirtualdisplay.Display instance, kept alive for app lifetime

def _ensure_virtual_display():
    """
    On Linux without a real DISPLAY (i.e. a VPS/headless server), start Xvfb
    so Chrome can open a real window context.  Silently skips on Windows/macOS
    or if a real DISPLAY is already set.
    Called once at module import time so the display is ready before any request.
    """
    global _vdisplay

    # Already running or not needed
    if _vdisplay is not None:
        return

    # Only needed on Linux without an existing DISPLAY
    if platform.system() != "Linux":
        return
    if os.environ.get("DISPLAY"):
        print("[StemX] Real DISPLAY found — skipping Xvfb.")
        return

    try:
        from pyvirtualdisplay import Display
        _vdisplay = Display(visible=False, size=(1920, 1080), color_depth=24)
        _vdisplay.start()
        print(f"[StemX] ✅ Xvfb virtual display started (DISPLAY={os.environ.get('DISPLAY')})")
    except ImportError:
        print(
            "[StemX] ⚠ pyvirtualdisplay not installed. "
            "Run: pip install pyvirtualdisplay  and  apt install xvfb\n"
            "       Falling back to Playwright headless mode (may not work on blockzie.info)."
        )
    except Exception as e:
        print(f"[StemX] ⚠ Could not start Xvfb: {e}. Continuing without virtual display.")


# Start Xvfb as early as possible — before any Playwright call
_ensure_virtual_display()


# ── Editor URL ────────────────────────────────────────────────────────────────
URL = "https://blockzie.info"


# ── Chrome binary detection ───────────────────────────────────────────────────
def get_chrome_path() -> Optional[str]:
    """Detect system Chrome/Chromium path based on OS."""
    system = platform.system()
    if system == "Windows":
        paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
        ]
    elif system == "Darwin":
        paths = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    else:  # Linux / VPS
        paths = [
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
            Path("/snap/bin/chromium"),
        ]

    for p in paths:
        if p.exists():
            return str(p)
    return None


# ── Workspace detection JS ────────────────────────────────────────────────────
JS_HAS_WORKSPACE = r"""() => {
  if (window.Blockly) {
    const ws = (Blockly.getMainWorkspace && Blockly.getMainWorkspace()) || Blockly.mainWorkspace || null;
    if (ws && Blockly.Xml) {
      return {
        kind: "blockly",
        ok: true,
        isReadOnly: ws.isReadOnly ? ws.isReadOnly() : false,
        isFlyout: !!ws.isFlyout,
        blockCount: ws.getAllBlocks ? ws.getAllBlocks(false).length : 0
      };
    }
  }
  if (window.ScratchBlocks) {
    const ws = ScratchBlocks.getMainWorkspace && ScratchBlocks.getMainWorkspace();
    if (ws && ScratchBlocks.Xml) {
      return {
        kind: "scratchblocks",
        ok: true,
        isReadOnly: ws.isReadOnly ? ws.isReadOnly() : false,
        isFlyout: !!ws.isFlyout,
        blockCount: ws.getAllBlocks ? ws.getAllBlocks(false).length : 0
      };
    }
  }
  return { kind: "unknown", ok: false };
}"""


async def _find_frame_with_workspace(page):
    """
    Find the frame containing the MAIN (canvas) Blockly workspace.
    Blockzie has multiple frames — we must pick the editable canvas,
    not the toolbox/palette.
    """
    best_frame      = None
    best_kind       = None
    best_block_count = -1

    for fr in page.frames:
        try:
            res = await fr.evaluate(JS_HAS_WORKSPACE)
            if not isinstance(res, dict) or not res.get("ok"):
                continue

            kind  = res.get("kind")
            score = await fr.evaluate("""
                () => {
                    const B = window.Blockly || window.ScratchBlocks;
                    if (!B) return -1;
                    const ws = B.getMainWorkspace && B.getMainWorkspace();
                    if (!ws) return -1;
                    if (ws.isReadOnly && ws.isReadOnly()) return -1;
                    if (ws.RTL === undefined && ws.isFlyout) return -1;
                    const hasInjectionDiv = !!document.querySelector('.injectionDiv');
                    const hasBlocklyDiv   = !!document.querySelector('.blocklyDiv, #blocklyDiv, [id*="blockly"]');
                    let score = 1;
                    if (hasInjectionDiv) score += 10;
                    if (hasBlocklyDiv)   score += 5;
                    const registeredTypes = Object.keys(B.Blocks || {}).length;
                    score += Math.min(registeredTypes, 50);
                    return score;
                }
            """)

            if isinstance(score, (int, float)) and score > best_block_count:
                best_block_count = score
                best_frame       = fr
                best_kind        = kind

        except Exception:
            pass

    return best_frame, best_kind


# ── JavaScript helpers (unchanged from original) ─────────────────────────────
JS_EXPORT = r"""() => {
  if (window.Blockly) {
    const ws = (Blockly.getMainWorkspace && Blockly.getMainWorkspace()) || Blockly.mainWorkspace;
    const dom = Blockly.Xml.workspaceToDom(ws);
    if (Blockly.Xml.domToText) return Blockly.Xml.domToText(dom);
    return new XMLSerializer().serializeToString(dom);
  }
  if (window.ScratchBlocks) {
    const ws = ScratchBlocks.getMainWorkspace && ScratchBlocks.getMainWorkspace();
    const dom = ScratchBlocks.Xml.workspaceToDom(ws);
    if (ScratchBlocks.Xml.domToText) return ScratchBlocks.Xml.domToText(dom);
    return new XMLSerializer().serializeToString(dom);
  }
  throw new Error("No Blockly/ScratchBlocks");
}"""

JS_CLEAR = r"""() => {
  if (window.Blockly) {
    const ws = (Blockly.getMainWorkspace && Blockly.getMainWorkspace()) || Blockly.mainWorkspace;
    ws.clear(); return "CLEARED";
  }
  if (window.ScratchBlocks) {
    const ws = ScratchBlocks.getMainWorkspace && ScratchBlocks.getMainWorkspace();
    ws.clear(); return "CLEARED";
  }
  throw new Error("No Blockly/ScratchBlocks");
}"""

JS_LOAD_XML_TEXT = r"""(data) => {
  const xmlText = data.xmlText;
  const mode    = data.mode;
  const parser  = new DOMParser();
  const doc     = parser.parseFromString(xmlText, "text/xml");
  const err     = doc.getElementsByTagName("parsererror")[0];
  if (err) throw new Error("XML parse error: " + err.textContent);
  const xmlDom  = doc.documentElement;
  const B       = window.Blockly || window.ScratchBlocks || null;
  if (!B)   throw new Error("No Blockly/ScratchBlocks found on page");
  const ws = (B.getMainWorkspace && B.getMainWorkspace()) || B.mainWorkspace || null;
  if (!ws)  throw new Error("Workspace not found");
  const registered = Object.keys(B.Blocks || {});
  const unknown    = [];
  doc.querySelectorAll("block").forEach(b => {
    const t = b.getAttribute("type");
    if (t && registered.length > 0 && !registered.includes(t)) unknown.push(t);
  });
  if (unknown.length > 0) {
    return {
      ok: false,
      kind: "validation_error",
      unknown_types: [...new Set(unknown)],
      registered_count: registered.length,
      error: "Unknown block types: " + [...new Set(unknown)].join(", ")
    };
  }
  try {
    const origFire   = (B.Events && B.Events.fire) ? B.Events.fire.bind(B.Events) : null;
    const origWsFire = ws.fireChangeListener ? ws.fireChangeListener.bind(ws) : null;
    if (B.Events && B.Events.fire)   B.Events.fire            = function() {};
    if (ws.fireChangeListener)       ws.fireChangeListener    = function() {};
    try {
      if (mode === "inject") ws.clear();
      B.Xml.domToWorkspace(xmlDom, ws);
    } finally {
      if (origFire   && B.Events) B.Events.fire            = origFire;
      if (origWsFire)             ws.fireChangeListener    = origWsFire;
    }
    if (ws.render)       ws.render();
    if (ws.resize)       ws.resize();
    if (ws.scrollCenter) ws.scrollCenter();
  } catch(e) {
    return { ok: false, kind: "load_error", error: e.toString() };
  }
  return {
    ok: true,
    kind: window.Blockly ? "blockly" : "scratchblocks",
    blocks: ws.getAllBlocks(false).length
  };
}"""

JS_GET_BLOCK_TYPES = r"""() => {
  const B = window.Blockly || window.ScratchBlocks || null;
  if (!B) return { ok: false, error: "No Blockly/ScratchBlocks" };
  const types = Object.keys(B.Blocks || {});
  return { ok: true, count: types.length, types: types };
}"""

JS_REMOVE_TYPE = r"""(data) => {
  const blockType = data.blockType;
  const getWS = () => {
    if (window.Blockly)       return (Blockly.getMainWorkspace && Blockly.getMainWorkspace()) || Blockly.mainWorkspace;
    if (window.ScratchBlocks) return ScratchBlocks.getMainWorkspace && ScratchBlocks.getMainWorkspace();
    return null;
  };
  const ws = getWS();
  if (!ws) throw new Error("Workspace not found");
  const blocks  = ws.getAllBlocks(false);
  let removed   = 0;
  for (const b of blocks) {
    if (b.getType && b.getType() === blockType) { b.dispose(true); removed += 1; }
  }
  return { ok: true, removed, remaining: ws.getAllBlocks(false).length };
}"""


# ── Main engine class ─────────────────────────────────────────────────────────
class StemXEngineAsync:
    def __init__(self, url: str = URL, keep_open: bool = True):
        """
        Initialize StemX Engine.

        Args:
            url:       Editor URL to open.
            keep_open: Keep browser alive between operations (recommended).
        """
        self.url        = url
        self.keep_open  = keep_open
        self._p         = None
        self._browser   = None
        self._context   = None
        self._page      = None
        self._frame     = None
        self._kind      = None
        self._lock      = asyncio.Lock()

    # ── browser liveness check ─────────────────────────────────────────────
    def _is_alive(self) -> bool:
        if not self._browser or not self._page or not self._frame:
            return False
        try:
            if self._page.is_closed():
                return False
            if not self._browser.is_connected():
                return False
        except Exception:
            return False
        return True

    # ── open / launch ──────────────────────────────────────────────────────
    async def _open(self):
        """
        Open browser and navigate to editor.
        Reuses existing browser if keep_open=True and still alive.

        VPS note: Xvfb is started at module import (_ensure_virtual_display).
        Chrome runs with headless=False inside the virtual display so
        blockzie.info sees a real browser context.
        """
        if self.keep_open and self._is_alive():
            return self._p, self._browser, self._context, self._page, self._frame, self._kind

        if self.keep_open:
            await self.close()

        chrome_path = get_chrome_path()

        # ── Determine headless mode ────────────────────────────────────────
        # On Linux VPS: Xvfb gives us a virtual display, so keep headless=False
        # (blockzie.info needs a real browser context).
        # On macOS/Windows dev machines: also headless=False (real GUI).
        # Only fall back to Playwright headless if Xvfb failed AND no DISPLAY.
        on_linux_no_display = (
            platform.system() == "Linux"
            and not os.environ.get("DISPLAY")
            and _vdisplay is None          # Xvfb did NOT start
        )
        use_headless = on_linux_no_display   # True only if Xvfb unavailable
        if use_headless:
            print("[StemX] ⚠ No display and Xvfb unavailable — using Playwright headless mode.")

        # ── Launch args ────────────────────────────────────────────────────
        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-gpu",               # always safe, saves memory on VPS
        ]

        # --start-maximized only works with a real (or virtual) display
        if not use_headless:
            launch_args.append("--start-maximized")

        launch_options = {
            "headless": use_headless,
            "args":     launch_args,
        }
        if chrome_path:
            launch_options["executable_path"] = chrome_path

        p = await async_playwright().start()

        browser = await p.chromium.launch(**launch_options)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()
        await page.goto(self.url, wait_until="domcontentloaded")

        # ── Handle landing page ────────────────────────────────────────────
        print("[StemX] Waiting for page to render (5 s)…")
        await page.wait_for_timeout(5000)
        print("[StemX] Checking for landing page…")

        landing_selectors = [
            "img[src*='1ecb758138ff5f6e832707425a5c5075']",
            "div[class*='newScreenBox']:first-of-type",
            "div[class*='newScreenBox']",
            "div[class*='gui_newScreenBox']",
        ]
        clicked = False
        for selector in landing_selectors:
            try:
                el = await page.wait_for_selector(selector, timeout=5000)
                if el:
                    print(f"[StemX] Landing page found via: {selector}")
                    await el.click()
                    print("[StemX] ✅ Clicked Block Coding — waiting for editor…")
                    await page.wait_for_timeout(5000)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            print("[StemX] ⚠ Could not find Block Coding card.")
            try:
                await page.screenshot(path="blockzie_debug.png")
                print("[StemX] Screenshot saved: blockzie_debug.png")
            except Exception:
                pass

        # ── Wait for Blockly workspace to be fully ready ───────────────────
        print("[StemX] Waiting for Blockly workspace to initialize…")
        max_wait_seconds = 120
        poll_interval    = 2000  # ms
        waited           = 0
        ready            = False

        while waited < (max_wait_seconds * 1000):
            try:
                result = await page.evaluate("""
                    () => {
                        const B = window.Blockly || window.ScratchBlocks;
                        if (!B || !B.Xml) return {ready: false, reason: 'no Blockly'};
                        const ws = B.getMainWorkspace && B.getMainWorkspace();
                        if (!ws)          return {ready: false, reason: 'no workspace'};
                        const types = Object.keys(B.Blocks || {}).length;
                        if (types < 10)   return {ready: false, reason: 'only ' + types + ' types', types};
                        return {ready: true, types};
                    }
                """)
                types    = result.get("types",  0)     if isinstance(result, dict) else 0
                is_ready = result.get("ready", False)  if isinstance(result, dict) else False
                print(f"[StemX] {waited // 1000}s — registeredTypes={types}")
                if is_ready:
                    ready = True
                    print(f"[StemX] ✅ Blockly ready! {types} block types registered.")
                    break
            except Exception as e:
                print(f"[StemX] Poll error: {e}")

            await page.wait_for_timeout(poll_interval)
            waited += poll_interval

        if not ready:
            print(f"[StemX] ⚠ Workspace not fully ready after {max_wait_seconds}s, proceeding anyway…")

        frame, kind = await _find_frame_with_workspace(page)
        if not frame:
            await context.close()
            await browser.close()
            await p.stop()
            raise RuntimeError(
                "Workspace not found. Ensure editor fully loads. "
                "Check blockzie_debug.png for a screenshot."
            )

        if self.keep_open:
            self._p       = p
            self._browser = browser
            self._context = context
            self._page    = page
            self._frame   = frame
            self._kind    = kind

        return p, browser, context, page, frame, kind

    # ── close ──────────────────────────────────────────────────────────────
    async def close(self):
        """Close browser and clean up all Playwright resources."""
        for attr, name in [("_context", "context"), ("_browser", "browser"), ("_p", "playwright")]:
            obj = getattr(self, attr, None)
            if obj:
                try:
                    await obj.close()
                except Exception:
                    pass
                finally:
                    setattr(self, attr, None)

        self._page  = None
        self._frame = None
        self._kind  = None

    # ── retry helper ───────────────────────────────────────────────────────
    def _should_retry(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(phrase in msg for phrase in [
            "has been closed",
            "target page, context or browser has been closed",
            "execution context was destroyed",
            "browser has been closed",
        ])

    async def _with_retry(self, fn: Callable[[], Awaitable], on_recover: Optional[Callable[[], Awaitable]] = None):
        try:
            return await fn()
        except Exception as e:
            if self.keep_open and self._should_retry(e):
                await self.close()
                if on_recover:
                    await on_recover()
                return await fn()
            raise

    # ── workspace operations ───────────────────────────────────────────────
    async def export_xml(self, on_recover=None) -> str:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:    return await frame.evaluate(JS_EXPORT)
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def clear(self, on_recover=None) -> str:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:    return await frame.evaluate(JS_CLEAR)
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def load_xml_file(self, xml_path: Path, mode: str = "inject", on_recover=None) -> dict:
        xml_text = xml_path.read_text(encoding="utf-8")
        return await self.load_xml_text(xml_text, mode=mode, on_recover=on_recover)

    async def load_xml_text(self, xml_text: str, mode: str = "inject", on_recover=None) -> dict:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:    return await frame.evaluate(JS_LOAD_XML_TEXT, {"xmlText": xml_text, "mode": mode})
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def start_green_flag(self, on_recover=None) -> bool:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:
                    js = r"""
                    () => {
                      const needles = ["green flag","greenflag","start","run","play"];
                      const nodes   = Array.from(document.querySelectorAll('button,[role="button"],img,svg,span,div'));
                      function score(el) {
                        const attrs = [el.getAttribute?.("aria-label"),el.getAttribute?.("title"),
                          el.getAttribute?.("alt"),el.getAttribute?.("data-tooltip"),
                          el.getAttribute?.("data-tip"),el.className&&String(el.className),el.id
                        ].filter(Boolean).join(" ").toLowerCase();
                        let s = 0;
                        for (const n of needles) if (attrs.includes(n)) s += 2;
                        return s;
                      }
                      function clickEl(el) {
                        if (!el) return false;
                        const clickable = el.closest?.('button,[role="button"]') || el;
                        clickable.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true,view:window}));
                        return true;
                      }
                      let best=null,bestScore=0;
                      for (const el of nodes) { const s=score(el); if(s>bestScore){bestScore=s;best=el;} }
                      const fallbacks=['button[aria-label*="Green" i]','button[title*="Green" i]',
                        'button[aria-label*="flag" i]','button[title*="flag" i]',
                        '[class*="green-flag" i]','[class*="greenFlag" i]'];
                      if (best && bestScore >= 2) return clickEl(best);
                      for (const sel of fallbacks) { const el=document.querySelector(sel); if(el&&clickEl(el)) return true; }
                      return false;
                    }
                    """
                    return bool(await page.evaluate(js))
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def stop_all(self, on_recover=None) -> bool:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:
                    js = r"""
                    () => {
                      const needles=["stop","terminate","halt"];
                      const nodes=Array.from(document.querySelectorAll('button,[role="button"],img,svg,span,div'));
                      function score(el){
                        const attrs=[el.getAttribute?.("aria-label"),el.getAttribute?.("title"),
                          el.getAttribute?.("alt"),el.getAttribute?.("data-tooltip"),
                          el.getAttribute?.("data-tip"),el.className&&String(el.className),el.id
                        ].filter(Boolean).join(" ").toLowerCase();
                        let s=0;
                        for(const n of needles) if(attrs.includes(n)) s+=2;
                        if(attrs.includes("stop-sign")||attrs.includes("stopsign")) s+=1;
                        return s;
                      }
                      function clickEl(el){
                        if(!el) return false;
                        const clickable=el.closest?.('button,[role="button"]')||el;
                        clickable.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true,view:window}));
                        return true;
                      }
                      let best=null,bestScore=0;
                      for(const el of nodes){const s=score(el);if(s>bestScore){bestScore=s;best=el;}}
                      const fallbacks=['button[aria-label*="Stop" i]','button[title*="Stop" i]',
                        '[class*="stop" i]','[class*="stop-all" i]','[class*="stopSign" i]'];
                      if(best&&bestScore>=2) return clickEl(best);
                      for(const sel of fallbacks){const el=document.querySelector(sel);if(el&&clickEl(el)) return true;}
                      document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",code:"Escape",bubbles:true}));
                      return false;
                    }
                    """
                    return bool(await page.evaluate(js))
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def remove_type(self, block_type: str, on_recover=None) -> dict:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:    return await frame.evaluate(JS_REMOVE_TYPE, {"blockType": block_type})
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def get_block_types(self, on_recover=None) -> dict:
        async with self._lock:
            async def _do():
                p, browser, context, page, frame, kind = await self._open()
                try:    return await frame.evaluate(JS_GET_BLOCK_TYPES)
                finally:
                    if not self.keep_open:
                        await context.close(); await browser.close(); await p.stop()
            return await self._with_retry(_do, on_recover=on_recover)

    async def debug_frames(self) -> dict:
        if not self._page:
            return {"ok": False, "error": "No page open"}
        results = []
        for i, fr in enumerate(self._page.frames):
            try:
                info = await fr.evaluate(JS_HAS_WORKSPACE)
                results.append({"frame_index": i, "url": fr.url, "name": fr.name, "workspace_info": info})
            except Exception as e:
                results.append({"frame_index": i, "url": fr.url, "name": fr.name, "error": str(e)})
        return {
            "ok": True,
            "frame_count": len(self._page.frames),
            "current_frame_url": self._frame.url if self._frame else None,
            "current_kind": self._kind,
            "frames": results,
        }

    async def refresh_workspace(self):
        if not self._page or self._page.is_closed():
            raise RuntimeError("No active page")
        frame, kind = await _find_frame_with_workspace(self._page)
        if not frame:
            raise RuntimeError("Workspace not found after refresh")
        self._frame = frame
        self._kind  = kind
        return {"ok": True, "kind": kind}