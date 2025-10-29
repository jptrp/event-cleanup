# Event Cleanup: Dedupe & Compaction

[![CI](https://github.com/jptrp/event-cleanup/actions/workflows/python-tests.yml/badge.svg)](https://github.com/jptrp/event-cleanup/actions)

See the QA handoff document in `docs/QA_Handoff.md` for a runnable checklist and examples.

Goal: Given a list (stream batch) of event objects, produce a cleaned, idempotent list that:

- Drops malformed events
- De-duplicates by `event_id`
- Compacts multiple events per entity to a single, final event for the batch, preserving correctness even with out-of-order arrivals
- Applies simple patch semantics
- Produces deterministic output (idempotent)

## Event schema (normalized)

```jsonc
{
  "event_id": "uuid-or-snowflake-string",     // required, used for exact dedupe
  "entity_id": "string",                       // required
  "op": "create" | "update" | "upsert" | "delete",   // required
  "ts": "2025-10-29T14:00:00Z" | 1730210400,   // ISO8601 or UNIX epoch seconds
  "version": 7,                                // optional, monotonically increasing per entity
  "payload": {                                 // optional; for delete can be omitted
    // arbitrary fields OR patch form:
    "$set": { "field": "value", ... },
    "$unset": ["fieldA", "fieldB"]
  }
}
```

### Assumptions & tradeoffs

- No external store: compaction happens within the given batch. You may provide `prior_state` if you have known latest entity states from storage.
- Version vs timestamp: if `version` is present for events of an entity, ordering is by `(version asc, ts asc)`. Otherwise by `ts asc`.
- Patch semantics: if `payload` has `$set`/`$unset`, we apply it to the rolling state; otherwise we treat `payload` as the full state for that event.
- Unknown prior state: if only patches are present and `prior_state` lacks that entity, we apply them to an empty dict (best-effort).
- Delete wins: if the last effective op is `delete`, the compacted result for that entity is a single `delete` event (no payload).
- Deterministic output: output events are sorted by their final `(final_ts, entity_id)` for stable ordering.
- Malformed handling: events missing required fields or with invalid types are returned in `errors` with a reason and skipped.

## API

```python
from event_compactor import compact_events

cleaned, errors = compact_events(events, prior_state=None)
```

- `events`: list of dicts matching the schema above
- `prior_state`: optional dict of `entity_id -> dict` to seed compaction for patch application

## Returns

- `cleaned`: list of normalized, compacted event dicts
- `errors`: list of `{event, reason}` dicts

## Running tests

Run the test suite locally:

```bash
pytest -q
```

## Example

See `tests/test_event_compactor.py` for concrete examples and expectations.

Quick demo
----------

Run a small demo of the compactor without installing the package:

```bash
python scripts/run_smoke.py
```

Or use the Makefile target (if you prefer make):

```bash
make smoke
```
