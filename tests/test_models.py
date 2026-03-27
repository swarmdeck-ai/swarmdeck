"""Tests for core data models."""

import time

from swarmdeck.models import Span, Session, FrameworkInfo, _new_id


def test_span_creation():
    span = Span(operation="test_op", agent="paul", team="ops")
    assert span.operation == "test_op"
    assert span.agent == "paul"
    assert span.team == "ops"
    assert span.status == "ok"
    assert span.id is not None
    assert span.trace_id is not None
    assert span.started_at > 0


def test_span_finish():
    span = Span(operation="test_op")
    time.sleep(0.01)
    span.finish("ok")
    assert span.ended_at is not None
    assert span.duration_ms is not None
    assert span.duration_ms >= 10  # at least 10ms


def test_span_finish_error():
    span = Span(operation="test_op")
    span.finish("error")
    assert span.status == "error"


def test_span_add_event():
    span = Span(operation="test_op")
    span.add_event("llm_call", model="gpt-4")
    assert len(span.events) == 1
    assert span.events[0]["name"] == "llm_call"
    assert span.events[0]["model"] == "gpt-4"


def test_span_set_attribute():
    span = Span(operation="test_op")
    span.set_attribute("tokens", 150)
    assert span.attributes["tokens"] == 150


def test_span_to_dict():
    span = Span(operation="test_op", agent="paul")
    span.finish()
    d = span.to_dict()
    assert d["operation"] == "test_op"
    assert d["agent"] == "paul"
    assert "id" in d
    assert "duration_ms" in d


def test_session_creation():
    session = Session(name="test-session")
    assert session.name == "test-session"
    assert session.id is not None
    assert session.started_at > 0
    assert session.ended_at is None


def test_session_finish():
    session = Session(name="test-session")
    time.sleep(0.01)
    session.finish()
    assert session.ended_at is not None
    assert session.duration_ms is not None
    assert session.duration_ms >= 10


def test_session_to_dict():
    session = Session(name="test-session", metadata={"key": "value"})
    d = session.to_dict()
    assert d["name"] == "test-session"
    assert d["metadata"] == {"key": "value"}


def test_framework_info():
    info = FrameworkInfo(name="crewai", version="0.5.0")
    assert info.name == "crewai"
    assert info.version == "0.5.0"
    assert info.detected_at > 0


def test_new_id_unique():
    ids = {_new_id() for _ in range(1000)}
    assert len(ids) == 1000
