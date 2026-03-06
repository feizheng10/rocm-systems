##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
##############################################################################

"""
Jupyter / Jupyter Book API for rocprofiler-compute analysis.

This module provides a simple, stable API for loading and analyzing
rocprofiler-compute performance data in Jupyter notebooks or Jupyter Book.

**API summary**

- :func:`open` — Load performance data from a directory.
- :func:`analysis` — Display analysis results (tables) in the notebook.
- :func:`get_dataframe` — Return a specific table as a pandas DataFrame.
- :func:`list_tables` — List available table IDs and titles.

**Example**

.. code-block:: python

   import rocprof_compute_jupyter as rc

   rc.open("/path/to/workload_dir")
   rc.analysis()
   df = rc.get_dataframe(1)  # kernel top stats
"""

import argparse
import copy
from pathlib import Path
from typing import Any, Optional

import pandas as pd

try:
    from IPython.display import display
    IPYTHON_AVAILABLE = True
except ImportError:
    IPYTHON_AVAILABLE = False

    def display(obj: Any) -> None:
        """Fallback when IPython is not available."""
        print(obj)

from config import HIDDEN_COLUMNS
from rocprof_compute_analyze.analysis_base import OmniAnalyze_Base
from rocprof_compute_soc.soc_base import OmniSoC_Base
from utils import file_io, parser, schema
from utils.logger import console_error, console_log, console_warning


class JupyterAnalysis(OmniAnalyze_Base):
    """Analysis runner for Jupyter notebooks; displays results as tables."""

    def __init__(
        self,
        perf_data_dir: str,
        supported_archs: dict[str, str],
        **kwargs: Any,
    ) -> None:
        args = argparse.Namespace(
            path=[[perf_data_dir]],
            config_dir=str(
                Path(__file__).resolve().parent / "rocprof_compute_soc" / "analysis_configs"
            ),
            list_stats=False,
            list_metrics=None,
            list_blocks=None,
            filter_metrics=kwargs.get("filter_metrics"),
            nodes=kwargs.get("nodes"),
            list_nodes=False,
            spatial_multiplexing=kwargs.get("spatial_multiplexing", False),
            kernel_verbose=kwargs.get("kernel_verbose", 0),
            verbose=kwargs.get("verbose", 0),
            debug=kwargs.get("debug", False),
            time_unit=kwargs.get("time_unit", "ns"),
            normal_unit=kwargs.get("normal_unit", "per_wave"),
            max_stat_num=kwargs.get("max_stat_num", 10),
            decimal=kwargs.get("decimal", 2),
            output_format="stdout",
            output_name=None,
            no_roof=kwargs.get("no_roof", False),
            specs_correction=kwargs.get("specs_correction"),
            roofline_data_type=kwargs.get("roofline_data_type", "empirical"),
            tui=False,
            gui=False,
            random_port=False,
            gpu_kernel=kwargs.get("kernel_filter"),
            gpu_id=kwargs.get("gpu_filter"),
            gpu_dispatch_id=kwargs.get("dispatch_filter"),
            pc_sampling_sorting_type=kwargs.get("pc_sampling_sorting_type", "samples"),
            torch_operator=kwargs.get("torch_operator") or [],
            list_torch_operators=kwargs.get("list_torch_operators", False),
        )
        super().__init__(args, supported_archs)
        self.dest_dir = str(Path(perf_data_dir).absolute().resolve())
        self.arch: Optional[str] = None
        self._hidden_columns = list(HIDDEN_COLUMNS)
        self._comparable_columns: list[str] = []
        self._initialized = False

    def pre_processing(self) -> None:
        """Load data and set architecture."""
        super().pre_processing()
        args = self.get_args()
        self._runs[self.dest_dir].raw_pmc = file_io.create_df_pmc(
            self.dest_dir,
            args.nodes,
            args.spatial_multiplexing,
            args.kernel_verbose,
            args.verbose,
            self._profiling_config,
        )
        if args.spatial_multiplexing:
            self._runs[self.dest_dir].raw_pmc = self.spatial_multiplex_merge_counters(
                self._runs[self.dest_dir].raw_pmc
            )
        if self._profiling_config.get("iteration_multiplexing") is not None:
            self._runs[self.dest_dir].raw_pmc = self.iteration_multiplex_impute_counters(
                self._runs[self.dest_dir].raw_pmc,
                self._profiling_config["iteration_multiplexing"],
            )
        file_io.create_df_kernel_top_stats(
            df_in=self._runs[self.dest_dir].raw_pmc,
            raw_data_dir=self.dest_dir,
            filter_gpu_ids=self._runs[self.dest_dir].filter_gpu_ids,
            filter_dispatch_ids=self._runs[self.dest_dir].filter_dispatch_ids,
            filter_nodes=self._runs[self.dest_dir].filter_nodes,
            time_unit=args.time_unit,
            kernel_verbose=args.kernel_verbose,
        )
        parser.load_non_mertrics_table(
            self._runs[self.dest_dir], self.dest_dir, args
        )
        self.arch = self._runs[self.dest_dir].sys_info.iloc[0]["gpu_arch"]
        self._comparable_columns = parser.build_comparable_columns(args.time_unit)
        self._initialized = True

    def run_analysis(self) -> None:
        """No-op in Jupyter; use display_results() instead."""
        pass

    def _display_dataframe(
        self,
        df: pd.DataFrame,
        table_config: dict[str, Any],
        title: Optional[str] = None,
    ) -> None:
        """Display a dataframe in the notebook (hidden columns excluded)."""
        if title:
            display(f"### {title}")
        if df.empty:
            console_warning(
                "analysis",
                f"Table {table_config.get('id', 'unknown')} is empty",
            )
            return
        display_columns = [
            c for c in df.columns.tolist() if c not in self._hidden_columns
        ]
        display(df[display_columns])

    def display_results(
        self,
        filter_kernel: Optional[list[str]] = None,
        filter_gpu: Optional[list[int]] = None,
        filter_dispatch: Optional[list[int]] = None,
        show_basic_only: bool = False,
    ) -> None:
        """Render analysis results in the notebook."""
        if not self._initialized:
            console_error("analysis", "Must call pre_processing() first")
        args = self.get_args()
        base_run = self.dest_dir
        base_data = self._runs[base_run]
        if filter_kernel:
            base_data.filter_kernel_ids = [str(k) for k in filter_kernel]
        if filter_gpu:
            base_data.filter_gpu_ids = filter_gpu
        if filter_dispatch:
            base_data.filter_dispatch_ids = filter_dispatch
        if not self.arch or self.arch not in self._arch_configs:
            console_error("analysis", f"Architecture {self.arch!r} not supported")
        arch_config = self._arch_configs[self.arch]
        panel_configs = copy.deepcopy(arch_config.panel_configs)
        if show_basic_only or not (filter_kernel or filter_gpu or filter_dispatch):
            basic_panels_keep = [0, 100, 200, 300, 400]
            panel_configs = {
                k: panel_configs[k]
                for k in panel_configs
                if k in basic_panels_keep
            }
        parser.load_table_data(
            workload=base_data,
            dir_path=self.dest_dir,
            is_gui=False,
            args=args,
            config=self._profiling_config,
        )
        display("# ROCProfiler-Compute Analysis Results")
        display(f"**Data directory:** {self.dest_dir}")
        display(f"**Architecture:** {self.arch}")
        display("")
        for panel_id, panel in panel_configs.items():
            if panel["title"] == "Memory Chart":
                continue
            title = f"{panel_id // 100}. {panel['title']}"
            display(f"## {title}")
            for data_source in panel["data source"]:
                for _t_type, table_config in data_source.items():
                    tid = table_config["id"]
                    if tid not in base_data.dfs:
                        continue
                    df = base_data.dfs[tid]
                    if "Info" in getattr(df, "columns", []):
                        df = df.reset_index()
                    subtitle = table_config.get("title")
                    if subtitle:
                        subtitle = f"{tid // 100}.{tid % 100} {subtitle}"
                    self._display_dataframe(df, table_config, subtitle)
        if not (filter_kernel or filter_gpu or filter_dispatch):
            display("")
            display(
                "**Note:** Use filter_kernel, filter_gpu, or filter_dispatch "
                "to see more detailed metrics."
            )


_current_analysis: Optional[JupyterAnalysis] = None
_supported_archs: dict[str, str] = {}


def _supported_archs_map() -> dict[str, str]:
    """Return arch short name -> description map."""
    global _supported_archs
    if not _supported_archs:
        _supported_archs = {
            "gfx908": "MI100",
            "gfx90a": "MI200",
            "gfx940": "MI300A",
            "gfx941": "MI300A",
            "gfx942": "MI300X",
            "gfx950": "MI350X",
        }
    return _supported_archs


def open(perf_data_dir: str, **kwargs: Any) -> None:
    """
    Load performance data from a directory and prepare for analysis.

    Must be called before :func:`analysis`, :func:`get_dataframe`, or :func:`list_tables`.

    Parameters
    ----------
    perf_data_dir : str
        Path to the workload directory (containing sysinfo.csv, pmc_perf, etc.).
    **kwargs
        Optional: kernel_filter, gpu_filter, dispatch_filter, time_unit,
        normal_unit, max_stat_num, decimal, spatial_multiplexing, etc.

    Raises
    ------
    SystemExit
        If the path is not a valid directory.

    Examples
    --------
    >>> import rocprof_compute_jupyter as rc
    >>> rc.open("/path/to/workload_dir")
    >>> rc.open("/path/to/workload", time_unit="us", max_stat_num=20)
    """
    global _current_analysis
    path = Path(perf_data_dir).absolute().resolve()
    if not path.is_dir():
        console_error("analysis", f"Not a directory: {perf_data_dir}")
    console_log("analysis", f"Loading performance data from {path}")
    archs = _supported_archs_map()
    _current_analysis = JupyterAnalysis(str(path), archs, **kwargs)
    from utils.specs import generate_machine_specs
    sys_info = file_io.load_sys_info(str(path / "sysinfo.csv"))
    sys_info_dict = {k: v[0] for k, v in sys_info.to_dict("list").items()}
    mspec = generate_machine_specs(_current_analysis.get_args(), sys_info_dict)
    arch = mspec.gpu_arch
    import importlib
    soc_module = importlib.import_module(f"rocprof_compute_soc.soc_{arch}")
    soc_class = getattr(soc_module, f"{arch}_soc")
    omni_socs: dict[str, OmniSoC_Base] = {
        arch: soc_class(_current_analysis.get_args(), mspec)
    }
    _current_analysis.set_soc(omni_socs)
    _current_analysis.sanitize()
    _current_analysis.pre_processing()
    console_log("analysis", "Performance data loaded successfully")


def analysis(
    filter_kernel: Optional[list[str]] = None,
    filter_gpu: Optional[list[int]] = None,
    filter_dispatch: Optional[list[int]] = None,
    show_basic_only: bool = False,
) -> None:
    """
    Display analysis results in the notebook.

    Parameters
    ----------
    filter_kernel : list of str, optional
        Kernel IDs to include.
    filter_gpu : list of int, optional
        GPU IDs to include.
    filter_dispatch : list of int, optional
        Dispatch IDs to include.
    show_basic_only : bool, default False
        If True, show only basic panels (Top Stats, System Info, etc.).

    Raises
    ------
    SystemExit
        If :func:`open` has not been called first.

    Examples
    --------
    >>> import rocprof_compute_jupyter as rc
    >>> rc.open("/path/to/workload_dir")
    >>> rc.analysis()
    >>> rc.analysis(filter_kernel=["0", "1"], show_basic_only=False)
    """
    global _current_analysis
    if _current_analysis is None:
        console_error("analysis", "No data loaded. Call open(perf_data_dir) first.")
    _current_analysis.display_results(
        filter_kernel=filter_kernel,
        filter_gpu=filter_gpu,
        filter_dispatch=filter_dispatch,
        show_basic_only=show_basic_only,
    )


def get_dataframe(table_id: int) -> Optional[pd.DataFrame]:
    """
    Return a table by ID as a pandas DataFrame.

    Parameters
    ----------
    table_id : int
        Table ID (e.g. 1 = kernel top stats, 2 = dispatch list).

    Returns
    -------
    pandas.DataFrame or None
        The table if found, else None.

    Raises
    ------
    SystemExit
        If :func:`open` has not been called first.

    Examples
    --------
    >>> df = rc.get_dataframe(1)
    >>> df.head()
    """
    global _current_analysis
    if _current_analysis is None:
        console_error("analysis", "No data loaded. Call open(perf_data_dir) first.")
    base_data = _current_analysis._runs.get(_current_analysis.dest_dir)
    if base_data is None:
        return None
    return base_data.dfs.get(table_id)


def list_tables() -> None:
    """
    Print available table IDs and titles.

    Raises
    ------
    SystemExit
        If :func:`open` has not been called first.
    """
    global _current_analysis
    if _current_analysis is None:
        console_error("analysis", "No data loaded. Call open(perf_data_dir) first.")
    if not _current_analysis.arch or _current_analysis.arch not in _current_analysis._arch_configs:
        console_error("analysis", "Architecture configuration not found")
    arch_config = _current_analysis._arch_configs[_current_analysis.arch]
    panel_configs = arch_config.panel_configs
    print("Available tables:")
    print(f"{'ID':<8} {'Panel':<40} Table")
    print("-" * 80)
    for panel_id, panel in panel_configs.items():
        panel_title = f"{panel_id // 100}. {panel['title']}"
        for data_source in panel["data source"]:
            for _t_type, table_config in data_source.items():
                tid = table_config["id"]
                table_title = table_config.get("title", "")
                print(f"{tid:<8} {panel_title:<40} {table_title}")
