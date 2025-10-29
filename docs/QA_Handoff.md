````markdown
# 🧪 QA Handoff Document  
**Project:** Event Cleanup – Dedupe & Compaction  
**Component:** `event_compactor.py`  
**Owner:** Backend / Data Engineering  
**Tester:** QA Engineering  
**Date:** October 2025  


## 📘 Overview

This module performs **robust event deduplication and compaction** for data streams (e.g., Kafka, Pub/Sub, API ingestion). It ensures each batch of incoming events is cleaned, validated, deduplicated, and compacted into deterministic, idempotent output.  

**Primary Goal:**  
Guarantee that repeated, out-of-order, or malformed events do not cause inconsistent downstream state.


## 🎯 QA Objective

Validate that the event compaction logic:
 # 🧪 QA Handoff Document

 **Project:** Event Cleanup – Dedupe & Compaction

 **Component:** `event_compactor.py`

 **Owner:** Backend / Data Engineering

 **Tester:** QA Engineering

 **Date:** October 2025

 ---

 ## 📘 Overview

 This module performs **robust event deduplication and compaction** for data streams (e.g., Kafka, Pub/Sub, API ingestion). It ensures each batch of incoming events is cleaned, validated, deduplicated, and compacted into deterministic, idempotent output.

 **Primary Goal:**

 Guarantee that repeated, out-of-order, or malformed events do not cause inconsistent downstream state.

 ---

 ## 🎯 QA Objective

 Validate that the event compaction logic:
 1. Produces correct results across all edge cases.
 2. Is **idempotent** — repeated runs yield identical outputs.
 3. Handles malformed, duplicate, and out-of-order events correctly.
 4. Maintains consistent ordering semantics based on version and timestamp.
 5. Produces deterministic output ordering and stable event IDs.

 ---

 ## ⚙️ Functional Summary

 | **Feature** | **Description** |
 |--------------|----------------|
 | **Deduplication** | Drops repeated events with identical `event_id`. |
 | **Validation** | Rejects malformed events missing required fields or invalid data. |
 | **Normalization** | Standardizes timestamps and operation names (`create`/`update` → `upsert`). |
 | **Patch Semantics** | Applies `$set` and `$unset` incremental changes in payloads. |
 | **Compaction** | Groups all events per `entity_id` and merges them to one final result. |
 | **Delete Handling** | If the latest op is `delete`, removes entity payload. |
 | **Idempotency** | Deterministic hashing of entity + time ensures identical results per run. |
 | **Error Reporting** | Returns all malformed or dropped events with reasons, non-fatal. |

 ---

 ## 🧪 Test Environment

 **Dependencies**

 - Python 3.10+
 - `pytest`

 **Setup**

 ```bash
 python -m venv .venv
 source .venv/bin/activate
 python -m pip install --upgrade pip
 pip install pytest
 pytest -q
 ```

 **Project structure**

 ```
 event-cleanup/
 ├── src/
 │   └── event_compactor.py
 ├── tests/
 │   └── test_event_compactor.py
 ├── README.md
 └── pyproject.toml
 ```

 ---

 ## 🧠 Test Scenarios & Expected Results

 | **#** | **Scenario** | **Input / Condition** | **Expected Behavior** |
 |--------|---------------|-----------------------|------------------------|
 | 1 | **Duplicate Event IDs** | Same `event_id` appears multiple times. | Later duplicates are ignored. |
 | 2 | **Malformed Events** | Missing `event_id`, `entity_id`, or invalid `op`. | Event logged in `errors` list; excluded from output. |
 | 3 | **Patch Merge ($set / $unset)** | `$set` or `$unset` payload updates existing fields. | Applies correctly, previous fields persist or are removed. |
 | 4 | **Delete Event** | `op: delete` appears latest. | Entity compacted to single delete event (no payload). |
 | 5 | **Version Priority** | Events contain `version` values. | Higher version supersedes older ones, even with earlier timestamp. |
 | 6 | **Prior State Merge** | Provided `prior_state` dict. | State merges correctly before patch application. |
 | 7 | **Multiple Entities** | Batch contains multiple `entity_id` values. | Each entity produces exactly one compacted event. |
 | 8 | **Non-Dict Payloads** | Payload is a list or string. | Event rejected as malformed with reason. |
 | 9 | **Determinism Check** | Run identical input twice. | Bit-for-bit identical outputs. |
 | 10 | **Out-of-Order Events** | Older timestamps appear after newer ones. | Output reflects logical ordering by timestamp/version. |

 ---

 ## 🧾 Manual Verification Checklist

 | ✅ | **Step** | **Verification** |
 |-----|-----------|-----------------|
 | [ ] | Run `pytest -v` | All automated tests pass. |
 | [ ] | Inspect `errors` return | Malformed events clearly listed with reasons. |
 | [ ] | Modify input timestamps | Re-run produces consistent ordering. |
 | [ ] | Add duplicate versions | Later timestamp for same version overrides previous. |
 | [ ] | Check determinism | Identical output after multiple executions. |

 ---

 ## ⚖️ Edge Case Testing

 Additional stress or exploratory test ideas:

 - Invalid timestamp formats (ISO, epoch mix).
 - Missing payloads or empty events.
 - Very large event batches (e.g., >10,000).
 - Simulate conflicting patches on same field.
 - Ensure timestamp sorting is stable when identical.

 ---

 ## 📊 Acceptance Criteria

 1. **All test cases pass** in automated suite.
 2. **Idempotency confirmed** — repeated runs yield identical results.
 3. **Error handling functional** — malformed data never crashes compaction.
 4. **Output ordering stable** — sorted by `(ts, entity_id)` consistently.
 5. **Performance acceptable** — compaction completes under 3 seconds for 10K events.

 ---

 ## 📦 Deliverables

 - `src/event_compactor.py` — core logic
 - `tests/test_event_compactor.py` — QA regression coverage
 - `README.md` — usage, schema, assumptions
 - `pyproject.toml` — test config

 ---

 ## 🗂️ Reporting

 **If a defect is found**, report:

 - Minimal reproducible event set (list of JSON objects)
 - Observed vs expected output
 - Python version & environment info

 Submit findings via the project issue tracker or QA report template.
