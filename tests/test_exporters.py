from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from swarmdeck.exporters.otel import span_to_otel, spans_to_otel, write_otel_json
from swarmdeck.models import Span


class OTelExporterTests(unittest.TestCase):
    def test_span_to_otel_normalizes_ids_and_events(self) -> None:
        span = Span(
            operation="paul.verify",
            id="abc123",
            trace_id="trace789",
            parent_span_id="parent456",
            agent="paul",
            team="openclaw",
        )
        span.add_event("handoff.accepted", owner="paul")
        span.finish()

        otel_span = span_to_otel(span)

        self.assertEqual(len(otel_span["traceId"]), 32)
        self.assertEqual(len(otel_span["spanId"]), 16)
        self.assertEqual(len(otel_span["parentSpanId"]), 16)
        self.assertEqual(otel_span["events"][0]["name"], "handoff.accepted")

    def test_write_otel_json_writes_payload(self) -> None:
        span = Span(operation="oscar.intake", agent="oscar", team="openclaw")
        span.finish()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "export.json"
            written = write_otel_json(
                str(output),
                [span],
                resource_attributes={"service.name": "openclaw-team"},
            )

            self.assertEqual(written, output)
            payload = json.loads(output.read_text(encoding="utf-8"))
            resource_spans = payload["resourceSpans"][0]
            self.assertEqual(
                resource_spans["resource"]["attributes"][0]["key"],
                "service.name",
            )
            self.assertEqual(
                resource_spans["scopeSpans"][0]["spans"][0]["name"],
                "oscar.intake",
            )

    def test_spans_to_otel_builds_resource_payload(self) -> None:
        span = Span(operation="rick.digest", agent="rick", team="openclaw")
        span.finish()

        payload = spans_to_otel([span], resource_attributes={"deployment.environment": "dev"})

        self.assertIn("resourceSpans", payload)
        attrs = payload["resourceSpans"][0]["resource"]["attributes"]
        keys = {item["key"] for item in attrs}
        self.assertIn("deployment.environment", keys)


if __name__ == "__main__":
    unittest.main()
