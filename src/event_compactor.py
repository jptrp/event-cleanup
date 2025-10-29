from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple, Set

ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
)

def _parse_ts(ts: Any) -> datetime:
    if isinstance(ts, (int, float)):
        # treat as unix seconds
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    if isinstance(ts, str):
        # try ISO8601 zulu or naive
        s = ts.strip()
        # Fast path for 'Z'
        if s.endswith("Z"):
            s = s[:-1]
            # Try with microseconds, then seconds
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
        # Fallback try a few known formats as UTC
        for fmt in ISO_FORMATS:
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    raise ValueError("Invalid ts format")

def normalize_iso8601(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    entity_id: str
    op: str    # 'upsert' or 'delete'
    ts: datetime
    version: Optional[int]
    payload: Optional[Dict[str, Any]]

    @staticmethod
    def from_obj(o: Dict[str, Any]) -> "NormalizedEvent":
        # Validate required fields
        missing = [k for k in ("event_id", "entity_id", "op", "ts") if k not in o]
        if missing:
            raise KeyError(f"Missing required fields: {missing}")
        event_id = str(o["event_id"]).strip()
        entity_id = str(o["entity_id"]).strip()
        op_raw = str(o["op"]).lower().strip()
        op = "upsert" if op_raw in ("create", "update", "upsert") else op_raw
        if op not in ("upsert", "delete"):
            raise ValueError(f"Invalid op: {o['op']}")
        ts = _parse_ts(o["ts"])
        version = None
        if "version" in o and o["version"] is not None:
            try:
                version = int(o["version"])
            except Exception as e:
                raise ValueError("version must be int") from e
        payload = o.get("payload", None)
        if payload is not None and not isinstance(payload, dict):
            raise ValueError("payload must be dict when present")
        return NormalizedEvent(
            event_id=event_id,
            entity_id=entity_id,
            op=op,
            ts=ts,
            version=version,
            payload=payload,
        )

    def to_obj(self) -> Dict[str, Any]:
        d = {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "op": self.op,
            "ts": normalize_iso8601(self.ts),
        }
        if self.version is not None:
            d["version"] = self.version
        if self.op == "upsert" and self.payload is not None:
            d["payload"] = self.payload
        return d

def _apply_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(state) if state is not None else {}
    if "$set" in patch and isinstance(patch["$set"], dict):
        for k, v in patch["$set"].items():
            out[k] = v
    if "$unset" in patch:
        unset = patch["$unset"]
        if isinstance(unset, dict):
            keys = [k for k, flag in unset.items() if flag]
        elif isinstance(unset, list):
            keys = unset
        else:
            keys = []
        for k in keys:
            out.pop(k, None)
    return out

def _merge_state(current: Optional[Dict[str, Any]], payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if payload is None:
        return dict(current) if current is not None else {}
    if any(k in payload for k in ("$set", "$unset")):
        return _apply_patch(current or {}, payload)
    return dict(payload)

def compact_events(
    events: Iterable[Dict[str, Any]],
    prior_state: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    prior_state = prior_state or {}
    errors: List[Dict[str, Any]] = []
    normalized: List[NormalizedEvent] = []
    seen_event_ids: Set[str] = set()

    for e in events:
        try:
            ne = NormalizedEvent.from_obj(e)
        except Exception as ex:
            errors.append({"event": e, "reason": f"malformed: {ex}"})
            continue
        if ne.event_id in seen_event_ids:
            continue
        seen_event_ids.add(ne.event_id)
        normalized.append(ne)

    by_entity: Dict[str, List[NormalizedEvent]] = {}
    for ne in normalized:
        by_entity.setdefault(ne.entity_id, []).append(ne)

    compacted: List[Dict[str, Any]] = []

    for entity_id, items in by_entity.items():
        has_versions = any(i.version is not None for i in items)
        if has_versions:
            items_sorted = sorted(items, key=lambda x: (x.version if x.version is not None else -1, x.ts))
        else:
            items_sorted = sorted(items, key=lambda x: x.ts)

        state = dict(prior_state.get(entity_id, {})) if prior_state else {}
        last_ts = max(i.ts for i in items_sorted) if items_sorted else None
        last_version = None
        last_op = None

        seen_versions: Set[int] = set()

        for ne in items_sorted:
            if ne.version is not None:
                if ne.version in seen_versions:
                    pass
                seen_versions.add(ne.version)
                last_version = ne.version
            last_ts = ne.ts if (last_ts is None or ne.ts >= last_ts) else last_ts

            if ne.op == "delete":
                state = {}
                last_op = "delete"
            else:
                state = _merge_state(state, ne.payload)
                last_op = "upsert"

        base = f"{entity_id}|{int(last_ts.timestamp()) if last_ts else 0}|{last_version if last_version is not None else ''}|{last_op or ''}"
        import hashlib
        event_id = hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

        from datetime import datetime, timezone
        final_ts = last_ts or datetime.now(tz=timezone.utc)
        if last_op == "delete":
            compacted.append({
                "event_id": event_id,
                "entity_id": entity_id,
                "op": "delete",
                "ts": normalize_iso8601(final_ts),
            })
        else:
            compacted.append({
                "event_id": event_id,
                "entity_id": entity_id,
                "op": "upsert",
                "ts": normalize_iso8601(final_ts),
                "payload": state,
            })

    compacted.sort(key=lambda d: (d["ts"], d["entity_id"]))
    return compacted, errors
