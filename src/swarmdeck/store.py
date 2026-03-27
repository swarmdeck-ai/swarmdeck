"""SQLite storage layer for traces and sessions."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, List, Optional

from swarmdeck.models import Session, Span

_DEFAULT_DB_DIR = os.path.join(os.path.expanduser("~"), ".swarmdeck")
_DEFAULT_DB_PATH = os.path.join(_DEFAULT_DB_DIR, "traces.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    started_at REAL NOT NULL,
    ended_at REAL,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS spans (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    parent_span_id TEXT,
    trace_id TEXT NOT NULL,
    agent TEXT,
    team TEXT,
    operation TEXT NOT NULL,
    started_at REAL NOT NULL,
    ended_at REAL,
    duration_ms REAL,
    status TEXT DEFAULT 'ok',
    attributes TEXT,
    events TEXT
);

CREATE INDEX IF NOT EXISTS idx_spans_session ON spans(session_id);
CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_agent ON spans(agent);
"""


class TraceStore:
    """Thread-safe SQLite storage for SwarmDeck traces."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = str(db_path or os.environ.get("SWARMDECK_DB_PATH") or _DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()

    def save_span(self, span: Span) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO spans
            (id, session_id, parent_span_id, trace_id, agent, team, operation,
             started_at, ended_at, duration_ms, status, attributes, events)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                span.id,
                span.session_id,
                span.parent_span_id,
                span.trace_id,
                span.agent,
                span.team,
                span.operation,
                span.started_at,
                span.ended_at,
                span.duration_ms,
                span.status,
                _encode_json(span.attributes),
                _encode_json(span.events),
            ),
        )
        conn.commit()

    def save_session(self, session: Session) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO sessions
            (id, name, started_at, ended_at, metadata)
            VALUES (?, ?, ?, ?, ?)""",
            (
                session.id,
                session.name,
                session.started_at,
                session.ended_at,
                _encode_json(session.metadata),
            ),
        )
        conn.commit()

    def save_batch(self, items: list) -> None:
        conn = self._get_conn()
        for item in items:
            if isinstance(item, Span):
                conn.execute(
                    """INSERT OR REPLACE INTO spans
                    (id, session_id, parent_span_id, trace_id, agent, team, operation,
                     started_at, ended_at, duration_ms, status, attributes, events)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.id,
                        item.session_id,
                        item.parent_span_id,
                        item.trace_id,
                        item.agent,
                        item.team,
                        item.operation,
                        item.started_at,
                        item.ended_at,
                        item.duration_ms,
                        item.status,
                        _encode_json(item.attributes),
                        _encode_json(item.events),
                    ),
                )
            elif isinstance(item, Session):
                conn.execute(
                    """INSERT OR REPLACE INTO sessions
                    (id, name, started_at, ended_at, metadata)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        item.id,
                        item.name,
                        item.started_at,
                        item.ended_at,
                        _encode_json(item.metadata),
                    ),
                )
        conn.commit()

    def query_spans(
        self,
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Span]:
        conn = self._get_conn()
        clauses = []
        params = []
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if agent:
            clauses.append("agent = ?")
            params.append(agent)
        if trace_id:
            clauses.append("trace_id = ?")
            params.append(trace_id)
        if operation:
            clauses.append("operation = ?")
            params.append(operation)
        if status:
            clauses.append("status = ?")
            params.append(status)

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM spans{where} ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_span(row) for row in rows]

    def query_sessions(self, limit: int = 50) -> List[Session]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_session(row) for row in rows]

    @staticmethod
    def _row_to_span(row: sqlite3.Row) -> Span:
        return Span(
            id=row["id"],
            trace_id=row["trace_id"],
            session_id=row["session_id"],
            parent_span_id=row["parent_span_id"],
            agent=row["agent"],
            team=row["team"],
            operation=row["operation"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            duration_ms=row["duration_ms"],
            status=row["status"],
            attributes=_decode_json(row["attributes"], default={}),
            events=_decode_json(row["events"], default=[]),
        )

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            name=row["name"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            metadata=_decode_json(row["metadata"], default={}),
        )

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None

    @property
    def database_path(self) -> str:
        return self._db_path


def _encode_json(value: Any) -> str:
    return json.dumps(_json_safe(value))


def _decode_json(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    return json.loads(raw)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _json_safe(value.to_dict())
    return repr(value)
