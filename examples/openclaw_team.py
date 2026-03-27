"""Dog-food example for tracing an OpenClaw-style handoff flow."""

from __future__ import annotations

import os
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
DB_PATH = EXAMPLE_DIR / "openclaw-team.db"
EXPORT_PATH = EXAMPLE_DIR / "openclaw-team-otlp.json"

if DB_PATH.exists():
    DB_PATH.unlink()
if EXPORT_PATH.exists():
    EXPORT_PATH.unlink()

os.environ.setdefault("SWARMDECK_DB_PATH", str(DB_PATH))

from swarmdeck import observatory, trace  # noqa: E402


@trace(agent="oscar", team="openclaw", operation="oscar.intake")
def oscar_intake(directive: str) -> str:
    return paul_execute(directive)


@trace(agent="paul", team="openclaw", operation="paul.execute")
def paul_execute(directive: str) -> str:
    verification = sandra_publish_check(directive)
    return rick_digest(verification)


@trace(agent="sandra", team="openclaw", operation="sandra.publish_check")
def sandra_publish_check(directive: str) -> str:
    return f"publish-ready:{directive}"


@trace(agent="rick", team="openclaw", operation="rick.digest")
def rick_digest(message: str) -> str:
    return f"digest:{message}"


def main() -> None:
    with observatory.session(
        "openclaw-daily-cycle",
        initiated_by="oscar",
        team="openclaw",
        lane="swarmdeck-phase-1",
    ):
        result = oscar_intake("Build SwarmDeck Observatory SDK")

    observatory.flush()
    spans = observatory.query(limit=20)
    observatory.write_otel(
        str(EXPORT_PATH),
        resource_attributes={
            "service.name": "openclaw-team",
            "swarmdeck.demo": True,
        },
        limit=50,
    )

    print(f"result={result}")
    print(f"db={observatory.database_path}")
    print(f"export={EXPORT_PATH}")
    print(f"sessions={len(observatory.sessions())}")
    print(f"spans={len(spans)}")


if __name__ == "__main__":
    main()
