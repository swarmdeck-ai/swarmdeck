"""Console exporter — pretty-prints spans to stderr for debugging."""

from __future__ import annotations

import sys
import time
from typing import List

from swarmdeck.models import Span, Session


def console_handler(items: List) -> None:
    """Print spans and sessions to stderr. Enable with SWARMDECK_DEBUG=1."""
    for item in items:
        if isinstance(item, Span):
            _print_span(item)
        elif isinstance(item, Session):
            _print_session(item)


def _print_span(span: Span) -> None:
    status_icon = "\u2713" if span.status == "ok" else "\u2717"
    agent_str = f" [{span.agent}]" if span.agent else ""
    dur_str = f" {span.duration_ms:.1f}ms" if span.duration_ms else ""
    print(
        f"  {status_icon}{agent_str} {span.operation}{dur_str}",
        file=sys.stderr,
    )


def _print_session(session: Session) -> None:
    state = "ended" if session.ended_at else "started"
    print(
        f"  \u25b6 session:{session.name} ({state})",
        file=sys.stderr,
    )
