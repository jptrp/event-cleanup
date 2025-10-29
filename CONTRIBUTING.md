Contributing
============

Quick development notes for contributors (humans and AI agents).

Setup (macOS / zsh)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install pytest
```

Run tests

```bash
pytest -q
```

Run a single test or test function

```bash
pytest tests/test_event_compactor.py::test_compaction_with_patch_semantics -q
```

Notes

- The project relies on `pyproject.toml` to set `pythonpath = ["src"]` for pytest, so you can import `event_compactor` directly in tests and REPLs.
- Target Python is 3.10+ (see `pyproject.toml`).
- Keep changes minimal and add/update tests when altering observable behavior (ordering, hash/event_id derivation, schema).
