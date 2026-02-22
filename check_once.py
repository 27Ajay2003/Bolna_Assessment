"""
check_once.py — Single-shot version for GitHub Actions / CI.
Fetches incidents from all configured providers and prints any active ones.
No polling loop — runs once and exits.
"""

import asyncio
import aiohttp
from config import STATUS_PAGES
from watcher.fetcher import fetch_incidents
from watcher.handler import handle_event


async def check_all():
    connector = aiohttp.TCPConnector(limit=100)
    timeout = aiohttp.ClientTimeout(total=15)

    found_any = False

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        for page in STATUS_PAGES:
            url = page["incidents_url"]
            name = page["name"]

            incidents = await fetch_incidents(session, url)
            if not incidents:
                print(f"[{name}] No incidents or fetch failed.")
                continue

            active = [i for i in incidents if i.get("status") != "resolved"]

            if not active:
                print(f"[{name}] ✅ All clear — no active incidents.")
            else:
                found_any = True
                for incident in active:
                    updates = incident.get("incident_updates", [])
                    latest = updates[0] if updates else {}
                    handle_event(name, {
                        "type": "new_incident",
                        "incident_name": incident.get("name"),
                        "status": incident.get("status"),
                        "impact": incident.get("impact", "none"),
                        "components": [
                            c.get("name") for c in incident.get("components", []) if c.get("name")
                        ],
                        "message": latest.get("body", "No details."),
                        "timestamp": latest.get("created_at"),
                    })

    if not found_any:
        print("\n✅ All providers are fully operational.")


if __name__ == "__main__":
    asyncio.run(check_all())
