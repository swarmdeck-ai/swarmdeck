"""Handoff Protocol transport backends."""

from __future__ import annotations

import json
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from swarmdeck.handoff.models import (
    Agent,
    HandoffAck,
    HandoffDone,
    HandoffProgress,
    HandoffRequest,
)

_STATUS_DIRS = ("pending", "accepted", "in_progress", "completed", "failed", "rejected")

_MESSAGE_TYPES = {
    "handoff.request": HandoffRequest,
    "handoff.ack": HandoffAck,
    "handoff.progress": HandoffProgress,
    "handoff.done": HandoffDone,
}


class Transport(ABC):
    """Abstract base for handoff message transport."""

    @abstractmethod
    def send(self, agent_id: str, message: dict) -> None:
        """Deliver a message to the specified agent."""

    @abstractmethod
    def receive(self, agent_id: str) -> List[dict]:
        """Retrieve pending messages for the specified agent."""

    @abstractmethod
    def update_status(self, handoff_id: str, new_status: str) -> None:
        """Move a handoff to a new status."""

    @abstractmethod
    def get_handoff(self, handoff_id: str) -> Optional[dict]:
        """Retrieve a handoff by ID regardless of status."""

    @abstractmethod
    def list_handoffs(self, status: Optional[str] = None) -> List[dict]:
        """List handoffs, optionally filtered by status."""


class FileTransport(Transport):
    """File-based transport — JSON files in a shared directory.

    Layout:
        {root}/
        ├── pending/
        │   └── ho_abc123.json
        ├── accepted/
        ├── in_progress/
        ├── completed/
        ├── failed/
        └── rejected/
    """

    def __init__(self, root: Optional[str] = None) -> None:
        self._root = Path(root or os.path.join(os.path.expanduser("~"), ".swarmdeck", "handoffs"))
        for d in _STATUS_DIRS:
            (self._root / d).mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def send(self, agent_id: str, message: dict) -> None:
        msg_type = message.get("type", "")
        if msg_type == "handoff.request":
            handoff_id = message["id"]
            dest = self._root / "pending" / f"{handoff_id}.json"
        elif msg_type == "handoff.ack":
            handoff_id = message["handoff_id"]
            dest = self._root / "pending" / f"{handoff_id}.ack.json"
        elif msg_type == "handoff.progress":
            handoff_id = message["handoff_id"]
            # Progress messages go alongside the in_progress handoff
            dest = self._root / "in_progress" / f"{handoff_id}.progress.json"
        elif msg_type == "handoff.done":
            handoff_id = message["handoff_id"]
            dest = self._root / "in_progress" / f"{handoff_id}.done.json"
        else:
            raise ValueError(f"Unknown message type: {msg_type}")

        dest.write_text(json.dumps(message, indent=2), encoding="utf-8")

    def receive(self, agent_id: str) -> List[dict]:
        messages = []
        for f in sorted(self._root.glob("**/*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                to_agent = data.get("to", {}).get("agent", "")
                if to_agent == agent_id:
                    messages.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return messages

    def update_status(self, handoff_id: str, new_status: str) -> None:
        if new_status not in _STATUS_DIRS:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {_STATUS_DIRS}")

        # Find the handoff file in any status directory
        source = self._find_handoff_file(handoff_id)
        if source is None:
            raise FileNotFoundError(f"Handoff {handoff_id} not found")

        dest = self._root / new_status / source.name
        shutil.move(str(source), str(dest))

    def get_handoff(self, handoff_id: str) -> Optional[dict]:
        f = self._find_handoff_file(handoff_id)
        if f is None:
            return None
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list_handoffs(self, status: Optional[str] = None) -> List[dict]:
        results = []
        dirs = [status] if status else list(_STATUS_DIRS)
        for d in dirs:
            dir_path = self._root / d
            if not dir_path.exists():
                continue
            for f in sorted(dir_path.glob("*.json")):
                if ".ack." in f.name or ".progress." in f.name or ".done." in f.name:
                    continue  # skip auxiliary messages
                try:
                    results.append(json.loads(f.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, OSError):
                    continue
        return results

    def _find_handoff_file(self, handoff_id: str) -> Optional[Path]:
        filename = f"{handoff_id}.json"
        for d in _STATUS_DIRS:
            candidate = self._root / d / filename
            if candidate.exists():
                return candidate
        return None
