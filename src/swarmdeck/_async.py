"""Background trace worker for async span emission."""

from __future__ import annotations

import atexit
import queue
import threading
import time
from typing import Callable, Dict, Iterable, List, Optional, Union

from swarmdeck.models import Session, Span

TraceItem = Union[Span, Session]
TraceHandler = Callable[[List[TraceItem]], None]

_SENTINEL = object()
_BATCH_SIZE = 50
_FLUSH_INTERVAL = 0.1  # seconds
_QUEUE_MAX_SIZE = 10_000


class TraceWorker:
    """Background daemon thread that batches and flushes trace data.

    The `emit()` hot path uses `put_nowait()` so traced functions do not block
    on SQLite or exporter I/O. If the queue is saturated, the event is dropped
    and counted instead of stalling the caller.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[object] = queue.Queue(maxsize=_QUEUE_MAX_SIZE)
        self._handlers: Dict[str, TraceHandler] = {}
        self._thread: Optional[threading.Thread] = None
        self._started = False
        self._lock = threading.Lock()
        self._atexit_registered = False
        self._dropped_items = 0

    def _build_thread(self) -> threading.Thread:
        return threading.Thread(
            target=self._run,
            daemon=True,
            name="swarmdeck-tracer",
        )

    def _ensure_started(self) -> None:
        if self._started:
            return
        with self._lock:
            if not self._started:
                self._thread = self._build_thread()
                self._thread.start()
                self._started = True
                if not self._atexit_registered:
                    atexit.register(self.shutdown)
                    self._atexit_registered = True

    def add_handler(self, handler: TraceHandler, key: Optional[str] = None) -> str:
        """Register or replace a handler used for flushed trace batches."""
        handler_key = key or f"handler:{id(handler)}"
        with self._lock:
            self._handlers[handler_key] = handler
        return handler_key

    def remove_handler(self, key: str) -> None:
        with self._lock:
            self._handlers.pop(key, None)

    def emit(self, item: TraceItem) -> bool:
        self._ensure_started()
        try:
            self._queue.put_nowait(item)
            return True
        except queue.Full:
            with self._lock:
                self._dropped_items += 1
            return False

    def _run(self) -> None:
        batch: List[TraceItem] = []
        while True:
            try:
                item = self._queue.get(timeout=_FLUSH_INTERVAL)
                if item is _SENTINEL:
                    batch_size = len(batch)
                    self._flush(batch)
                    self._complete_batch(batch_size)
                    self._queue.task_done()
                    return
                batch.append(item)
                if len(batch) >= _BATCH_SIZE:
                    batch_size = len(batch)
                    self._flush(batch)
                    self._complete_batch(batch_size)
                    batch = []
            except queue.Empty:
                if batch:
                    batch_size = len(batch)
                    self._flush(batch)
                    self._complete_batch(batch_size)
                    batch = []

    def _flush(self, batch: List[TraceItem]) -> None:
        if not batch:
            return
        with self._lock:
            handlers: Iterable[TraceHandler] = tuple(self._handlers.values())
        for handler in handlers:
            try:
                handler(batch)
            except Exception:
                pass

    def _complete_batch(self, size: int) -> None:
        for _ in range(size):
            self._queue.task_done()

    def flush(self, timeout: float = 2.0) -> bool:
        """Wait until queued items are persisted or timeout expires."""
        self._ensure_started()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._queue.unfinished_tasks == 0:
                return True
            time.sleep(0.01)
        return self._queue.unfinished_tasks == 0

    def shutdown(self, timeout: float = 2.0) -> None:
        with self._lock:
            if not self._started:
                return
            thread = self._thread
        self.flush(timeout=timeout)
        self._queue.put(_SENTINEL)
        if thread is not None:
            thread.join(timeout=timeout)
        with self._lock:
            self._started = False
            self._thread = None

    @property
    def dropped_items(self) -> int:
        with self._lock:
            return self._dropped_items


_worker = TraceWorker()


def get_worker() -> TraceWorker:
    return _worker
