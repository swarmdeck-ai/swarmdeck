"""Observatory — the public facade for SwarmDeck tracing."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, List, Optional

from swarmdeck import frameworks
from swarmdeck._async import get_worker
from swarmdeck.exporters.console import console_handler
from swarmdeck.exporters.otel import spans_to_otel, write_otel_json
from swarmdeck.models import FrameworkInfo, Session, Span
from swarmdeck.session import SessionContext
from swarmdeck.store import TraceStore


class Observatory:
    """Main entry point for SwarmDeck observability."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._store = TraceStore(db_path)
        self._frameworks: Optional[List[FrameworkInfo]] = None
        self._worker = get_worker()

        self.activate()

        if os.environ.get("SWARMDECK_DEBUG", "").strip().lower() in {"1", "true", "yes"}:
            self.enable_console()

    def activate(self) -> "Observatory":
        """Make this observatory the active process-level persistence sink."""
        self._worker.add_handler(self._store.save_batch, key="store")
        return self

    def add_handler(self, handler: Callable, key: Optional[str] = None) -> str:
        return self._worker.add_handler(handler, key=key)

    def enable_console(self) -> None:
        self._worker.add_handler(console_handler, key="console")

    @property
    def detected_frameworks(self) -> List[FrameworkInfo]:
        if self._frameworks is None:
            self._frameworks = frameworks.detect()
        return self._frameworks

    def session(self, name: str, **metadata) -> SessionContext:
        return SessionContext(name, metadata=metadata)

    def query(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Span]:
        return self._store.query_spans(
            session_id=session_id,
            agent=agent,
            trace_id=trace_id,
            operation=operation,
            status=status,
            limit=limit,
        )

    def sessions(self, limit: int = 50) -> List[Session]:
        return self._store.query_sessions(limit=limit)

    def export_otel(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        resource_attributes: Optional[dict] = None,
    ) -> dict:
        spans = self.query(
            session_id=session_id,
            agent=agent,
            trace_id=trace_id,
            operation=operation,
            status=status,
            limit=limit,
        )
        return spans_to_otel(spans, resource_attributes=resource_attributes)

    def write_otel(
        self,
        path: str,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        resource_attributes: Optional[dict] = None,
    ) -> Path:
        spans = self.query(
            session_id=session_id,
            agent=agent,
            trace_id=trace_id,
            operation=operation,
            status=status,
            limit=limit,
        )
        return write_otel_json(path, spans, resource_attributes=resource_attributes)

    def flush(self, timeout: float = 2.0) -> bool:
        return self._worker.flush(timeout=timeout)

    def shutdown(self, timeout: float = 2.0) -> None:
        self.flush(timeout=timeout)
        self._store.close()
        self._worker.shutdown(timeout=timeout)

    @property
    def store(self) -> TraceStore:
        return self._store

    @property
    def database_path(self) -> str:
        return self._store.database_path
