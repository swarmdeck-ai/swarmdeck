"""Tests for session context manager."""

from swarmdeck.session import SessionContext
from swarmdeck.context import current_session


def test_session_context_basic():
    with SessionContext("test-session") as session:
        assert session.name == "test-session"
        assert current_session() is session

    assert current_session() is None


def test_session_context_sets_ended_at():
    with SessionContext("test-session") as session:
        assert session.ended_at is None

    assert session.ended_at is not None


def test_session_context_metadata():
    with SessionContext("test-session", metadata={"key": "value"}) as session:
        assert session.metadata == {"key": "value"}


def test_session_context_captures_error():
    try:
        with SessionContext("failing-session") as session:
            raise RuntimeError("test error")
    except RuntimeError:
        pass

    assert session.metadata.get("error") == "test error"
    assert session.metadata.get("error_type") == "RuntimeError"


def test_session_context_restores_on_exception():
    try:
        with SessionContext("failing-session"):
            raise RuntimeError("test")
    except RuntimeError:
        pass

    assert current_session() is None


def test_nested_sessions():
    with SessionContext("outer") as outer:
        assert current_session() is outer
        with SessionContext("inner") as inner:
            assert current_session() is inner
        assert current_session() is outer
    assert current_session() is None
