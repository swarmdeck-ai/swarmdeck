"""The `@trace` decorator — SwarmDeck's primary public API."""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, Dict, Optional, TypeVar

from swarmdeck._async import get_worker
from swarmdeck.context import _span_scope, current_session, current_span
from swarmdeck.models import Span, _new_id

F = TypeVar("F", bound=Callable[..., Any])


def trace(
    func: Optional[F] = None,
    *,
    agent: Optional[str] = None,
    team: Optional[str] = None,
    operation: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorate a function so SwarmDeck records it as a span.

    Works as either `@trace` or `@trace(agent="paul", team="ops")`.
    """

    def decorator(target: F) -> F:
        op_name = operation or target.__qualname__
        static_attributes = {
            "code.function": target.__qualname__,
            "code.module": target.__module__,
        }
        if attributes:
            static_attributes.update(attributes)

        @functools.wraps(target)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            span = _build_span(op_name, agent=agent, team=team, attributes=static_attributes)
            with _span_scope(span):
                try:
                    result = target(*args, **kwargs)
                    span.finish("ok")
                    return result
                except Exception as exc:
                    span.finish("error")
                    span.attributes["error"] = str(exc)
                    span.attributes["error_type"] = type(exc).__name__
                    raise
                finally:
                    get_worker().emit(span)

        @functools.wraps(target)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            span = _build_span(op_name, agent=agent, team=team, attributes=static_attributes)
            with _span_scope(span):
                try:
                    result = await target(*args, **kwargs)
                    span.finish("ok")
                    return result
                except Exception as exc:
                    span.finish("error")
                    span.attributes["error"] = str(exc)
                    span.attributes["error_type"] = type(exc).__name__
                    raise
                finally:
                    get_worker().emit(span)

        if asyncio.iscoroutinefunction(target):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)
    return decorator


def _build_span(
    operation: str,
    *,
    agent: Optional[str],
    team: Optional[str],
    attributes: Optional[Dict[str, Any]] = None,
) -> Span:
    parent = current_span()
    session = current_session()
    span = Span(
        operation=operation,
        agent=agent,
        team=team,
        trace_id=parent.trace_id if parent else _new_id(),
        parent_span_id=parent.id if parent else None,
        session_id=session.id if session else None,
    )
    if attributes:
        span.attributes.update(attributes)
    return span
