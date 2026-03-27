"""Framework auto-detection for CrewAI, LangGraph, and AutoGen."""

from __future__ import annotations

from typing import List

from swarmdeck.models import FrameworkInfo
from swarmdeck.frameworks import crewai, langgraph, autogen

_ADAPTERS = [crewai, langgraph, autogen]


def detect() -> List[FrameworkInfo]:
    """Detect all installed agent frameworks."""
    detected = []
    for adapter in _ADAPTERS:
        info = adapter.detect()
        if info is not None:
            detected.append(info)
    return detected
