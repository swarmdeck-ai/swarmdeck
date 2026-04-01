# SwarmDeck

**The missing operations layer for AI agent teams.**

SwarmDeck is a framework-agnostic observability and coordination toolkit for multi-agent AI systems. It works with LangGraph, CrewAI, AutoGen, Claude Code, OpenAI Agents SDK, and raw API calls — no framework lock-in. One decorator gives you tracing, cost attribution, and session replay. The open Handoff Protocol gives your agents a standard way to delegate, acknowledge, and report back.

We built SwarmDeck because we run a 5-agent production team and needed tooling that none of the existing solutions provided: framework-agnostic tracing, structured handoffs, and shared operational context.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/swarmdeck.svg)](https://pypi.org/project/swarmdeck/)

## Quick Start

```bash
pip install swarmdeck
```

```python
from swarmdeck import trace, observatory

@trace(agent="researcher", team="content")
def research(topic):
    return call_llm(f"Research {topic}")

@trace(agent="writer", team="content")
def write(data):
    return call_llm(f"Write article from {data}")

with observatory.session("weekly-report"):
    article = write(research("AI agents"))

observatory.flush()
print(f"Traces at: {observatory.database_path}")
```

That's it. No config files, no environment variables, no setup. Traces are stored locally in `~/.swarmdeck/traces.db`.

## Why SwarmDeck?

Every major lab ships an agent framework. Nobody ships the operational tooling around it.

| Problem | What exists today | SwarmDeck |
|---|---|---|
| **Debugging multi-agent flows** | "Logging multi-agent conversations is a huge pain" | Live timeline with parent-child span hierarchy |
| **Framework lock-in** | LangSmith only works with LangChain. CrewAI Enterprise only works with CrewAI. | One SDK, auto-detects your framework |
| **Agent coordination** | Ad-hoc messages, shared state blobs, no standard | Open Handoff Protocol with ACK/reject/progress/done lifecycle |
| **"What happened" vs "Why"** | Tools show call logs and costs | Decision traces capture reasoning, not just API calls |

## Competitors

| Capability | SwarmDeck | AgentOps | LangSmith | Helicone | W&B Weave | CrewAI Ent. |
|---|---|---|---|---|---|---|
| Framework-agnostic | **Yes** | Partial | No | Yes (LLM-level) | Partial | No |
| Agent-level tracing | **Yes** | Yes | Yes | No | Yes | Yes |
| Handoff protocol | **Yes (open RFC)** | No | No | No | No | No |
| Open source (MIT) | **Yes** | Partial | No | Yes | Partial | No |
| Self-hostable | **Yes** | Enterprise | Enterprise | Yes | Enterprise | Enterprise |
| OTel-compatible | **Yes** | No | Yes | No | No | Yes |
| Zero dependencies | **Yes** | No | No | No | No | No |

## Features

### Observatory SDK

- **`@trace` decorator** — one line to instrument any function (sync and async)
- **Sessions** — group spans into logical workflows with `observatory.session()`
- **Zero runtime dependencies** — core SDK uses only Python stdlib
- **< 5ms overhead** — async trace emission via background thread
- **SQLite storage** — local-first, all data stays on your machine
- **Framework detection** — auto-detects CrewAI, LangGraph, AutoGen
- **OpenTelemetry export** — `pip install swarmdeck[otel]` for any OTel backend
- **Parent-child spans** — nested `@trace` calls create span hierarchies automatically
- **Error capture** — exceptions recorded with type and message, then re-raised

### Handoff Protocol (Open RFC)

A standard for structured agent-to-agent task delegation:

```python
from swarmdeck.handoff import HandoffManager, Agent

oscar = HandoffManager(agent=Agent(agent="oscar", framework="claude-code"))
paul = HandoffManager(agent=Agent(agent="paul", framework="claude-code"))

# Oscar delegates a task
request = oscar.create_handoff(
    to=Agent(agent="paul"),
    description="Fix the webhook cron failure",
    context={"error": "EAGAIN -11", "failing_since": "2026-03-21"},
    priority="high",
)

# Paul accepts and completes
paul.accept(request.id)
paul.complete(request.id, summary="Fixed stale path in ROOT constant")
```

Four message types: `handoff.request`, `handoff.ack`, `handoff.progress`, `handoff.done`. Six-state lifecycle. Transport-agnostic (file-based default, Redis, HTTP/webhook, custom). Full spec: [`docs/HANDOFF-PROTOCOL-RFC.md`](docs/HANDOFF-PROTOCOL-RFC.md).

## API Reference

### Tracing

```python
from swarmdeck import trace

# With parameters
@trace(agent="paul", team="ops", operation="health-check")
def check_health(): ...

# Bare decorator
@trace
def my_function(): ...
```

### Sessions

```python
from swarmdeck import observatory

with observatory.session("deployment", environment="prod") as s:
    deploy()
    verify()

print(s.duration_ms)
```

### Querying

```python
spans = observatory.query(agent="researcher", limit=20)
errors = observatory.query(status="error")
sessions = observatory.sessions(limit=10)
```

### OTel Export

```python
observatory.write_otel("traces.json", agent="researcher")
payload = observatory.export_otel(session_id="abc123")
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SWARMDECK_DB_PATH` | `~/.swarmdeck/traces.db` | SQLite database location |
| `SWARMDECK_DEBUG` | `0` | Set to `1` to print traces to stderr |

## Development

```bash
git clone https://github.com/swarmdeck-ai/swarmdeck.git
cd swarmdeck
pip install -e ".[dev]"
pytest  # 69 tests
```

## Roadmap

- **Phase 1 (now):** Observatory SDK + Handoff Protocol
- **Phase 2:** Config-as-Code, session replay, TypeScript SDK
- **Phase 3:** Memory Bus (shared agent memory with concurrency control)
- **Phase 4:** Hosted dashboard, enterprise features

## License

MIT
