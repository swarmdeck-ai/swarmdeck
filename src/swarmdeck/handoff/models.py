"""Handoff Protocol message models."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _handoff_id() -> str:
    return f"ho_{uuid.uuid4().hex[:12]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Agent:
    """Agent identity in the handoff protocol."""

    agent: str
    framework: Optional[str] = None
    instance_id: Optional[str] = None


@dataclass
class TaskContext:
    """Key-value context pair attached to a handoff."""

    key: str
    value: str


@dataclass
class Task:
    """Task definition within a handoff request."""

    description: str
    context: List[TaskContext] = field(default_factory=list)
    priority: str = "normal"
    deadline: Optional[str] = None
    labels: List[str] = field(default_factory=list)


@dataclass
class Expectations:
    """Expected outputs from the handoff."""

    output_format: Optional[str] = None
    confirmation_required: bool = True
    artifacts: List[str] = field(default_factory=list)


@dataclass
class HandoffRequest:
    """A structured task delegation from one agent to another."""

    sender: Agent
    receiver: Agent
    task: Task
    expectations: Expectations = field(default_factory=Expectations)
    id: str = field(default_factory=_handoff_id)
    version: str = "0.1"
    created_at: str = field(default_factory=_utc_now)

    @property
    def type(self) -> str:
        return "handoff.request"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type
        d["from"] = d.pop("sender")
        d["to"] = d.pop("receiver")
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffRequest":
        return cls(
            id=data["id"],
            version=data.get("version", "0.1"),
            sender=Agent(**data["from"]),
            receiver=Agent(**data["to"]),
            task=Task(
                description=data["task"]["description"],
                context=[TaskContext(**c) for c in data["task"].get("context", [])],
                priority=data["task"].get("priority", "normal"),
                deadline=data["task"].get("deadline"),
                labels=data["task"].get("labels", []),
            ),
            expectations=Expectations(
                output_format=data.get("expectations", {}).get("output_format"),
                confirmation_required=data.get("expectations", {}).get(
                    "confirmation_required", True
                ),
                artifacts=data.get("expectations", {}).get("artifacts", []),
            ),
            created_at=data.get("created_at", _utc_now()),
        )


@dataclass
class HandoffAck:
    """Acknowledgement (accept/reject) of a handoff request."""

    handoff_id: str
    sender: Agent
    accepted: bool
    reason: Optional[str] = None
    suggest_agent: Optional[str] = None
    estimated_completion: Optional[str] = None
    created_at: str = field(default_factory=_utc_now)

    @property
    def type(self) -> str:
        return "handoff.ack"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type
        d["from"] = d.pop("sender")
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class HandoffProgress:
    """Optional progress update during handoff execution."""

    handoff_id: str
    sender: Agent
    message: str
    progress_pct: Optional[int] = None
    created_at: str = field(default_factory=_utc_now)

    @property
    def type(self) -> str:
        return "handoff.progress"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type
        d["from"] = d.pop("sender")
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class HandoffDone:
    """Completion report for a handoff (success or failure)."""

    handoff_id: str
    sender: Agent
    status: str  # "completed" or "failed"
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)

    @property
    def type(self) -> str:
        return "handoff.done"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type
        d["from"] = d.pop("sender")
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
