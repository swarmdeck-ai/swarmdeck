"""SwarmDeck Handoff Protocol — reference implementation."""

from swarmdeck.handoff.models import (
    Agent,
    HandoffAck,
    HandoffDone,
    HandoffProgress,
    HandoffRequest,
)
from swarmdeck.handoff.manager import HandoffManager
from swarmdeck.handoff.transport import FileTransport, Transport

__all__ = [
    "Agent",
    "FileTransport",
    "HandoffAck",
    "HandoffDone",
    "HandoffManager",
    "HandoffProgress",
    "HandoffRequest",
    "Transport",
]
