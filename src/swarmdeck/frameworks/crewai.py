"""CrewAI framework detection."""

from __future__ import annotations

import importlib.util
from typing import Optional

from swarmdeck.models import FrameworkInfo


def detect() -> Optional[FrameworkInfo]:
    spec = importlib.util.find_spec("crewai")
    if spec is None:
        return None
    version = None
    try:
        import crewai  # type: ignore
        version = getattr(crewai, "__version__", None)
    except Exception:
        pass
    return FrameworkInfo(name="crewai", version=version)
