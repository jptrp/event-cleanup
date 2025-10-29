#!/usr/bin/env python3
"""Small smoke script to demonstrate and manually exercise compact_events.

Run: python scripts/run_smoke.py

This script is intentionally lightweight and modifies sys.path so it works
from the repository root without installing the package.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any


def ensure_src_on_path() -> None:
    # Add the repo's `src` directory to sys.path so `import event_compactor` works
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


ensure_src_on_path()

try:
    from event_compactor import compact_events
except Exception as exc:  # pragma: no cover - smoke script only
    print("Failed to import event_compactor from src/; have you activated a venv or installed the package?")
    raise


EXAMPLE_EVENTS: list[dict[str, Any]] = [
    {
        "event_id": "p1",
        "entity_id": "e1",
        "op": "upsert",
        "ts": "2025-01-01T00:00:00Z",
        "payload": {"a": 1, "b": 2},
    },
    {
        "event_id": "p2",
        "entity_id": "e1",
        "op": "update",
        "ts": "2025-01-01T00:00:01Z",
        "payload": {"$set": {"b": 5, "c": 9}},
    },
    {
        "event_id": "p3",
        "entity_id": "e1",
        "op": "update",
        "ts": "2025-01-01T00:00:02Z",
        "payload": {"$unset": ["a"]},
    },
    {
        "event_id": "d1",
        "entity_id": "x",
        "op": "upsert",
        "ts": "2025-01-01T00:00:00Z",
        "payload": {"a": 1},
    },
    {
        "event_id": "d2",
        "entity_id": "x",
        "op": "delete",
        "ts": "2025-01-01T00:00:01Z",
    },
]


def pretty_print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def main() -> int:
    print("Running smoke demo for event_compactor.compact_events()")
    cleaned, errors = compact_events(EXAMPLE_EVENTS)

    print("\nCompacted events:")
    pretty_print(cleaned)

    if errors:
        print("\nErrors:")
        pretty_print(errors)
        # non-zero exit to signal something unexpected happened
        return 2

    # Basic, explicit smoke assertions to catch catastrophic regressions quickly
    try:
        assert any(e.get("op") == "upsert" for e in cleaned) or any(e.get("op") == "delete" for e in cleaned)
    except AssertionError:
        print("Smoke assertion failed: expected at least one upsert or delete in result")
        return 3

    print("\nSmoke run OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
