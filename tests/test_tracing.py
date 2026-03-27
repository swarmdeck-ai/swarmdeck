from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from swarmdeck import Observatory, trace
from swarmdeck.models import FrameworkInfo, Span


class SwarmDeckTracingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "traces.db"
        self.observatory = Observatory(db_path=str(self.db_path))

    def tearDown(self) -> None:
        self.observatory.shutdown()
        self.tmpdir.cleanup()

    def test_sync_handoff_flow_is_traced(self) -> None:
        @trace(agent="rick", team="openclaw", operation="rick.digest")
        def rick_digest(message: str) -> str:
            return f"digest:{message}"

        @trace(agent="paul", team="openclaw", operation="paul.execute")
        def paul_execute(message: str) -> str:
            return rick_digest(message)

        @trace(agent="oscar", team="openclaw", operation="oscar.intake")
        def oscar_intake(message: str) -> str:
            return paul_execute(message)

        with self.observatory.session("openclaw-cycle", initiated_by="oscar"):
            result = oscar_intake("ship swarmdeck")

        self.observatory.flush()
        spans = sorted(self.observatory.query(limit=10), key=lambda item: item.started_at)
        sessions = self.observatory.sessions(limit=10)

        self.assertEqual(result, "digest:ship swarmdeck")
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(spans), 3)
        self.assertTrue(all(span.session_id == sessions[0].id for span in spans))
        self.assertEqual(spans[0].trace_id, spans[1].trace_id)
        self.assertEqual(spans[1].trace_id, spans[2].trace_id)
        self.assertEqual(spans[1].parent_span_id, spans[0].id)
        self.assertEqual(spans[2].parent_span_id, spans[1].id)

    def test_store_serializes_non_json_attributes(self) -> None:
        span = Span(operation="paul.serialize", agent="paul", team="openclaw")
        span.set_attribute("path", Path("/tmp/swarmdeck.txt"))
        span.set_attribute("exc", ValueError("boom"))
        span.finish()
        self.observatory.store.save_span(span)

        loaded = self.observatory.query(operation="paul.serialize", limit=1)[0]

        self.assertEqual(loaded.attributes["path"], "/tmp/swarmdeck.txt")
        self.assertIn("boom", loaded.attributes["exc"])

    def test_framework_detection_uses_available_adapters(self) -> None:
        with mock.patch("swarmdeck.frameworks.crewai.detect", return_value=FrameworkInfo("crewai", "1.0")):
            with mock.patch("swarmdeck.frameworks.langgraph.detect", return_value=None):
                with mock.patch("swarmdeck.frameworks.autogen.detect", return_value=FrameworkInfo("autogen", "0.4")):
                    detected = self.observatory.detected_frameworks

        self.assertEqual([item.name for item in detected], ["crewai", "autogen"])


class SwarmDeckAsyncTracingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "traces.db"
        self.observatory = Observatory(db_path=str(self.db_path))

    def tearDown(self) -> None:
        self.observatory.shutdown()
        self.tmpdir.cleanup()

    async def test_async_trace_captures_error_status(self) -> None:
        @trace(agent="sandra", team="openclaw", operation="sandra.publish")
        async def sandra_publish() -> None:
            await asyncio.sleep(0)
            raise RuntimeError("publish failed")

        with self.observatory.session("async-flow"):
            with self.assertRaises(RuntimeError):
                await sandra_publish()

        self.observatory.flush()
        spans = self.observatory.query(operation="sandra.publish", limit=1)

        self.assertEqual(spans[0].status, "error")
        self.assertEqual(spans[0].attributes["error_type"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
