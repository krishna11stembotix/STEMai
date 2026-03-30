import asyncio
import sys
from uvicorn import Config
from uvicorn.server import Server

PORT = 8123  # ✅ unified port

if sys.platform == "win32":
    from asyncio import ProactorEventLoop

    class ProactorServer(Server):
        """Uvicorn server that forces ProactorEventLoop on Windows for Playwright subprocess support."""
        def run(self, sockets=None):
            loop = ProactorEventLoop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.serve(sockets=sockets))

    config = Config(
        app="app.app:app",   # ✅ correct path
        host="0.0.0.0",
        port=PORT,
        reload=False,        # ✅ production safe
    )

    server = ProactorServer(config=config)
    server.run()

else:
    import uvicorn

    uvicorn.run(
        "app.app:app",   # ✅ FIXED (was app.main ❌)
        host="0.0.0.0",
        port=PORT,       # ✅ FIXED (8123)
        reload=False     # ✅ FIXED (no reload in production)
    )
