"""Playwright E2E fixtures — skips when agent1 GATE-2 (backend) is not up."""

from __future__ import annotations

import os
import urllib.error
import urllib.request

import pytest

pytest_plugins = ["pytest_playwright"]


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("E2E_BASE_URL", "http://localhost:8000")


def _health_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


@pytest.fixture(scope="session")
def backend_available(base_url: str) -> bool:
    return _health_ok(base_url)


@pytest.fixture(scope="session")
def require_backend(backend_available: bool) -> None:
    if not backend_available:
        pytest.skip(
            "Backend not reachable at E2E_BASE_URL (/health). "
            "Waiting for agent1 GATE-2 and agent2 GATE-1."
        )


@pytest.fixture
def ui(page, base_url: str, require_backend: None):
    page.goto(f"{base_url}/ui/")
    return page


@pytest.fixture
def unique_name() -> str:
    import time

    return f"E2E Test {int(time.time() * 1000)}"
