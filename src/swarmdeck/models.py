"""Core data models for SwarmDeck tracing."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _now() -> float:
    return time.time()


@dataclass
class Span:
    """A single traced operation (tool call, LLM request, agent action)."""

    operation: str
    id: str = field(default_factory=_new_id)
    trace_id: str = field(default_factory=_new_id)
    session_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    agent: Optional[str] = None
    team: Optional[str] = None
    started_at: float = field(default_factory=_now)
    ended_at: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "ok"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status: str = "ok") -> None:
        self.ended_at = _now()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        self.status = status

    def add_event(self, name: str, **attrs: Any) -> None:
        self.events.append({"name": name, "timestamp": _now(), **attrs})

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "parent_span_id": self.parent_span_id,
            "agent": self.agent,
            "team": self.team,
            "operation": self.operation,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class Session:
    """A logical grouping of spans (e.g., one agent workflow run)."""

    name: str
    id: str = field(default_factory=_new_id)
    started_at: float = field(default_factory=_now)
    ended_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self) -> None:
        self.ended_at = _now()

    @property
    def duration_ms(self) -> Optional[float]:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class FrameworkInfo:
    """Detected agent framework metadata."""

    name: str
    version: Optional[str] = None
    detected_at: float = field(default_factory=_now)
