## Quick orientation for AI contributors

This repository implements a small, self-contained event dedupe & compaction utility. Keep changes minimal, test-driven, and consistent with the existing patterns in `src/event_compactor.py` and `tests/test_event_compactor.py`.

Key files
- `src/event_compactor.py` — single module containing the core logic: `NormalizedEvent`, `_parse_ts`, `compact_events`, `_merge_state`, and helpers. Most edits should live here.
- `tests/test_event_compactor.py` — pytest tests that encode the expected behavior (dedupe, patch semantics, delete wins, version ordering, prior_state usage).
- `README.md` — canonical schema, assumptions, and example API usage.

Important behavior to preserve (do not change silently)
- Input validation: `NormalizedEvent.from_obj` raises on malformed events; `compact_events` collects those into an `errors` list and continues. Preserve that external contract (return `(compacted, errors)`).
- Ordering: If any event for an entity has `version`, ordering is by `(version asc, ts asc)`. Otherwise ordering is by `ts asc`.
- Patch semantics: payloads using `$set` / `$unset` are applied as patches via `_apply_patch`; otherwise a `payload` is treated as a full state replacement.
- Delete semantics: a final `delete` for an entity results in a single `op: delete` event with no payload.
- Determinism: output is sorted by `(ts, entity_id)` and event ids are derived deterministically from the final entity state (see hash generation in `compact_events`). Keep deterministic outputs for tests to remain stable.

Testing & workflow
- Run tests with `pytest -q`. The repository uses `pyproject.toml` pytest settings where `pythonpath = ["src"]` so imports use `event_compactor` directly.
- Python requirement: see `pyproject.toml` (requires Python >= 3.10). There are no external runtime dependencies declared.

Style & implementation notes
- Small, pure functions are preferred. Existing code uses dataclasses and small helpers; follow that style for readability and testability.
- Errors are reported as a list of `{"event": <original>, "reason": <str>}` — follow the same shape when adding new validation checks.
- Avoid changing public API shape of `compact_events(events, prior_state=None) -> (list, list)` unless tests are updated accordingly.

Examples from this repo to reference
- Use `compact_events` as the single entry point (see `README.md` and tests).
- Timestamp parsing supports both UNIX epoch seconds (int/float) and several ISO8601 formats (see `_parse_ts`). When adding formats, preserve timezone-to-UTC behavior.

When to change tests
- If you intentionally change observable behavior (ordering, event id derivation, schema), update `tests/test_event_compactor.py` and explain why in the PR description. Keep changes minimal and explicit.

If you need clarification
- Ask for which behavior to preserve (ordering, patch semantics, deterministic event_id). If you plan a breaking change (API or output shape), outline a migration plan and update tests accordingly.

Thanks — after edits run `pytest -q` and include failing test output in the PR if anything is unexpected.

## PR checklist (for humans and agents)

- Run tests locally: `pytest -q` (see `pyproject.toml` for pytest config).
- If you change observable behavior (ordering, event_id derivation, schema), update `tests/test_event_compactor.py` and include a short migration note in the PR description explaining why the change is needed.
- Keep edits small and focused. Prefer adding a test that demonstrates the change before modifying logic.
- Commit message: concise imperative style, e.g. `fix: handle iso8601 ms parsing` or `feat: support new $unset format`.

## Concrete examples (copyable)

1) Patch semantics (input → expected compacted output)

Input events:

```json
[ {"event_id":"p1","entity_id":"e1","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"a":1,"b":2}},
  {"event_id":"p2","entity_id":"e1","op":"update","ts":"2025-01-01T00:00:01Z","payload":{"$set":{"b":5,"c":9}}},
  {"event_id":"p3","entity_id":"e1","op":"update","ts":"2025-01-01T00:00:02Z","payload":{"$unset":["a"]}} ]
```

Expected single compacted event (upsert):

```json
{ "entity_id": "e1", "op": "upsert", "payload": {"b":5, "c":9} }
```

2) Delete wins (out-of-order timestamps are handled by version/ts rules)

Input events (note the third event has an earlier ts but arrives last):

```json
[ {"event_id":"d1","entity_id":"x","op":"upsert","ts":"2025-01-01T00:00:00Z","payload":{"a":1}},
  {"event_id":"d2","entity_id":"x","op":"delete","ts":"2025-01-01T00:00:01Z"},
  {"event_id":"d3","entity_id":"x","op":"upsert","ts":"2024-12-31T23:59:59Z","payload":{"a":2}} ]
```

Expected compacted event:

```json
{ "entity_id": "x", "op": "delete" }
```

These examples are taken from `tests/test_event_compactor.py` — if you change behavior, update those tests.
