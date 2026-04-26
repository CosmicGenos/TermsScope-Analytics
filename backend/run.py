import asyncio
import sys

import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        # uvicorn.Server.run() internally calls asyncio_run(..., loop_factory=ProactorEventLoop)
        # on Windows, bypassing any event-loop policy we set. We skip that entirely:
        # create a SelectorEventLoop ourselves and drive serve() directly on it.
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.serve())
        finally:
            loop.close()
    else:
        server.run()
