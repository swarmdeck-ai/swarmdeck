"""Tests for SQLite storage layer."""

import time

from swarmdeck.models import Span, Session
from swarmdeck.store import TraceStore


def test_save_and_query_span(tmp_db):
    store = TraceStore(db_path=tmp_db)
    span = Span(operation="test_op", agent="paul", team="ops")
    span.finish()
    store.save_span(span)

    results = store.query_spans(agent="paul")
    assert len(results) == 1
    assert results[0].operation == "test_op"
    assert results[0].agent == "paul"
    store.close()


def test_save_and_query_session(tmp_db):
    store = TraceStore(db_path=tmp_db)
    session = Session(name="test-session", metadata={"key": "value"})
    store.save_session(session)

    results = store.query_sessions()
    assert len(results) == 1
    assert results[0].name == "test-session"
    assert results[0].metadata == {"key": "value"}
    store.close()


def test_save_batch(tmp_db):
    store = TraceStore(db_path=tmp_db)
    span1 = Span(operation="op1", agent="paul")
    span1.finish()
    span2 = Span(operation="op2", agent="rick")
    span2.finish()
    session = Session(name="batch-session")

    store.save_batch([span1, span2, session])

    spans = store.query_spans()
    assert len(spans) == 2
    sessions = store.query_sessions()
    assert len(sessions) == 1
    store.close()


def test_query_by_trace_id(tmp_db):
    store = TraceStore(db_path=tmp_db)
    span1 = Span(operation="op1", trace_id="trace_abc")
    span1.finish()
    span2 = Span(operation="op2", trace_id="trace_xyz")
    span2.finish()
    store.save_batch([span1, span2])

    results = store.query_spans(trace_id="trace_abc")
    assert len(results) == 1
    assert results[0].trace_id == "trace_abc"
    store.close()


def test_query_by_operation(tmp_db):
    store = TraceStore(db_path=tmp_db)
    span1 = Span(operation="research")
    span1.finish()
    span2 = Span(operation="publish")
    span2.finish()
    store.save_batch([span1, span2])

    results = store.query_spans(operation="research")
    assert len(results) == 1
    assert results[0].operation == "research"
    store.close()


def test_query_by_status(tmp_db):
    store = TraceStore(db_path=tmp_db)
    span_ok = Span(operation="op1")
    span_ok.finish("ok")
    span_err = Span(operation="op2")
    span_err.finish("error")
    store.save_batch([span_ok, span_err])

    results = store.query_spans(status="error")
    assert len(results) == 1
    assert results[0].status == "error"
    store.close()


def test_query_limit(tmp_db):
    store = TraceStore(db_path=tmp_db)
    for i in range(10):
        span = Span(operation=f"op{i}")
        span.finish()
        store.save_span(span)

    results = store.query_spans(limit=3)
    assert len(results) == 3
    store.close()


def test_span_attributes_roundtrip(tmp_db):
    store = TraceStore(db_path=tmp_db)
    span = Span(operation="test", attributes={"tokens": 150, "model": "gpt-4"})
    span.finish()
    store.save_span(span)

    results = store.query_spans()
    assert results[0].attributes["tokens"] == 150
    assert results[0].attributes["model"] == "gpt-4"
    store.close()


def test_session_update_on_finish(tmp_db):
    store = TraceStore(db_path=tmp_db)
    session = Session(name="test")
    store.save_session(session)

    session.finish()
    store.save_session(session)

    results = store.query_sessions()
    assert len(results) == 1
    assert results[0].ended_at is not None
    store.close()


def test_database_path_property(tmp_db):
    store = TraceStore(db_path=tmp_db)
    assert store.database_path == tmp_db
    store.close()
