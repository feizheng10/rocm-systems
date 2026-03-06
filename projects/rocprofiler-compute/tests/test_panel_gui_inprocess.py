##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
##############################################################################
"""
In-process tests for Panel GUI layout and callback logic (no browser).

Run from project root:
  pytest tests/test_panel_gui_inprocess.py -v
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _layout_children(layout):
    """Get list of direct children (Panel version-agnostic)."""
    if hasattr(layout, "objects"):
        return list(layout.objects)
    return [layout[i] for i in range(len(layout))]


@pytest.fixture
def pn():
    """Panel module; skip tests if panel is not installed."""
    return pytest.importorskip("panel")


@pytest.fixture
def create_app(pn):
    """Import create_app from the demo module."""
    from rocprof_compute_analyze.panel_demo_simple import create_app as _create_app
    return _create_app


# ---------------------------------------------------------------------------
# Layout structure tests
# ---------------------------------------------------------------------------

@pytest.mark.panel_gui
@pytest.mark.inprocess
def test_demo_create_app_returns_column(create_app, pn):
    """create_app() returns a Panel Column."""
    layout = create_app()
    assert isinstance(layout, pn.Column)


@pytest.mark.panel_gui
@pytest.mark.inprocess
def test_demo_layout_has_heading_and_row(create_app, pn):
    """Layout contains a main heading and a Row (slider + pane)."""
    layout = create_app()
    children = _layout_children(layout)
    assert len(children) >= 2
    first = children[0]
    assert isinstance(first, pn.pane.Markdown)
    assert "Panel WebSocket Demo" in (first.object or "")
    row = children[1]
    assert isinstance(row, pn.Row)
    assert len(_layout_children(row)) >= 2


@pytest.mark.panel_gui
@pytest.mark.inprocess
def test_demo_slider_initial_value(create_app):
    """Slider has default value 10."""
    layout = create_app()
    row = _layout_children(layout)[1]
    row_children = _layout_children(row)
    slider = row_children[0]
    assert hasattr(slider, "value")
    assert slider.value == 10


@pytest.mark.panel_gui
@pytest.mark.inprocess
def test_demo_initial_markdown_shows_slider_value(create_app, pn):
    """Markdown pane initially shows 'Slider value: 10'."""
    layout = create_app()
    row = _layout_children(layout)[1]
    row_children = _layout_children(row)
    pane = row_children[1]
    assert isinstance(pane, pn.pane.Markdown)
    assert "10" in (pane.object or "")
    assert "Slider value" in (pane.object or "")


# ---------------------------------------------------------------------------
# Callback logic tests
# ---------------------------------------------------------------------------

@pytest.mark.panel_gui
@pytest.mark.inprocess
def test_demo_slider_callback_updates_markdown(create_app):
    """Changing slider value updates the Markdown pane content."""
    layout = create_app()
    row = _layout_children(layout)[1]
    row_children = _layout_children(row)
    slider = row_children[0]
    pane = row_children[1]

    slider.value = 50
    assert "50" in (pane.object or "")
    assert "Slider value" in (pane.object or "")

    slider.value = 0
    assert "0" in (pane.object or "")

    slider.value = 100
    assert "100" in (pane.object or "")


@pytest.mark.panel_gui
@pytest.mark.inprocess
def test_demo_slider_bounds(create_app):
    """Slider respects min/max (0 and 100)."""
    layout = create_app()
    row = _layout_children(layout)[1]
    slider = _layout_children(row)[0]
    assert slider.start == 0
    assert slider.end == 100
