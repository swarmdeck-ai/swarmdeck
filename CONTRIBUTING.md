# Contributing

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Scope

SwarmDeck Phase 1 is intentionally narrow:

- improve Observatory tracing
- keep storage local-first
- maintain framework-agnostic APIs
- prefer additive integrations over framework lock-in

## Pull Requests

- keep the public API small
- add tests for every behavioral change
- update `README.md` when usage changes
- prefer backwards-compatible schema changes for the SQLite store
