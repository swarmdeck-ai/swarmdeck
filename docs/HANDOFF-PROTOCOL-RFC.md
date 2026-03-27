# SwarmDeck Handoff Protocol — RFC Draft 0.1

**Status:** Draft
**Authors:** OpenClaw Team (Oscar, Paul, Rick, Sandra)
**Date:** 2026-03-27
**Target:** LF AI & Data Foundation (submission after Phase 1 adoption)

---

## Abstract

This document specifies the SwarmDeck Handoff Protocol, an open standard for structured agent-to-agent task delegation, acknowledgement, and completion reporting across heterogeneous AI agent frameworks. The protocol is framework-agnostic and transport-agnostic, designed to work between agents built on CrewAI, LangGraph, AutoGen, Claude Code, OpenAI Codex, or custom implementations.

## 1. Motivation

Multi-agent AI systems lack a standard for how agents delegate work to each other. Current approaches range from unstructured text messages to framework-specific internal APIs. This creates:

- **Silent failures** — delegated tasks disappear with no acknowledgement
- **Context loss** — receiving agents lack the information they need
- **No accountability** — no structured way to track who accepted what and when
- **Framework lock-in** — agent coordination only works within a single framework

The SwarmDeck Handoff Protocol addresses these by defining a minimal, structured message format and lifecycle for agent-to-agent task delegation.

## 2. Design Principles

1. **Explicit over implicit** — Every handoff has a structured message, not a side-channel
2. **Acknowledge before work** — Receiving agents must accept or reject before starting
3. **Context is first-class** — Handoffs carry exactly the context needed, no more
4. **Transport-agnostic** — The protocol defines messages, not how they're delivered
5. **Framework-agnostic** — Any agent that can read/write JSON can participate
6. **Minimal surface** — Small number of message types, easy to implement

## 3. Message Format

All handoff messages are JSON objects with a required `type` field and standard metadata.

### 3.1 Handoff Request

Sent by the delegating agent to initiate a task handoff.

```json
{
  "type": "handoff.request",
  "id": "ho_a1b2c3d4e5f6",
  "version": "0.1",
  "from": {
    "agent": "oscar",
    "framework": "claude-code",
    "instance_id": "oscar-main-001"
  },
  "to": {
    "agent": "paul",
    "framework": "claude-code",
    "instance_id": null
  },
  "task": {
    "description": "Fix webhook queue cron failure",
    "context": [
      {"key": "script_path", "value": "/path/to/process-webhook-queue.mjs"},
      {"key": "error", "value": "Unknown system error -11"},
      {"key": "failing_since", "value": "2026-03-21"}
    ],
    "priority": "high",
    "deadline": "2026-03-26T00:00:00Z",
    "labels": ["infra", "cron", "bugfix"]
  },
  "expectations": {
    "output_format": "status_report",
    "confirmation_required": true,
    "artifacts": ["fix_description", "test_result"]
  },
  "created_at": "2026-03-25T22:19:00Z"
}
```

### 3.2 Handoff Acknowledgement

Sent by the receiving agent to accept or reject the handoff.

```json
{
  "type": "handoff.ack",
  "handoff_id": "ho_a1b2c3d4e5f6",
  "from": {
    "agent": "paul",
    "framework": "claude-code"
  },
  "accepted": true,
  "reason": null,
  "estimated_completion": "2026-03-25T23:00:00Z",
  "created_at": "2026-03-25T22:20:00Z"
}
```

For rejections:

```json
{
  "type": "handoff.ack",
  "handoff_id": "ho_a1b2c3d4e5f6",
  "from": {
    "agent": "paul",
    "framework": "claude-code"
  },
  "accepted": false,
  "reason": "Blocked on repo trust confirmation from Charles",
  "suggest_agent": "charles",
  "created_at": "2026-03-25T22:20:00Z"
}
```

### 3.3 Progress Update

Optional message sent during execution.

```json
{
  "type": "handoff.progress",
  "handoff_id": "ho_a1b2c3d4e5f6",
  "from": {
    "agent": "paul"
  },
  "progress_pct": 60,
  "message": "Root cause identified. Fixing stale Desktop path in ROOT constant.",
  "created_at": "2026-03-25T22:25:00Z"
}
```

### 3.4 Handoff Completion

Sent when the task is done (success or failure).

```json
{
  "type": "handoff.done",
  "handoff_id": "ho_a1b2c3d4e5f6",
  "from": {
    "agent": "paul",
    "framework": "claude-code"
  },
  "status": "completed",
  "result": {
    "summary": "Fixed stale Desktop path in process-webhook-queue.mjs",
    "artifacts": {
      "fix_description": "Updated ROOT to OPS_ROOT pointing to ~/.openclaw/operations",
      "test_result": "WEBHOOK_QUEUE_EMPTY — clean execution, zero errors"
    },
    "files_changed": [
      "/Users/charles/.openclaw/operations/scripts/process-webhook-queue.mjs"
    ]
  },
  "created_at": "2026-03-25T22:30:00Z"
}
```

For failures:

```json
{
  "type": "handoff.done",
  "handoff_id": "ho_a1b2c3d4e5f6",
  "from": {
    "agent": "paul"
  },
  "status": "failed",
  "result": {
    "error": "Permission denied: cannot write to /etc/cron.d",
    "error_type": "PermissionError",
    "suggestion": "Escalate to Charles for sudo access",
    "partial_work": "Diagnosis complete, fix identified but not applied"
  },
  "created_at": "2026-03-25T22:30:00Z"
}
```

## 4. Status Lifecycle

```
              ┌──────────┐
              │  pending  │
              └─────┬─────┘
                    │ handoff.ack (accepted=true)
              ┌─────▼─────┐
         ┌────│  accepted  │
         │    └─────┬─────┘
         │          │ work begins
         │    ┌─────▼──────┐
         │    │ in_progress │──── handoff.progress (optional, repeatable)
         │    └──┬──────┬──┘
         │       │      │
         │  ┌────▼──┐ ┌─▼─────┐
         │  │completed│ │failed │
         │  └────────┘ └───────┘
         │
         │ handoff.ack (accepted=false)
    ┌────▼───┐
    │rejected │
    └────────┘
```

Valid transitions:
- `pending` → `accepted` (via `handoff.ack` with `accepted: true`)
- `pending` → `rejected` (via `handoff.ack` with `accepted: false`)
- `accepted` → `in_progress` (implicit when work begins)
- `in_progress` → `completed` (via `handoff.done` with `status: "completed"`)
- `in_progress` → `failed` (via `handoff.done` with `status: "failed"`)

## 5. Transport Layer

The protocol is transport-agnostic. Messages are JSON objects that can be delivered via any mechanism. Reference transports:

### 5.1 File-Based (Default)

Messages are written as JSON files to a shared directory.

```
~/.swarmdeck/handoffs/
├── pending/
│   └── ho_a1b2c3d4e5f6.json
├── accepted/
├── in_progress/
├── completed/
└── failed/
```

Files move between directories as status changes. Simple, debuggable, works locally with zero infrastructure.

### 5.2 Redis

Messages published to channels keyed by receiving agent.

```
PUBLISH swarmdeck:handoff:paul <message_json>
SUBSCRIBE swarmdeck:handoff:paul
```

### 5.3 HTTP/Webhook

POST messages to registered agent endpoints.

```
POST https://agent-paul.example.com/swarmdeck/handoff
Content-Type: application/json

<message_json>
```

### 5.4 Custom

Any transport that implements `send(agent_id, message)` and `receive(agent_id) -> message`.

## 6. Field Reference

### Required Fields (all message types)

| Field | Type | Description |
|---|---|---|
| `type` | string | Message type (`handoff.request`, `handoff.ack`, `handoff.progress`, `handoff.done`) |
| `created_at` | string (ISO 8601) | When the message was created |

### Handoff Request Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique handoff identifier (prefix: `ho_`) |
| `version` | string | Yes | Protocol version |
| `from` | Agent | Yes | Delegating agent identity |
| `to` | Agent | Yes | Receiving agent identity |
| `task.description` | string | Yes | Human-readable task description |
| `task.context` | array of KV | No | Key-value context pairs |
| `task.priority` | string | No | `low`, `normal`, `high`, `critical` |
| `task.deadline` | string (ISO 8601) | No | When the task is due |
| `task.labels` | array of string | No | Categorisation tags |
| `expectations.output_format` | string | No | Expected output type |
| `expectations.confirmation_required` | boolean | No | Whether ACK is required |
| `expectations.artifacts` | array of string | No | Expected output artifact names |

### Agent Identity

| Field | Type | Required | Description |
|---|---|---|---|
| `agent` | string | Yes | Agent name/role |
| `framework` | string | No | Agent framework (`claude-code`, `crewai`, `langgraph`, `autogen`, `custom`) |
| `instance_id` | string | No | Specific agent instance |

## 7. Conformance

A conformant implementation MUST:
1. Generate valid `handoff.request` messages with all required fields
2. Respond to received requests with `handoff.ack` within a transport-defined timeout
3. Send `handoff.done` when work is completed or has failed
4. Use ISO 8601 timestamps in UTC
5. Preserve all `task.context` key-value pairs through the handoff lifecycle

A conformant implementation MAY:
1. Send `handoff.progress` messages during execution
2. Include `suggest_agent` in rejection ACKs
3. Extend messages with additional fields prefixed with `x_`

## 8. Security Considerations

- Handoff messages may contain sensitive context (file paths, API keys, error details). Transports SHOULD encrypt messages in transit.
- File-based transport SHOULD use restrictive file permissions (600).
- Agent identity is self-asserted. Transports requiring authentication SHOULD verify agent identity at the transport layer.

## 9. References

- OpenClaw Oscar/Paul/Rick/Sandra team coordination (production usage since 2026-02)
- A2A (Agent-to-Agent) Protocol by Google (2025)
- Model Context Protocol (MCP) by Anthropic (2024)
