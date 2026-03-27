"""AutoGen framework detection."""

from __future__ import annotations

import importlib.util
from typing import Optional

from swarmdeck.models import FrameworkInfo


def detect() -> Optional[FrameworkInfo]:
    spec = importlib.util.find_spec("autogen")
    if spec is None:
        return None
    version = None
    try:
        import autogen  # type: ignore
        version = getattr(autogen, "__version__", None)
    except Exception:
        pass
    return FrameworkInfo(name="autogen", version=version)
