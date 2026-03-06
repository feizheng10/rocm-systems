##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
##############################################################################

"""
Unit tests for the Jupyter / Jupyter Book API (rocprof_compute_jupyter).

Run from project root: pytest tests/test_jupyter_api.py -v
"""

# Mark all tests in this module as jupyter API tests
pytestmark = pytest.mark.jupyter

import inspect
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src is on path (pyproject.toml pythonpath may already include it)
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="module")
def jupyter_module():
    """Import rocprof_compute_jupyter once per module."""
    import rocprof_compute_jupyter as rc
    return rc


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------

def test_jupyter_module_imports(jupyter_module):
    """Module imports without error."""
    assert jupyter_module is not None


def test_jupyter_public_functions(jupyter_module):
    """Public API includes open, analysis, get_dataframe, list_tables."""
    expected = {"open", "analysis", "get_dataframe", "list_tables"}
    public = {x for x in dir(jupyter_module) if not x.startswith("_")}
    for name in expected:
        assert name in public, f"Missing public function: {name}"


def test_jupyter_open_signature(jupyter_module):
    """open(perf_data_dir, **kwargs) has correct signature."""
    sig = inspect.signature(jupyter_module.open)
    params = list(sig.parameters)
    assert "perf_data_dir" in params
    assert "kwargs" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )


def test_jupyter_analysis_signature(jupyter_module):
    """analysis() has optional filter args."""
    sig = inspect.signature(jupyter_module.analysis)
    params = set(sig.parameters)
    assert "filter_kernel" in params
    assert "filter_gpu" in params
    assert "filter_dispatch" in params
    assert "show_basic_only" in params


def test_jupyter_get_dataframe_signature(jupyter_module):
    """get_dataframe(table_id) takes one int."""
    sig = inspect.signature(jupyter_module.get_dataframe)
    params = list(sig.parameters)
    assert params == ["table_id"]


def test_jupyter_analysis_class_exists(jupyter_module):
    """JupyterAnalysis class is available."""
    assert hasattr(jupyter_module, "JupyterAnalysis")
    assert hasattr(jupyter_module.JupyterAnalysis, "display_results")
    assert hasattr(jupyter_module.JupyterAnalysis, "pre_processing")


# ---------------------------------------------------------------------------
# Behavior: open() with invalid path
# ---------------------------------------------------------------------------

def test_open_invalid_dir_exits(jupyter_module):
    """open(nonexistent_dir) triggers exit (console_error + sys.exit)."""
    with patch.object(sys, "exit", side_effect=SystemExit(1)):
        with pytest.raises(SystemExit):
            jupyter_module.open("/nonexistent/path/12345")


def test_open_file_not_dir_exits(jupyter_module):
    """open(path_to_file) triggers exit."""
    with patch.object(sys, "exit", side_effect=SystemExit(1)):
        with pytest.raises(SystemExit):
            jupyter_module.open(__file__)


# ---------------------------------------------------------------------------
# Behavior: get_dataframe / list_tables without open()
# ---------------------------------------------------------------------------

def test_get_dataframe_without_open_exits(jupyter_module):
    """get_dataframe() without prior open() triggers exit."""
    # Reset global state so no analysis is loaded
    with patch.object(jupyter_module, "_current_analysis", None):
        with patch.object(sys, "exit", side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                jupyter_module.get_dataframe(1)


def test_list_tables_without_open_exits(jupyter_module):
    """list_tables() without prior open() triggers exit."""
    with patch.object(jupyter_module, "_current_analysis", None):
        with patch.object(sys, "exit", side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                jupyter_module.list_tables()


def test_analysis_without_open_exits(jupyter_module):
    """analysis() without prior open() triggers exit."""
    with patch.object(jupyter_module, "_current_analysis", None):
        with patch.object(sys, "exit", side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                jupyter_module.analysis()
