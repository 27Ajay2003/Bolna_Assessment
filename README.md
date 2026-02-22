# status_watcher

A lightweight Python service that monitors third-party service status pages (like OpenAI, Anthropic, Stripe, Cloudflare) and automatically prints an alert whenever an incident is created, updated, or resolved.

---

## Problem Statement

> Track and log service updates from the OpenAI Status Page. Whenever there's a new incident, outage, or degradation update related to any OpenAI API product, automatically detect the update and print the affected product/service and the latest status message. The solution should scale efficiently to 100+ similar status pages.

---

## Features

- **Real-time polling** of one or more Statuspage.io-compatible API endpoints
- **Concurrent watching** of multiple providers using `asyncio` — all pages polled simultaneously, not sequentially
- **Full incident lifecycle detection:**
  - 🔴 New active incident appears
  - 🟡 Existing incident receives an update
  - 🟢 Incident status transitions to resolved
- **Smart baseline** — on startup, already-resolved incidents are silently swallowed. No alert storm on boot.
- **Graceful error handling** — network timeouts, connection errors, and non-200 responses are logged without crashing the watcher
- **Easily extensible** — add new providers in `config.py`, swap `print()` for Slack/webhook/email in `handler.py`

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
├── Dockerfile               # Multi-stage Docker build
├── .dockerignore            # Excludes venv, cache, test files from build context
├── test_watcher.py          # Offline tests for all event types
└── watcher/
    ├── fetcher.py           # Async HTTP: fetches incidents JSON
    ├── state.py             # In-memory store of last known incident state
    ├── differ.py            # Detects what changed between two fetches
    └── handler.py           # Formats and prints alert output
```

---

## Setup

### 1. Clone / unzip the project

```bash
cd status_watcher
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

---

## Docker

### Build the image

```bash
docker build -t status-watcher .
```

### Run (logs stream to terminal)

```bash
docker run --rm status-watcher
```

### Run in the background (detached)

```bash
docker run -d --name status-watcher status-watcher
```

### View live logs

```bash
docker logs -f status-watcher
```

### Stop

```bash
docker stop status-watcher
```

> **Note:** The app has no ports to expose and no volumes to mount — it only prints to stdout. `docker logs` is all you need to monitor it.

---

## Configuration

Edit `config.py` to add or remove providers:

```python
STATUS_PAGES = [
    {
        "name": "OpenAI",
        "incidents_url": "https://status.openai.com/api/v2/incidents.json",
        "poll_interval": 30,   # seconds between each poll
    },
    {
        "name": "Anthropic",
        "incidents_url": "https://status.anthropic.com/api/v2/incidents.json",
        "poll_interval": 30,
    },
    {
        "name": "Stripe",
        "incidents_url": "https://www.stripestatus.com/api/v2/incidents.json",
        "poll_interval": 60,
    },
    {
        "name": "Cloudflare",
        "incidents_url": "https://www.cloudflarestatus.com/api/v2/incidents.json",
        "poll_interval": 30,
    },
]
```

Any service that uses the **Statuspage.io API v2** format works out of the box.

---

## Running Tests

```bash
python3 test_watcher.py
```

The test suite covers all 6 scenarios without requiring a live API or a real incident:

| Test | Scenario | Expected |
|------|----------|----------|
| 1 | New active incident appears | `new_incident` event fired |
| 2 | Incident receives a new update | `incident_updated` event fired |
| 3 | Incident disappears from feed | `resolved` event fired |
| 4 | No change between polls | No events fired |
| 5 | Already-resolved incident on startup | Silently skipped — no event |
| 6 | Active incident status → `resolved` | `resolved` event fired (not `incident_updated`) |

---

## Architecture & Design Decisions

### Why `asyncio` + `aiohttp`?

The problem statement specifically asks for a solution that can scale to **100+ status pages** efficiently. A naive approach would use threads or sequential polling, which doesn't scale:

- **Threads**: 100 threads = high memory overhead, OS scheduling overhead
- **Sequential polling**: With 100 pages × 30s interval, page 100 would be checked only every ~50 minutes
- **`asyncio`**: A single-threaded event loop handles all I/O concurrently. 100 pages poll truly in parallel, with negligible overhead. Connection pooling via `TCPConnector(limit=100)` prevents socket exhaustion.

### Baseline-first design

On startup, the first fetch is used exclusively to set the baseline — no events are fired. This prevents an alert flood when starting the watcher against a provider that already has 20 historical incidents in its feed. Only *changes* from that baseline onward trigger alerts.

### How resolved detection works

The Statuspage.io API **never removes resolved incidents** from the feed — they stay indefinitely as historical records. This means "incident disappeared from feed" would never fire. Instead, resolution is detected by:

1. **Primary**: Checking if `status == "resolved"` when an existing incident receives a new update (its `latest_update_at` changes). This is the real-world path.
2. **Fallback**: If an incident ID disappears from the feed entirely (rare, but possible if a provider cleans old data), it's also emitted as `resolved`.

### Already-resolved incidents on startup are silently skipped

When the watcher boots up, the provider feed may contain dozens of older resolved incidents. Without this guard, every one of them would fire a `new_incident` alert. The fix: during first-time processing (ID not in `old_state`), if `status == "resolved"`, the incident is added to the state store but no event is emitted.

### State is intentionally in-memory

Restarting the process resets the baseline cleanly. There's no risk of stale persisted state causing missed events or duplicate alerts. For a production system, a Redis or SQLite-backed store could be dropped in to `StateStore` without touching any other file.

---

## Extending the Handler

To send Slack messages, emails, or webhook calls instead of printing:

```python
# watcher/handler.py
def handle_event(provider_name: str, event: dict):
    # Replace or augment the print() below with your integration
    requests.post(SLACK_WEBHOOK_URL, json={"text": f"..."})
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `aiohttp` | 3.9.5 | Async HTTP client |
| `aiosignal` | 1.3.1 | aiohttp dependency |
| `async-timeout` | 4.0.3 | aiohttp dependency |
| `attrs` | 23.2.0 | aiohttp dependency |
| `frozenlist` | 1.4.1 | aiohttp dependency |
| `multidict` | 6.0.5 | aiohttp dependency |
| `yarl` | 1.9.4 | aiohttp dependency |

All dependencies are part of the standard `aiohttp` ecosystem. No LLMs, no databases, no external services required.
