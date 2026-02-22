import asyncio
import aiohttp
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import STATUS_PAGES
from watcher.fetcher import fetch_incidents
from watcher.state import StateStore
from watcher.differ import diff_incidents
from watcher.handler import handle_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ── Health check server (for Koyeb / Docker health checks) ──────────────────

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # suppress access logs


def start_health_server(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server running on port {port}")


# ── Watcher logic ────────────────────────────────────────────────────────────

async def watch_page(session: aiohttp.ClientSession, page: dict, store: StateStore):
    """Coroutine that watches a single status page forever."""
    url = page["incidents_url"]
    name = page["name"]
    poll_interval = page.get("poll_interval", 30)

    logger.info(f"Started watching: {name}")

    # First fetch is baseline — don't fire events, just record state
    incidents = await fetch_incidents(session, url)
    if incidents is not None:
        store.initialize(url, incidents)

    while True:
        await asyncio.sleep(poll_interval)
        try:
            incidents = await fetch_incidents(session, url)
            if incidents is None:
                continue

            events = diff_incidents(store.get(url), incidents)
            store.update(url, incidents)

            for event in events:
                handle_event(name, event)

        except Exception as e:
            logger.error(f"Unexpected error watching {name}: {e}")


async def main():
    start_health_server()

    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        store = StateStore()
        watchers = [
            watch_page(session, page, store)
            for page in STATUS_PAGES
        ]
        logger.info(f"Launching {len(watchers)} watcher(s)...")
        await asyncio.gather(*watchers, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")