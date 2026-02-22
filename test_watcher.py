"""
test_watcher.py — Simulates all three alert types to verify the watcher logic.
Run with: python test_watcher.py
"""

from watcher.differ import diff_incidents
from watcher.handler import handle_event

PROVIDER = "Test Provider"

# ── Fake incident data ──────────────────────────────────────────────────────

INCIDENT_A = {
    "id": "inc_001",
    "name": "API Latency Degradation",
    "status": "investigating",
    "impact": "major",
    "components": [{"name": "API"}, {"name": "Dashboard"}],
    "incident_updates": [
        {"body": "We are investigating elevated latency.", "created_at": "2025-01-01T10:00:00Z"}
    ],
}

INCIDENT_A_UPDATED = {
    **INCIDENT_A,
    "status": "identified",
    "incident_updates": [
        {"body": "Root cause identified. Fix in progress.", "created_at": "2025-01-01T10:30:00Z"},
        {"body": "We are investigating elevated latency.", "created_at": "2025-01-01T10:00:00Z"},
    ],
}

# ── Test 1: New Incident ────────────────────────────────────────────────────

print("=" * 60)
print("TEST 1: New incident appears")
print("=" * 60)

old_state = {}  # nothing known yet
events = diff_incidents(old_state, [INCIDENT_A])
for e in events:
    handle_event(PROVIDER, e)

assert len(events) == 1 and events[0]["type"] == "new_incident", "❌ Test 1 FAILED"
print("✅ Test 1 passed\n")

# ── Test 2: Incident gets an update ────────────────────────────────────────

print("=" * 60)
print("TEST 2: Incident receives a new update")
print("=" * 60)

# old_state reflects what was stored after Test 1
from watcher.state import StateStore
store = StateStore()
store.initialize("url", [INCIDENT_A])
old_state = store.get("url")

events = diff_incidents(old_state, [INCIDENT_A_UPDATED])
for e in events:
    handle_event(PROVIDER, e)

assert len(events) == 1 and events[0]["type"] == "incident_updated", "❌ Test 2 FAILED"
print("✅ Test 2 passed\n")

# ── Test 3: Incident resolved (disappears from feed) ───────────────────────

print("=" * 60)
print("TEST 3: Incident resolved (no longer in feed)")
print("=" * 60)

store.update("url", [INCIDENT_A_UPDATED])
old_state = store.get("url")

events = diff_incidents(old_state, [])  # empty feed = all incidents gone
for e in events:
    handle_event(PROVIDER, e)

assert len(events) == 1 and events[0]["type"] == "resolved", "❌ Test 3 FAILED"
print("✅ Test 3 passed\n")

# ── Test 4: No change ──────────────────────────────────────────────────────

print("=" * 60)
print("TEST 4: No changes (steady state)")
print("=" * 60)

store.update("url", [INCIDENT_A_UPDATED])
old_state = store.get("url")

events = diff_incidents(old_state, [INCIDENT_A_UPDATED])
assert len(events) == 0, "❌ Test 4 FAILED"
print("  (no events fired — correct)")
print("✅ Test 4 passed\n")

print("=" * 60)
print("TEST 5: Already-resolved incident on startup is silently skipped")
print("=" * 60)

INCIDENT_ALREADY_RESOLVED = {
    "id": "inc_old",
    "name": "Old Outage (already fixed)",
    "status": "resolved",
    "impact": "minor",
    "components": [{"name": "API"}],
    "incident_updates": [
        {"body": "Resolved.", "created_at": "2024-12-01T08:00:00Z"}
    ],
}

events = diff_incidents({}, [INCIDENT_ALREADY_RESOLVED])
assert len(events) == 0, "❌ Test 5 FAILED"
print("  (no events fired — correct, already resolved at baseline)")
print("✅ Test 5 passed\n")

# ── Test 6: Status transitions directly to resolved ────────────────────────

print("=" * 60)
print("TEST 6: Active incident status transitions to resolved")
print("=" * 60)

INCIDENT_A_RESOLVED = {
    **INCIDENT_A,
    "status": "resolved",
    "incident_updates": [
        {"body": "Issue resolved. All systems operational.", "created_at": "2025-01-01T11:00:00Z"},
        {"body": "Root cause identified. Fix in progress.", "created_at": "2025-01-01T10:30:00Z"},
    ],
}

store.update("url", [INCIDENT_A_UPDATED])
old_state = store.get("url")

events = diff_incidents(old_state, [INCIDENT_A_RESOLVED])
for e in events:
    handle_event(PROVIDER, e)

assert len(events) == 1 and events[0]["type"] == "resolved", "❌ Test 6 FAILED"
print("✅ Test 6 passed\n")

print("=" * 60)
print("All 6 tests passed! ✅")
print("=" * 60)
