"""LangGraph framework detection."""

from __future__ import annotations

import importlib.util
from typing import Optional

from swarmdeck.models import FrameworkInfo


def detect() -> Optional[FrameworkInfo]:
    spec = importlib.util.find_spec("langgraph")
    if spec is None:
        return None
    version = None
    try:
        import langgraph  # type: ignore
        version = getattr(langgraph, "__version__", None)
    except Exception:
        pass
    return FrameworkInfo(name="langgraph", version=version)
