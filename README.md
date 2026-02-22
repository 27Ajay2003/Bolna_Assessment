# status_watcher

A lightweight Python service that monitors third-party service status pages and automatically alerts whenever an incident is created, updated, or resolved.

**Hosted demo:** [GitHub Actions runs](https://github.com/27Ajay2003/Bolna_Assessment/actions) — polls every 5 minutes, logs are public.

---

## Problem Statement

> Track and log service updates from the OpenAI Status Page. Whenever there's a new incident, outage, or degradation update related to any OpenAI API product, automatically detect the update and print the affected product/service and the latest status message. The solution should scale efficiently to 100+ similar status pages.

---

## Features

- **Real-time polling** of Statuspage.io-compatible API endpoints
- **Concurrent watching** via `asyncio` — all pages polled simultaneously
- **Full incident lifecycle detection:**
  - 🔴 New active incident appears
  - 🟡 Existing incident receives a new update
  - 🟢 Incident resolved
- **Persistent state** across runs via `state.json` — no alert storm on restart
- **Hosted on GitHub Actions** — runs every 5 minutes, commits `state.json` back to the repo

---

## Output Format

```
🔴 NEW INCIDENT [2025-11-03 14:32:00] Product: OpenAI - API Status: investigating — Elevated latency on Chat Completions
🟡 UPDATED [2025-11-03 14:45:00] Product: OpenAI - API Status: monitoring — Fix deployed, watching metrics
🟢 RESOLVED [2025-11-03 15:00:00] Product: OpenAI - API Status: resolved — All systems operational
```

---

## Project Structure

```
status_watcher/
├── main.py                  # Entry point — starts all watchers concurrently
├── config.py                # List of status pages to monitor
├── requirements.txt         # Dependencies
├── test_watcher.py          # Offline unit tests (6 scenarios)
├── Dockerfile               # Multi-stage Docker build
├── .dockerignore
├── .gitignore
├── state.json               # Auto-generated — persists incident state across runs
└── watcher/
    ├── fetcher.py           # Async HTTP: fetches incidents JSON
    ├── state.py             # In-memory + JSON-backed state store
    ├── differ.py            # Detects new/updated/resolved events
    └── handler.py           # Formats and prints alerts
```

---

## Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## Docker

```bash
docker build -t status-watcher .
docker run --rm status-watcher
```

---

## GitHub Actions (Hosted)

The included workflow (`.github/workflows/status_watcher.yml`) runs automatically every 5 minutes:

1. Checks out the repo (including `state.json` from the last run)
2. Runs `python main.py` — polls all providers, prints alerts for any changes
3. Commits updated `state.json` back to the repo with `[skip ci]`

**How state persists:**
```
Run 1: no state.json → baseline set → polls → saves state.json → commits
Run 2: loads state.json → diffs → fires alerts for real changes → saves → commits
```

To trigger manually: go to **Actions → Status Watcher → Run workflow**.

---

## Configuration

Edit `config.py` to add providers:

```python
STATUS_PAGES = [
    {
        "name": "OpenAI",
        "incidents_url": "https://status.openai.com/api/v2/incidents.json",
        "poll_interval": 30,
    },
    # Add any Statuspage.io-compatible provider here
]
```

---

## Running Tests

```bash
python3 test_watcher.py
```

| Test | Scenario | Expected |
|------|----------|----------|
| 1 | New active incident | `new_incident` fired |
| 2 | Incident receives an update | `incident_updated` fired |
| 3 | Incident disappears from feed | `resolved` fired |
| 4 | No change between polls | No events |
| 5 | Already-resolved on startup | Silently skipped |
| 6 | Status changes to `resolved` | `resolved` fired |

---

## Architecture Notes

- **`asyncio` + `aiohttp`** — single-threaded event loop handles 100+ pages concurrently with no threading overhead
- **Baseline-first** — first fetch records state without firing events; prevents alert flood on startup
- **Resolved detection** — Statuspage.io never removes resolved incidents; resolution is detected by checking `status == "resolved"` when `latest_update_at` changes
- **`state.json`** — written after every poll cycle; GitHub Actions commits it back so state survives across the 5-minute scheduled runs

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `aiohttp` | Async HTTP client |
| `asyncio` | Standard library event loop |
