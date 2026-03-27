"""Tests for context propagation."""

from swarmdeck.context import (
    current_span,
    current_session,
    _span_scope,
    _session_scope,
)
from swarmdeck.models import Span, Session


def test_current_span_default_none():
    assert current_span() is None


def test_current_session_default_none():
    assert current_session() is None


def test_span_scope_sets_and_restores():
    assert current_span() is None
    span = Span(operation="test")
    with _span_scope(span):
        assert current_span() is span
    assert current_span() is None


def test_session_scope_sets_and_restores():
    assert current_session() is None
    session = Session(name="test")
    with _session_scope(session):
        assert current_session() is session
    assert current_session() is None


def test_nested_span_scopes():
    parent = Span(operation="parent")
    child = Span(operation="child")
    with _span_scope(parent):
        assert current_span() is parent
        with _span_scope(child):
            assert current_span() is child
        assert current_span() is parent
    assert current_span() is None


def test_span_scope_restores_on_exception():
    span = Span(operation="test")
    try:
        with _span_scope(span):
            assert current_span() is span
            raise ValueError("test error")
    except ValueError:
        pass
    assert current_span() is None
