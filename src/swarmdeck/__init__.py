"""SwarmDeck public package surface."""

from swarmdeck._version import __version__
from swarmdeck.context import current_session, current_span
from swarmdeck.models import FrameworkInfo, Session, Span
from swarmdeck.tracer import trace
from swarmdeck.observatory import Observatory

# Module-level singleton — zero-config start
observatory = Observatory()

__all__ = [
    "FrameworkInfo",
    "Observatory",
    "Session",
    "Span",
    "__version__",
    "current_session",
    "current_span",
    "observatory",
    "trace",
]
