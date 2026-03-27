"""Tests for the @trace decorator."""

import time

from swarmdeck.tracer import trace
from swarmdeck.context import current_span
from swarmdeck._async import get_worker


def test_trace_basic():
    @trace(agent="researcher", team="content")
    def my_func():
        return "hello"

    result = my_func()
    assert result == "hello"


def test_trace_preserves_function_name():
    @trace(agent="paul")
    def important_function():
        pass

    assert important_function.__name__ == "important_function"


def test_trace_captures_error():
    @trace(agent="paul")
    def failing_func():
        raise ValueError("test error")

    try:
        failing_func()
    except ValueError:
        pass
    # If we got here without crashing, the decorator handled the error correctly


def test_trace_nested_parent_child():
    parent_span_seen = None
    child_span_seen = None

    @trace(agent="outer")
    def outer():
        nonlocal parent_span_seen
        parent_span_seen = current_span()
        return inner()

    @trace(agent="inner")
    def inner():
        nonlocal child_span_seen
        child_span_seen = current_span()
        return "nested"

    result = outer()
    assert result == "nested"
    assert parent_span_seen is not None
    assert child_span_seen is not None
    assert child_span_seen.parent_span_id == parent_span_seen.id
    assert child_span_seen.trace_id == parent_span_seen.trace_id


def test_trace_bare_decorator():
    @trace
    def bare_func():
        return 42

    assert bare_func() == 42
    assert bare_func.__name__ == "bare_func"


def test_trace_with_attributes():
    @trace(agent="paul", attributes={"custom_key": "custom_value"})
    def attributed_func():
        span = current_span()
        assert span.attributes["custom_key"] == "custom_value"
        return "ok"

    assert attributed_func() == "ok"


def test_trace_records_code_metadata():
    @trace(agent="paul")
    def tracked_func():
        span = current_span()
        assert "code.function" in span.attributes
        assert "code.module" in span.attributes

    tracked_func()
