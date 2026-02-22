from datetime import datetime, timezone


def handle_event(provider_name: str, event: dict):
    """
    Print a detected status change event in the required format.
    Swap print() for Slack/email/webhook as needed.
    """
    raw_ts = event.get("timestamp")
    try:
        dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        formatted_ts = dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, AttributeError):
        formatted_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    components = event.get("components", [])
    product_str = ", ".join(components) if components else "Unknown Product"

    event_type_label = {
        "new_incident": "🔴 NEW INCIDENT",
        "incident_updated": "🟡 UPDATED",
        "resolved": "🟢 RESOLVED",
    }.get(event.get("type"), "ℹ️ UPDATE")

    print(
        f"\n{event_type_label} [{formatted_ts}] "
        f"Product: {provider_name} - {product_str} "
        f"Status: {event.get('status', 'unknown')} — {event.get('message')}"
    )