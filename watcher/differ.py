from datetime import datetime, timezone


def diff_incidents(old_state: dict, fresh_incidents: list) -> list[dict]:
    """
    Compare fresh incidents against the last known state.

    Returns a list of event dicts for anything that changed:
    - New incident detected (active only — already-resolved incidents on startup are skipped)
    - Existing incident received a new update
    - Incident status transitioned to resolved
    - Incident disappeared from the feed entirely (rare fallback)
    """
    events = []
    fresh_ids = set()

    for incident in fresh_incidents:
        iid = incident.get("id")
        if not iid:
            continue

        fresh_ids.add(iid)
        name = incident.get("name", "Unknown Incident")
        status = incident.get("status", "unknown")
        impact = incident.get("impact", "none")
        components = [c.get("name") for c in incident.get("components", []) if c.get("name")]
        updates = incident.get("incident_updates", [])
        latest_update = updates[0] if updates else {}
        latest_message = latest_update.get("body", "No details provided.")
        latest_update_at = latest_update.get("created_at")

        if iid not in old_state:
            # Skip incidents that are already resolved — avoids spamming on startup
            if status != "resolved":
                events.append({
                    "type": "new_incident",
                    "incident_name": name,
                    "status": status,
                    "impact": impact,
                    "components": components,
                    "message": latest_message,
                    "timestamp": latest_update_at,
                })

        else:
            prev = old_state[iid]
            if latest_update_at and latest_update_at != prev.get("latest_update_at"):
                # Status-aware event type: resolved vs updated
                event_type = "resolved" if status == "resolved" else "incident_updated"
                events.append({
                    "type": event_type,
                    "incident_name": name,
                    "status": status,
                    "impact": impact,
                    "components": components,
                    "message": latest_message,
                    "timestamp": latest_update_at,
                })

    # Detect resolved incidents: present in old state but gone from fresh feed
    for iid, prev in old_state.items():
        if iid not in fresh_ids:
            events.append({
                "type": "resolved",
                "incident_name": prev.get("name", "Unknown Incident"),
                "status": "resolved",
                "impact": prev.get("impact", "none"),
                "components": prev.get("components", []),
                "message": "Incident no longer appears in the status feed.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    return events