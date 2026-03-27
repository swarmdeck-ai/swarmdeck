"""Context propagation for span and session tracking via contextvars."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from swarmdeck.models import Span, Session

_current_span: ContextVar[Optional[Span]] = ContextVar("swarmdeck_span", default=None)
_current_session: ContextVar[Optional[Session]] = ContextVar("swarmdeck_session", default=None)


def current_span() -> Optional[Span]:
    return _current_span.get()


def current_session() -> Optional[Session]:
    return _current_session.get()


@contextmanager
def _span_scope(span: Span) -> Iterator[Span]:
    token = _current_span.set(span)
    try:
        yield span
    finally:
        _current_span.reset(token)


@contextmanager
def _session_scope(session: Session) -> Iterator[Session]:
    token = _current_session.set(session)
    try:
        yield session
    finally:
        _current_session.reset(token)
