"""Shared test fixtures for SwarmDeck tests."""

import os
import tempfile

import pytest


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a temporary SQLite database path."""
    return str(tmp_path / "test_traces.db")


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Ensure tests never write to the real ~/.swarmdeck directory."""
    db_path = str(tmp_path / "test_traces.db")
    monkeypatch.setenv("SWARMDECK_DB_PATH", db_path)
