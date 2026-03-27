"""Session context manager for grouping spans into logical workflows."""

from __future__ import annotations

from typing import Any, Dict, Optional

from swarmdeck.models import Session
from swarmdeck.context import _session_scope
from swarmdeck._async import get_worker


class SessionContext:
    """Context manager that creates a traced session.

    Usage:
        with SessionContext("weekly-report") as session:
            # all @trace'd calls inside here are associated with this session
            crew.kickoff()
    """

    def __init__(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._session = Session(name=name, metadata=metadata or {})
        self._scope = None

    def __enter__(self) -> Session:
        get_worker().emit(self._session)
        self._scope = _session_scope(self._session)
        self._scope.__enter__()
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._session.finish()
        if exc_type is not None:
            self._session.metadata["error"] = str(exc_val)
            self._session.metadata["error_type"] = exc_type.__name__
        get_worker().emit(self._session)
        if self._scope:
            self._scope.__exit__(exc_type, exc_val, exc_tb)
        return False

    async def __aenter__(self) -> Session:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        return self.__exit__(exc_type, exc_val, exc_tb)
