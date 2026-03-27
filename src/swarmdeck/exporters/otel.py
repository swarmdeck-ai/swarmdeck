"""OpenTelemetry-compatible exporters for SwarmDeck traces."""

from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from swarmdeck.models import Span


def spans_to_otel(
    spans: Sequence[Span],
    *,
    resource_attributes: Optional[Dict[str, Any]] = None,
    scope_name: str = "swarmdeck",
    scope_version: str = "0.1.0",
) -> Dict[str, Any]:
    """Convert spans into an OTLP JSON-compatible payload."""
    resource_values = {
        "service.name": "swarmdeck",
        "telemetry.sdk.name": "swarmdeck",
        "telemetry.sdk.language": "python",
    }
    if resource_attributes:
        resource_values.update(resource_attributes)

    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [_kv_attr(key, value) for key, value in resource_values.items()]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": scope_name,
                            "version": scope_version,
                        },
                        "spans": [span_to_otel(span) for span in spans],
                    }
                ],
            }
        ]
    }


def span_to_otel(span: Span) -> Dict[str, Any]:
    """Convert a single span into an OTLP JSON-compatible span record."""
    attributes = {
        "swarmdeck.agent": span.agent or "",
        "swarmdeck.team": span.team or "",
        **span.attributes,
    }
    return {
        "traceId": _normalize_hex(span.trace_id, 32),
        "spanId": _normalize_hex(span.id, 16),
        "parentSpanId": _normalize_hex(span.parent_span_id or "", 16),
        "name": span.operation,
        "kind": "SPAN_KIND_INTERNAL",
        "startTimeUnixNano": int((span.started_at or 0) * 1_000_000_000),
        "endTimeUnixNano": int((span.ended_at or span.started_at or 0) * 1_000_000_000),
        "status": {
            "code": "STATUS_CODE_ERROR" if span.status == "error" else "STATUS_CODE_OK"
        },
        "attributes": [_kv_attr(key, value) for key, value in attributes.items()],
        "events": [_event_to_otel(event) for event in span.events],
    }


def write_otel_json(
    path: str,
    spans: Sequence[Span],
    *,
    resource_attributes: Optional[Dict[str, Any]] = None,
    scope_name: str = "swarmdeck",
    scope_version: str = "0.1.0",
) -> Path:
    """Write spans to an OTLP JSON-compatible file."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = spans_to_otel(
        spans,
        resource_attributes=resource_attributes,
        scope_name=scope_name,
        scope_version=scope_version,
    )
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def _kv_attr(key: str, value: Any) -> Dict[str, Any]:
    return {"key": str(key), "value": _otel_value(value)}


def _event_to_otel(event: Dict[str, Any]) -> Dict[str, Any]:
    values = dict(event)
    name = str(values.pop("name", "event"))
    timestamp = values.pop("timestamp", 0)
    return {
        "name": name,
        "timeUnixNano": int(float(timestamp) * 1_000_000_000),
        "attributes": [_kv_attr(key, value) for key, value in values.items()],
    }


def _otel_value(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"stringValue": "null"}
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, dict):
        return {
            "kvlistValue": {
                "values": [_kv_attr(key, item) for key, item in value.items()]
            }
        }
    if isinstance(value, (list, tuple, set)):
        return {"arrayValue": {"values": [_otel_value(item) for item in value]}}
    return {"stringValue": str(value)}


def _normalize_hex(value: str, size: int) -> str:
    filtered = "".join(ch for ch in str(value).lower() if ch in string.hexdigits.lower())
    if not filtered:
        filtered = "0"
    return filtered[-size:].rjust(size, "0")
