"""Tests for Handoff Protocol models, transport, and manager."""

import json

from swarmdeck.handoff.models import (
    Agent,
    Expectations,
    HandoffAck,
    HandoffDone,
    HandoffProgress,
    HandoffRequest,
    Task,
    TaskContext,
)
from swarmdeck.handoff.transport import FileTransport
from swarmdeck.handoff.manager import HandoffManager


# --- Model tests ---

def test_handoff_request_creation():
    req = HandoffRequest(
        sender=Agent(agent="oscar", framework="claude-code"),
        receiver=Agent(agent="paul", framework="claude-code"),
        task=Task(description="Fix webhook cron"),
    )
    assert req.id.startswith("ho_")
    assert req.type == "handoff.request"
    assert req.task.description == "Fix webhook cron"


def test_handoff_request_to_dict():
    req = HandoffRequest(
        sender=Agent(agent="oscar"),
        receiver=Agent(agent="paul"),
        task=Task(description="Test task"),
    )
    d = req.to_dict()
    assert d["type"] == "handoff.request"
    assert d["from"]["agent"] == "oscar"
    assert d["to"]["agent"] == "paul"
    assert "sender" not in d
    assert "receiver" not in d


def test_handoff_request_to_json():
    req = HandoffRequest(
        sender=Agent(agent="oscar"),
        receiver=Agent(agent="paul"),
        task=Task(description="Test"),
    )
    j = req.to_json()
    parsed = json.loads(j)
    assert parsed["type"] == "handoff.request"


def test_handoff_request_from_dict():
    data = {
        "type": "handoff.request",
        "id": "ho_test123",
        "version": "0.1",
        "from": {"agent": "oscar", "framework": "claude-code"},
        "to": {"agent": "paul", "framework": "claude-code"},
        "task": {
            "description": "Fix cron",
            "context": [{"key": "script", "value": "/path/to/script"}],
            "priority": "high",
        },
        "expectations": {"confirmation_required": True},
        "created_at": "2026-03-25T22:19:00Z",
    }
    req = HandoffRequest.from_dict(data)
    assert req.id == "ho_test123"
    assert req.sender.agent == "oscar"
    assert req.receiver.agent == "paul"
    assert req.task.priority == "high"
    assert len(req.task.context) == 1


def test_handoff_ack():
    ack = HandoffAck(
        handoff_id="ho_test",
        sender=Agent(agent="paul"),
        accepted=True,
    )
    assert ack.type == "handoff.ack"
    d = ack.to_dict()
    assert d["accepted"] is True
    assert d["from"]["agent"] == "paul"


def test_handoff_reject():
    ack = HandoffAck(
        handoff_id="ho_test",
        sender=Agent(agent="paul"),
        accepted=False,
        reason="Blocked on repo trust",
        suggest_agent="charles",
    )
    d = ack.to_dict()
    assert d["accepted"] is False
    assert d["reason"] == "Blocked on repo trust"
    assert d["suggest_agent"] == "charles"


def test_handoff_progress():
    prog = HandoffProgress(
        handoff_id="ho_test",
        sender=Agent(agent="paul"),
        message="Root cause identified",
        progress_pct=60,
    )
    assert prog.type == "handoff.progress"
    d = prog.to_dict()
    assert d["progress_pct"] == 60


def test_handoff_done_completed():
    done = HandoffDone(
        handoff_id="ho_test",
        sender=Agent(agent="paul"),
        status="completed",
        result={"summary": "Fixed stale path"},
    )
    assert done.type == "handoff.done"
    assert done.status == "completed"


def test_handoff_done_failed():
    done = HandoffDone(
        handoff_id="ho_test",
        sender=Agent(agent="paul"),
        status="failed",
        result={"error": "Permission denied"},
    )
    assert done.status == "failed"


# --- Transport tests ---

def test_file_transport_send_and_get(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    req = HandoffRequest(
        sender=Agent(agent="oscar"),
        receiver=Agent(agent="paul"),
        task=Task(description="Test task"),
    )
    transport.send("paul", req.to_dict())

    result = transport.get_handoff(req.id)
    assert result is not None
    assert result["id"] == req.id


def test_file_transport_list_handoffs(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    for i in range(3):
        req = HandoffRequest(
            sender=Agent(agent="oscar"),
            receiver=Agent(agent="paul"),
            task=Task(description=f"Task {i}"),
        )
        transport.send("paul", req.to_dict())

    results = transport.list_handoffs(status="pending")
    assert len(results) == 3


def test_file_transport_update_status(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    req = HandoffRequest(
        sender=Agent(agent="oscar"),
        receiver=Agent(agent="paul"),
        task=Task(description="Test"),
    )
    transport.send("paul", req.to_dict())

    transport.update_status(req.id, "accepted")
    assert transport.list_handoffs(status="pending") == []
    accepted = transport.list_handoffs(status="accepted")
    assert len(accepted) == 1
    assert accepted[0]["id"] == req.id


def test_file_transport_receive(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    req = HandoffRequest(
        sender=Agent(agent="oscar"),
        receiver=Agent(agent="paul"),
        task=Task(description="For Paul"),
    )
    transport.send("paul", req.to_dict())

    messages = transport.receive("paul")
    assert len(messages) == 1
    assert messages[0]["to"]["agent"] == "paul"

    # Different agent shouldn't see it
    assert transport.receive("rick") == []


# --- Manager tests ---

def test_manager_create_handoff(tmp_path):
    manager = HandoffManager(
        agent=Agent(agent="oscar", framework="claude-code"),
        transport=FileTransport(root=str(tmp_path / "handoffs")),
    )
    req = manager.create_handoff(
        to=Agent(agent="paul"),
        description="Fix webhook cron",
        context={"script": "/path/to/script.mjs"},
        priority="high",
        labels=["infra", "cron"],
    )
    assert req.id.startswith("ho_")
    assert req.task.priority == "high"


def test_manager_accept_handoff(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    oscar = HandoffManager(agent=Agent(agent="oscar"), transport=transport)
    paul = HandoffManager(agent=Agent(agent="paul"), transport=transport)

    req = oscar.create_handoff(to=Agent(agent="paul"), description="Test task")
    ack = paul.accept(req.id)

    assert ack.accepted is True
    assert transport.list_handoffs(status="accepted")


def test_manager_reject_handoff(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    oscar = HandoffManager(agent=Agent(agent="oscar"), transport=transport)
    paul = HandoffManager(agent=Agent(agent="paul"), transport=transport)

    req = oscar.create_handoff(to=Agent(agent="paul"), description="Test task")
    ack = paul.reject(req.id, reason="Not authorized", suggest_agent="charles")

    assert ack.accepted is False
    assert transport.list_handoffs(status="rejected")


def test_manager_full_lifecycle(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    oscar = HandoffManager(agent=Agent(agent="oscar"), transport=transport)
    paul = HandoffManager(agent=Agent(agent="paul"), transport=transport)

    # Oscar creates handoff
    req = oscar.create_handoff(
        to=Agent(agent="paul"),
        description="Fix webhook queue cron",
        context={"error": "EAGAIN -11", "failing_since": "2026-03-21"},
        priority="high",
    )
    assert transport.list_handoffs(status="pending")

    # Paul accepts
    paul.accept(req.id)
    assert transport.list_handoffs(status="accepted")

    # Paul sends progress
    paul.progress(req.id, "Root cause identified: stale Desktop path", progress_pct=60)
    assert transport.list_handoffs(status="in_progress")

    # Paul completes
    done = paul.complete(
        req.id,
        summary="Fixed ROOT to OPS_ROOT in process-webhook-queue.mjs",
        artifacts={"test_result": "WEBHOOK_QUEUE_EMPTY"},
        files_changed=["process-webhook-queue.mjs"],
    )
    assert done.status == "completed"
    assert transport.list_handoffs(status="completed")
    assert not transport.list_handoffs(status="in_progress")


def test_manager_fail_lifecycle(tmp_path):
    transport = FileTransport(root=str(tmp_path / "handoffs"))
    oscar = HandoffManager(agent=Agent(agent="oscar"), transport=transport)
    paul = HandoffManager(agent=Agent(agent="paul"), transport=transport)

    req = oscar.create_handoff(to=Agent(agent="paul"), description="Dangerous task")
    paul.accept(req.id)
    paul.progress(req.id, "Starting work")

    done = paul.fail(
        req.id,
        error="Permission denied",
        suggestion="Escalate to Charles",
        partial_work="Diagnosis complete",
    )
    assert done.status == "failed"
    assert transport.list_handoffs(status="failed")
