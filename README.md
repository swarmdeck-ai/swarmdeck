# SwarmDeck

SwarmDeck is a framework-agnostic observability layer for AI agent teams.

Phase 1 delivers the Observatory SDK for Python:

- `@trace` decorator-based tracing
- Session context managers for grouped workflow runs
- Local-first SQLite storage
- Async trace emission designed to stay off the agent hot path
- Framework auto-detection for CrewAI, LangGraph, and AutoGen
- OpenTelemetry-compatible OTLP JSON export
- An OpenClaw dog-food example that traces Oscar/Paul/Rick/Sandra-style handoffs

## Install

```bash
pip install swarmdeck
```

For local development:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Quick Start

```python
from swarmdeck import observatory, trace

@trace(agent="researcher", team="content")
def research(query: str) -> str:
    return f"researched:{query}"

with observatory.session("weekly-report", owner="oscar"):
    research("trace our pipeline")

observatory.flush()
print(observatory.query(limit=5))
```

## API

### Decorator-based tracing

```python
from swarmdeck import trace

@trace(agent="paul", team="openclaw", operation="paul.verify")
def verify_gateway(label: str) -> str:
    return f"{label}:ok"
```

### Session context manager

```python
from swarmdeck import observatory

with observatory.session("openclaw-daily-cycle", owner="oscar", priority="high"):
    ...
```

### Query stored traces

```python
spans = observatory.query(agent="paul", limit=20)
sessions = observatory.sessions(limit=10)
```

### Export OTLP JSON

```python
observatory.write_otel(
    "artifacts/openclaw.json",
    resource_attributes={"service.name": "openclaw-team"},
)
```

## OpenClaw Dog-Food Example

Run the example handoff flow:

```bash
PYTHONPATH=src python3 examples/openclaw_team.py
```

It traces a simple Oscar -> Paul -> Sandra -> Rick style workflow and writes:

- a local SQLite database
- an OTLP JSON export for downstream tooling

## Framework Detection

SwarmDeck detects common agent frameworks when installed in the environment:

- CrewAI
- LangGraph
- AutoGen

Detection is passive. You do not need to configure adapters to use the core tracing SDK.

## Repository Layout

```text
src/swarmdeck/          Python SDK
examples/               Dog-food integration examples
tests/                  Unit coverage for tracing, storage, and export
```

## Status

This repository is currently the Phase 1 Observatory implementation described in the SwarmDeck spec. Handoff Protocol, Memory Bus, Config-as-Code, and Replay remain later phases.
