"""HandoffManager — high-level API for the Handoff Protocol."""

from __future__ import annotations

from typing import Dict, List, Optional

from swarmdeck.handoff.models import (
    Agent,
    HandoffAck,
    HandoffDone,
    HandoffProgress,
    HandoffRequest,
    Task,
    TaskContext,
    Expectations,
)
from swarmdeck.handoff.transport import FileTransport, Transport


class HandoffManager:
    """Manages handoff lifecycle for an agent.

    Usage:
        manager = HandoffManager(agent=Agent(agent="paul", framework="claude-code"))

        # Create and send a handoff
        request = manager.create_handoff(
            to=Agent(agent="rick"),
            description="Research API dependencies",
            priority="high",
        )

        # Receive and acknowledge
        pending = manager.receive()
        manager.accept(pending[0].id)

        # Complete
        manager.complete(request.id, summary="Done", artifacts={"report": "..."})
    """

    def __init__(
        self,
        agent: Agent,
        transport: Optional[Transport] = None,
    ) -> None:
        self._agent = agent
        self._transport = transport or FileTransport()

    @property
    def agent(self) -> Agent:
        return self._agent

    def create_handoff(
        self,
        to: Agent,
        description: str,
        context: Optional[Dict[str, str]] = None,
        priority: str = "normal",
        deadline: Optional[str] = None,
        labels: Optional[List[str]] = None,
        output_format: Optional[str] = None,
        artifacts: Optional[List[str]] = None,
    ) -> HandoffRequest:
        """Create and send a new handoff request."""
        task_context = [TaskContext(key=k, value=v) for k, v in (context or {}).items()]
        request = HandoffRequest(
            sender=self._agent,
            receiver=to,
            task=Task(
                description=description,
                context=task_context,
                priority=priority,
                deadline=deadline,
                labels=labels or [],
            ),
            expectations=Expectations(
                output_format=output_format,
                artifacts=artifacts or [],
            ),
        )
        self._transport.send(to.agent, request.to_dict())
        return request

    def receive(self) -> List[dict]:
        """Get all pending messages for this agent."""
        return self._transport.receive(self._agent.agent)

    def accept(
        self,
        handoff_id: str,
        estimated_completion: Optional[str] = None,
    ) -> HandoffAck:
        """Accept a handoff request."""
        ack = HandoffAck(
            handoff_id=handoff_id,
            sender=self._agent,
            accepted=True,
            estimated_completion=estimated_completion,
        )
        self._transport.send(self._agent.agent, ack.to_dict())
        self._transport.update_status(handoff_id, "accepted")
        return ack

    def reject(
        self,
        handoff_id: str,
        reason: str,
        suggest_agent: Optional[str] = None,
    ) -> HandoffAck:
        """Reject a handoff request."""
        ack = HandoffAck(
            handoff_id=handoff_id,
            sender=self._agent,
            accepted=False,
            reason=reason,
            suggest_agent=suggest_agent,
        )
        self._transport.send(self._agent.agent, ack.to_dict())
        self._transport.update_status(handoff_id, "rejected")
        return ack

    def progress(
        self,
        handoff_id: str,
        message: str,
        progress_pct: Optional[int] = None,
    ) -> HandoffProgress:
        """Send a progress update for an in-progress handoff."""
        update = HandoffProgress(
            handoff_id=handoff_id,
            sender=self._agent,
            message=message,
            progress_pct=progress_pct,
        )
        self._transport.update_status(handoff_id, "in_progress")
        self._transport.send(self._agent.agent, update.to_dict())
        return update

    def complete(
        self,
        handoff_id: str,
        summary: str,
        artifacts: Optional[Dict[str, str]] = None,
        files_changed: Optional[List[str]] = None,
    ) -> HandoffDone:
        """Mark a handoff as completed."""
        done = HandoffDone(
            handoff_id=handoff_id,
            sender=self._agent,
            status="completed",
            result={
                "summary": summary,
                "artifacts": artifacts or {},
                "files_changed": files_changed or [],
            },
        )
        self._transport.send(self._agent.agent, done.to_dict())
        self._transport.update_status(handoff_id, "completed")
        return done

    def fail(
        self,
        handoff_id: str,
        error: str,
        suggestion: Optional[str] = None,
        partial_work: Optional[str] = None,
    ) -> HandoffDone:
        """Mark a handoff as failed."""
        done = HandoffDone(
            handoff_id=handoff_id,
            sender=self._agent,
            status="failed",
            result={
                "error": error,
                "suggestion": suggestion,
                "partial_work": partial_work,
            },
        )
        self._transport.send(self._agent.agent, done.to_dict())
        self._transport.update_status(handoff_id, "failed")
        return done

    def list_handoffs(self, status: Optional[str] = None) -> List[dict]:
        """List all handoffs, optionally filtered by status."""
        return self._transport.list_handoffs(status=status)

    def get_handoff(self, handoff_id: str) -> Optional[dict]:
        """Get a specific handoff by ID."""
        return self._transport.get_handoff(handoff_id)
