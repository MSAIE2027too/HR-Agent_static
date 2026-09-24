"""Pytest isolation: each test gets a fresh LangGraph thread store."""
import os

import pytest


@pytest.fixture(autouse=True)
def _isolate_threads(tmp_path, monkeypatch):
    monkeypatch.setenv("THREADS_DB", str(tmp_path / "threads.db"))
