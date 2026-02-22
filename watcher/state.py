import json
import os


class StateStore:
    """
    In-memory store that tracks the last known state per status page URL.

    Structure per URL:
    {
        "incident_id": {
            "status": "investigating",
            "latest_update_at": "2025-11-03T14:32:00Z"
        },
        ...
    }
    """

    def __init__(self):
        self._store: dict[str, dict] = {}

    def initialize(self, url: str, incidents: list):
        """Set baseline state on first fetch — no events fired."""
        self._store[url] = self._snapshot(incidents)

    def get(self, url: str) -> dict:
        return self._store.get(url, {})

    def update(self, url: str, incidents: list):
        self._store[url] = self._snapshot(incidents)

    def _snapshot(self, incidents: list) -> dict:
        snapshot = {}
        for incident in incidents:
            iid = incident.get("id")
            if not iid:
                continue
            updates = incident.get("incident_updates", [])
            latest_update_at = updates[0].get("created_at") if updates else None
            snapshot[iid] = {
                "status": incident.get("status"),
                "latest_update_at": latest_update_at,
                "name": incident.get("name", "Unknown Incident"),
                "impact": incident.get("impact", "none"),
                "components": [
                    c.get("name") for c in incident.get("components", []) if c.get("name")
                ],
            }
        return snapshot

    def load_from_json(self, path: str):
        """Load persisted state from a JSON file. No-op if file doesn't exist."""
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            self._store = json.load(f)

    def save_to_json(self, path: str):
        """Write current state to a JSON file for persistence across runs."""
        with open(path, "w") as f:
            json.dump(self._store, f, indent=2)