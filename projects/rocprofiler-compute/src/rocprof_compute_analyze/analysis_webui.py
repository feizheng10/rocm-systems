##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
##############################################################################

import argparse
import copy
import random
from pathlib import Path
from typing import Any, List, Optional

import holoviews as hv
import pandas as pd
import panel as pn

from config import HIDDEN_COLUMNS, PROJECT_NAME
from rocprof_compute_analyze.analysis_base import OmniAnalyze_Base
from utils import file_io, parser, schema
from utils.gui import build_bar_chart, build_table_chart
from utils.gui_components.header import get_header
from utils.gui_components.memchart import get_memchart_panel
from utils.logger import console_debug, console_error, console_log, console_warning, demarcate


class webui_analysis(OmniAnalyze_Base):
    def __init__(
        self, args: argparse.Namespace, supported_archs: dict[str, str]
    ) -> None:
        super().__init__(args, supported_archs)
        self.arch: Optional[str] = None
        self.__hidden_sections = ["Memory Chart"]
        self.__hidden_columns = HIDDEN_COLUMNS
        self.__barchart_elements: dict[str, list[int]] = {
            "instr_mix": [1001, 1002],
            "multi_bar": [1604, 1705],
            "sol": [1101, 1201, 1301, 1401, 1601, 1701],
        }
        self.__full_width_elements: set[int] = {1801}
        self.__roofline_data_type = args.roofline_data_type

    def _generate_content(
        self,
        disp_filt: list,
        kernel_filter: list,
        gcd_filter: list,
        norm_filt: str,
        top_n_filt: int,
    ) -> pn.Column:
        """Build Panel layout from current filter state (reactive content)."""
        base_run = getattr(self, "_gui_base_run", "")
        arch_configs = getattr(self, "_gui_arch_configs", None)
        comparable_columns = getattr(self, "_gui_comparable_columns", [])
        if not base_run or arch_configs is None:
            return pn.Column(
                pn.pane.Markdown("Loading...", styles={"color": "white"}),
                sizing_mode="stretch_width",
            )
        try:
            return self._build_content(
                base_run, arch_configs, comparable_columns,
                disp_filt or [], kernel_filter or [], gcd_filter or [],
                norm_filt, top_n_filt,
            )
        except Exception as e:
            return pn.Column(
                pn.pane.Markdown(
                    f"Error building content: {e!r}",
                    styles={"color": "#f88"},
                ),
                sizing_mode="stretch_width",
            )

    def _build_content(
        self,
        base_run: str,
        arch_configs: schema.ArchConfig,
        comparable_columns: list[str],
        disp_filt: list,
        kernel_filter: list,
        gcd_filter: list,
        norm_filt: str,
        top_n_filt: int,
    ) -> pn.Column:
        """Build Panel layout from current filter state (reactive content)."""
        args = self.get_args()
        base_data = self.initalize_runs(normalization_filter=norm_filt)
        panel_configs = copy.deepcopy(arch_configs.panel_configs)

        base_data[base_run].raw_pmc = file_io.create_df_pmc(
            self.dest_dir,
            args.nodes,
            args.spatial_multiplexing,
            args.kernel_verbose,
            args.verbose,
            self._profiling_config,
        )
        if args.spatial_multiplexing:
            base_data[base_run].raw_pmc = self.spatial_multiplex_merge_counters(
                base_data[base_run].raw_pmc
            )
        if self._profiling_config.get("iteration_multiplexing") is not None:
            base_data[base_run].raw_pmc = self.iteration_multiplex_impute_counters(
                base_data[base_run].raw_pmc,
                policy=self._profiling_config["iteration_multiplexing"],
            )

        console_debug("analysis", f"gui normalization is {norm_filt}")
        console_debug("analysis", f"gui dispatch filter is {disp_filt}")
        console_debug("analysis", f"gui kernel filter is {kernel_filter}")
        console_debug("analysis", f"gui gpu filter is {gcd_filter}")
        console_debug("analysis", f"gui top-n filter is {top_n_filt}")

        base_data[base_run].filter_kernel_ids = (
            [str(k) for k in kernel_filter] if kernel_filter else []
        )
        base_data[base_run].filter_gpu_ids = (
            [int(g) for g in gcd_filter] if gcd_filter else []
        )
        base_data[base_run].filter_dispatch_ids = (
            [int(d) for d in disp_filt] if disp_filt else []
        )
        base_data[base_run].filter_top_n = top_n_filt

        file_io.create_df_kernel_top_stats(
            df_in=base_data[base_run].raw_pmc,
            raw_data_dir=str(self.dest_dir),
            filter_gpu_ids=base_data[base_run].filter_gpu_ids,
            filter_dispatch_ids=base_data[base_run].filter_dispatch_ids,
            filter_nodes=self._runs[self.dest_dir].filter_nodes,
            time_unit=args.time_unit,
            kernel_verbose=args.kernel_verbose,
        )

        if not (disp_filt or kernel_filter or gcd_filter):
            basic_dfs_keep = [1, 2, 101, 201, 301, 401, 402]
            basic_panels_keep = [0, 100, 200, 300, 400]
            base_data[base_run].dfs = {
                k: base_data[base_run].dfs[k]
                for k in base_data[base_run].dfs
                if k in basic_dfs_keep
            }
            panel_configs = {
                k: panel_configs[k]
                for k in panel_configs
                if k in basic_panels_keep
            }

        parser.load_table_data(
            workload=base_data[base_run],
            dir_path=self.dest_dir,
            is_gui=True,
            args=args,
            config=self._profiling_config,
        )

        sections: List[Any] = []
        if 300 in panel_configs and panel_configs[300].get("data source"):
            sections.append(
                get_memchart_panel(
                    panel_configs[300]["data source"],
                    base_data[base_run],
                )
            )

        has_roofline = (Path(self.dest_dir) / "roofline.csv").is_file()
        soc = self.get_socs()
        if soc and self.arch and self.arch in soc and has_roofline:
            if hasattr(soc[self.arch], "roofline_obj"):
                soc[self.arch].analysis_setup(
                    roofline_parameters={
                        "workload_dir": self.dest_dir,
                        "device_id": 0,
                        "sort_type": "kernels",
                        "mem_level": "ALL",
                        "include_kernel_names": True,
                        "is_standalone": False,
                        "roofline_data_type": self.__roofline_data_type,
                        "kernel_filter": False,
                        "iteration_multiplexing": self._profiling_config.get(
                            "iteration_multiplexing"
                        ),
                    }
                )
                roof_result = soc[self.arch].roofline_obj.empirical_roofline(
                    ret_df=parser.apply_filters(
                        workload=base_data[base_run],
                        dir_path=self.dest_dir,
                        is_gui=True,
                        debug=args.debug,
                    )
                )
                if roof_result:
                    ops_fig, flops_fig = roof_result
                    roof_row = []
                    if ops_fig is not None:
                        roof_row.append(
                            pn.Column(
                                pn.pane.Markdown(
                                    "### Empirical Roofline Analysis (Ops)",
                                    styles={"color": "white"},
                                ),
                                pn.pane.Plotly(ops_fig, sizing_mode="stretch_width"),
                            )
                        )
                    if flops_fig is not None:
                        roof_row.append(
                            pn.Column(
                                pn.pane.Markdown(
                                    "### Empirical Roofline Analysis (Flops)",
                                    styles={"color": "white"},
                                ),
                                pn.pane.Plotly(flops_fig, sizing_mode="stretch_width"),
                            )
                        )
                    if roof_row:
                        sections.append(
                            pn.Column(
                                pn.pane.Markdown(
                                    "## Roofline",
                                    styles={"color": "white"},
                                ),
                                pn.Row(*roof_row, sizing_mode="stretch_width"),
                                name="roofline",
                            )
                        )

        for panel_id, panel in panel_configs.items():
            if panel["title"] in self.__hidden_sections:
                continue
            title = f"{panel_id // 100}. {panel['title']}"
            section_title = (
                panel["title"]
                .replace("(", "")
                .replace(")", "")
                .replace("/", "")
                .replace(" ", "_")
                .lower()
            )
            html_section: List[Any] = []
            for data_source in panel["data source"]:
                for t_type, table_config in data_source.items():
                    original_df = base_data[base_run].dfs.get(table_config["id"])
                    if original_df is None:
                        continue
                    if t_type == "raw_csv_table" and "Info" in original_df.keys():
                        original_df = original_df.reset_index()
                    content = determine_chart_type(
                        original_df=original_df,
                        table_config=table_config,
                        hidden_columns=self.__hidden_columns,
                        barchart_elements=self.__barchart_elements,
                        comparable_columns=comparable_columns,
                        decimal=args.decimal,
                    )
                    for c in content:
                        if isinstance(c, hv.Element):
                            html_section.append(pn.pane.HoloViews(c))
                        else:
                            html_section.append(c)

            panel_col = pn.Column(
                pn.pane.Markdown(f"## {title}", styles={"color": "white"}),
                pn.Row(*html_section, sizing_mode="stretch_width"),
                name=section_title,
            )
            sections.append(panel_col)

        if not (disp_filt or kernel_filter or gcd_filter):
            sections.append(
                pn.pane.Markdown(
                    "To dive deeper, use the top drop down menus to isolate "
                    "particular kernel(s) or dispatch(s). You will then see the "
                    "web page update with additional low-level metrics.",
                    styles={"color": "#aaa"},
                )
            )

        if not sections:
            sections.append(
                pn.pane.Markdown("No panels to display.", styles={"color": "#888"})
            )
        return pn.Column(
            *sections,
            sizing_mode="stretch_width",
            styles={"background": "rgb(50, 50, 50)", "padding": "12px"},
        )

    @demarcate
    def build_layout(
        self, input_filters: dict[str, Any], arch_configs: schema.ArchConfig
    ) -> None:
        """Build Panel GUI layout with reactive filters."""
        pn.extension("plotly", "tabulator")
        args = self.get_args()
        comparable_columns = parser.build_comparable_columns(args.time_unit)
        base_run, base_data = next(iter(self._runs.items()))

        kernel_top_df = base_data.dfs.get(1)
        filt_kernel_names: list[str] = []
        if kernel_top_df is not None:
            for kernel_id in base_data.filter_kernel_ids:
                if kernel_id in kernel_top_df.index:
                    filt_kernel_names.append(
                        str(kernel_top_df.loc[kernel_id, "Kernel_Name"])
                    )
        input_filters["kernel"] = filt_kernel_names

        header_col, widget_dict = get_header(
            base_data.raw_pmc, input_filters, filt_kernel_names
        )
        norm_filt = widget_dict["norm_filt"]
        gcd_filt = widget_dict["gcd_filt"]
        disp_filt = widget_dict["disp_filt"]
        top_n_filt = widget_dict["top_n_filt"]
        kernel_filt = widget_dict["kernel_filt"]

        # Store for _generate_content (avoids passing non-serializable objects to pn.bind)
        self._gui_base_run = base_run
        self._gui_arch_configs = arch_configs
        self._gui_comparable_columns = comparable_columns

        content = pn.bind(
            self._generate_content,
            disp_filt=disp_filt,
            kernel_filter=kernel_filt,
            gcd_filter=gcd_filt,
            norm_filt=norm_filt,
            top_n_filt=top_n_filt,
        )

        self._panel_layout = pn.Column(
            pn.pane.Markdown(
                f"# {PROJECT_NAME}",
                styles={"color": "white", "padding": "8px"},
            ),
            header_col,
            content,
            sizing_mode="stretch_width",
            styles={"background": "rgb(50, 50, 50)"},
        )

    # -----------------------
    # Required child methods
    # -----------------------
    @demarcate
    def pre_processing(self) -> None:
        """Perform any pre-processing steps prior to analysis."""
        super().pre_processing()
        if len(self._runs) != 1:
            console_error(
                "analysis",
                "Multiple runs not yet supported in GUI. Retry without --gui flag.",
            )
        args = self.get_args()
        self.dest_dir = str(Path(args.path[0][0]).absolute().resolve())
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
                policy=self._profiling_config["iteration_multiplexing"],
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

    @demarcate
    def run_analysis(self) -> None:
        """Run Panel web UI analysis."""
        super().run_analysis()
        args = self.get_args()
        input_filters = {
            "kernel": self._runs[self.dest_dir].filter_kernel_ids,
            "gpu": self._runs[self.dest_dir].filter_gpu_ids,
            "dispatch": self._runs[self.dest_dir].filter_dispatch_ids,
            "normalization": args.normal_unit,
            "top_n": args.max_stat_num,
        }
        if self.arch and self.arch in self._arch_configs:
            self.build_layout(input_filters, self._arch_configs[self.arch])
        port = random.randint(1024, 49151) if args.random_port else args.gui
        if hasattr(self, "_panel_layout") and self._panel_layout is not None:
            layout = self._panel_layout

            def get_app():
                # Same pattern as panel_demo_simple.py: return layout (or fallback on error)
                try:
                    return layout
                except Exception as e:
                    return pn.Column(
                        pn.pane.Markdown(f"# {PROJECT_NAME}"),
                        pn.pane.Markdown(f"Error loading app: {e!r}", styles={"color": "red"}),
                        sizing_mode="stretch_width",
                    )

            # Same pattern as working panel serve CLI: 0.0.0.0 + allow_websocket_origin=["*"] + prefix
            prefix = "app"
            apps = {prefix: get_app}
            console_log(
                "analysis",
                f"GUI server: open http://127.0.0.1:{port}/{prefix} or http://localhost:{port}/{prefix} "
                "(use 127.0.0.1 or localhost in browser, not 0.0.0.0)",
            )
            pn.serve(
                apps,
                port=port,
                address="0.0.0.0",
                title=PROJECT_NAME,
                show=False,
                allow_websocket_origin=["*"],
            )


@demarcate
def determine_chart_type(
    original_df: pd.DataFrame,
    table_config: dict[str, Any],
    hidden_columns: list[str],
    barchart_elements: dict[str, list[int]],
    comparable_columns: list[str],
    decimal: int,
) -> List[Any]:
    """Return list of Panel/HoloViews components (hv.Bars or pn.widgets.Tabulator)."""
    content: List[Any] = []
    if original_df.empty:
        console_warning(
            "analysis",
            f"The dataframe with id={table_config['id']} is empty! Not displaying it.",
        )
        return content
    display_columns = [
        c for c in original_df.columns.values.tolist() if c not in hidden_columns
    ]
    display_df = original_df[display_columns]

    if table_config["id"] in [
        x for i in barchart_elements.values() for x in i
    ]:
        d_figs = build_bar_chart(
            display_df, table_config, barchart_elements
        )
        for fig in d_figs:
            content.append(fig)
    else:
        d_figs = build_table_chart(
            display_df,
            table_config,
            original_df,
            display_columns,
            comparable_columns,
            decimal,
        )
        content.extend(d_figs)

    if table_config.get("title"):
        subtitle = (
            f"{table_config['id'] // 100}.{table_config['id'] % 100} "
            f"{table_config['title']}\n"
        )
        content.insert(0, pn.pane.Markdown(f"#### {subtitle}", styles={"color": "white"}))
    return content
