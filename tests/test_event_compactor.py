import pytest
from event_compactor import compact_events, normalize_iso8601
from datetime import datetime, timezone

def ts(s: str) -> str:
    return s

def test_dedupe_by_event_id():
    events = [
        {"event_id":"a1","entity_id":"u1","op":"upsert","ts":ts("2025-01-01T00:00:00Z"),"payload":{"x":1}},
        {"event_id":"a1","entity_id":"u1","op":"update","ts":ts("2025-01-01T00:00:01Z"),"payload":{"x":2}},
        {"event_id":"a2","entity_id":"u1","op":"update","ts":ts("2025-01-01T00:00:02Z"),"payload":{"x":3}},
    ]
    out, errs = compact_events(events)
    assert errs == []
    assert len(out) == 1
    assert out[0]["entity_id"] == "u1"
    assert out[0]["op"] == "upsert"
    assert out[0]["payload"]["x"] == 3

def test_malformed_events_are_reported():
    events = [
        {"event_id":"ok","entity_id":"e1","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"a":1}},
        {"entity_id":"e2","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"a":1}},
        {"event_id":"bad","entity_id":"e3","op":"weird","ts":"2025-01-01T00:00:00Z"},
        {"event_id":"bad2","op":"upsert","ts":"2025-01-01T00:00:00Z"},
    ]
    out, errs = compact_events(events)
    assert len(errs) == 3
    assert len(out) == 1
    assert out[0]["entity_id"] == "e1"

def test_compaction_with_patch_semantics():
    events = [
        {"event_id":"p1","entity_id":"e1","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"a":1,"b":2}},
        {"event_id":"p2","entity_id":"e1","op":"update","ts":"2025-01-01T00:00:01Z","payload":{"$set":{"b":5,"c":9}}},
        {"event_id":"p3","entity_id":"e1","op":"update","ts":"2025-01-01T00:00:02Z","payload":{"$unset":["a"]}},
    ]
    out, errs = compact_events(events)
    assert errs == []
    assert len(out) == 1
    final = out[0]
    assert final["payload"] == {"b":5, "c":9}

def test_delete_wins():
    events = [
        {"event_id":"d1","entity_id":"x","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"a":1}},
        {"event_id":"d2","entity_id":"x","op":"delete","ts":"2025-01-01T00:00:01Z"},
        {"event_id":"d3","entity_id":"x","op":"upsert","ts":"2025-01-01T00:00:02Z","payload":{"a":2}},
    ]
    events[2]["ts"] = "2024-12-31T23:59:59Z"
    out, errs = compact_events(events)
    assert errs == []
    assert len(out) == 1
    final = out[0]
    assert final["op"] == "delete"

def test_version_ordering_over_ts():
    events = [
        {"event_id":"v1","entity_id":"eV","op":"update","ts":"2025-01-01T00:00:10Z","version":1,"payload":{"x":1}},
        {"event_id":"v2","entity_id":"eV","op":"update","ts":"2025-01-01T00:00:05Z","version":2,"payload":{"x":2}},
    ]
    out, errs = compact_events(events)
    assert errs == []
    assert len(out) == 1
    assert out[0]["payload"]["x"] == 2

def test_prior_state_is_used():
    prior = {"eP":{"a":1,"b":2}}
    events = [
        {"event_id":"pp1","entity_id":"eP","op":"update","ts":"2025-01-01T00:00:00Z","payload":{"$unset":["b"]}},
        {"event_id":"pp2","entity_id":"eP","op":"update","ts":"2025-01-01T00:00:01Z","payload":{"$set":{"c":3}}},
    ]
    out, errs = compact_events(events, prior_state=prior)
    assert errs == []
    assert out[0]["payload"] == {"a":1,"c":3}

def test_multi_entity_outputs_both_compacted():
    events = [
        {"event_id":"m1","entity_id":"A","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"x":1}},
        {"event_id":"m2","entity_id":"B","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"y":2}},
        {"event_id":"m3","entity_id":"A","op":"update","ts":"2025-01-01T00:00:01Z","payload":{"x":2}},
    ]
    out, errs = compact_events(events)
    assert errs == []
    assert len(out) == 2
    by_id = {e["entity_id"]: e for e in out}
    assert by_id["A"]["payload"]["x"] == 2
    assert by_id["B"]["payload"]["y"] == 2

def test_duplicate_versions_are_collapsed():
    events = [
        {"event_id":"dv1","entity_id":"E","op":"update","ts":"2025-01-01T00:00:00Z","version":1,"payload":{"a":1}},
        {"event_id":"dv2","entity_id":"E","op":"update","ts":"2025-01-01T00:00:01Z","version":1,"payload":{"a":2}},
        {"event_id":"dv3","entity_id":"E","op":"update","ts":"2025-01-01T00:00:02Z","version":2,"payload":{"a":3}},
    ]
    out, errs = compact_events(events)
    assert errs == []
    assert out[0]["payload"]["a"] == 3

def test_non_dict_payload_is_malformed():
    events = [
        {"event_id":"x1","entity_id":"bad","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":["not","dict"]},
    ]
    out, errs = compact_events(events)
    assert len(errs) == 1
    assert out == []
