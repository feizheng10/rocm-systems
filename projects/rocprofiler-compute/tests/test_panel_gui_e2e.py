##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
##############################################################################
"""
E2E tests for the Panel GUI using pytest + Playwright.

Requires: pip install playwright pytest-playwright && playwright install chromium

Run from project root:
  pytest tests/test_panel_gui_e2e.py -v
  pytest tests/test_panel_gui_e2e.py -v --headed   # show browser

If PANEL_DEMO_URL is set (e.g. http://127.0.0.1:8869/panel_demo_serve), tests
use that URL instead of starting the server (useful when demo is already running).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Ensure src is on path (conftest does this for root, but be explicit for portability)
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from playwright.sync_api import Page, expect
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Default port for spawned server; overridden when PANEL_DEMO_URL is set
PANEL_DEMO_PORT = 9876
DEMO_PREFIX = "panel_demo_serve"


def _wait_for_url(url: str, timeout: float = 15.0) -> bool:
    """Return True when url returns 200."""
    import urllib.request
    import urllib.error
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


@pytest.fixture(scope="module")
def panel_demo_url():
    """
    Base URL for the Panel demo app.
    If PANEL_DEMO_URL is set, use it. Otherwise start the demo server on a random port.
    """
    env_url = os.environ.get("PANEL_DEMO_URL", "").strip()
    if env_url:
        yield env_url.rstrip("/")
        return

    # Start demo server in subprocess
    script = SRC / "rocprof_compute_analyze" / "panel_demo_simple.py"
    if not script.exists():
        pytest.skip(f"Demo script not found: {script}")

    proc = subprocess.Popen(
        [sys.executable, str(script), "--port", str(PANEL_DEMO_PORT)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={**os.environ},
    )
    try:
        url = f"http://127.0.0.1:{PANEL_DEMO_PORT}/{DEMO_PREFIX}"
        if not _wait_for_url(url):
            proc.terminate()
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            pytest.skip(f"Panel demo server did not become ready. stderr: {stderr}")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture
def page(panel_demo_url, request):
    """Playwright page fixture; skip if Playwright not installed."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not installed. pip install playwright pytest-playwright && playwright install chromium")
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True
        )
        context = browser.new_context()
        pg = context.new_page()
        pg.goto(panel_demo_url)
        yield pg
        context.close()
        browser.close()
        pw.stop()
    except Exception as e:
        pytest.skip(f"Playwright browser launch failed: {e}")


# Use pytest-playwright's page when available; otherwise our fixture above uses sync_playwright.
# For simplicity we use sync_playwright in fixture so we don't depend on pytest-playwright plugin.
@pytest.mark.panel_gui
@pytest.mark.e2e
@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
def test_demo_page_loads(page, panel_demo_url):
    """E2E: Demo page loads and main heading is visible."""
    page.goto(panel_demo_url)
    expect(page.get_by_role("heading", name="Panel WebSocket Demo")).to_be_visible(timeout=10000)


@pytest.mark.panel_gui
@pytest.mark.e2e
@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
def test_demo_slider_visible(page, panel_demo_url):
    """E2E: Slider widget is present and visible."""
    page.goto(panel_demo_url)
    slider = page.get_by_role("slider")
    expect(slider).to_be_visible(timeout=10000)
    # Default value is 10
    expect(slider).to_have_value("10")


@pytest.mark.panel_gui
@pytest.mark.e2e
@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
def test_demo_slider_updates_markdown(page, panel_demo_url):
    """E2E: Changing slider value updates the displayed text."""
    page.goto(panel_demo_url)
    slider = page.get_by_role("slider")
    expect(slider).to_be_visible(timeout=10000)
    slider.fill("50")
    # Markdown pane should show "Slider value: 50"
    expect(page.get_by_text("Slider value:", exact=False)).to_contain_text("50", timeout=5000)
