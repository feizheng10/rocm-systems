##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
##############################################################################

from typing import Any

import pandas as pd
import panel as pn

from utils import schema

AVAIL_NORMALIZATIONS = ["per_wave", "per_cycle", "per_second", "per_kernel"]


def list_unique(orig_list: list[str], is_numeric: bool) -> list[str]:
    list_set = set(orig_list)
    unique_list = list(list_set)
    if is_numeric:
        unique_list.sort()
    return unique_list


def get_header(
    raw_pmc: pd.DataFrame, input_filters: dict[str, Any], kernel_names: list[str]
) -> tuple[pn.Column, dict[str, Any]]:
    """
    Build Panel header with nav menu and filter widgets.
    Returns (layout_column, widget_dict) so the app can bind to widget values.
    widget_dict keys: norm_filt, gcd_filt, disp_filt, top_n_filt, kernel_filt
    """
    pmc_data = raw_pmc[schema.PMC_PERF_FILE_PREFIX]
    kernel_names = [str(name).strip() for name in pmc_data["Kernel_Name"]]
    gpu_ids = [str(gpu_id) for gpu_id in pmc_data["GPU_ID"]]
    dispatch_ids = [str(dispatch_id) for dispatch_id in pmc_data["Dispatch_ID"]]

    norm_filt = pn.widgets.Select(
        name="Normalization",
        options=AVAIL_NORMALIZATIONS,
        value=input_filters["normalization"],
        width=150,
    )
    gcd_filt = pn.widgets.MultiChoice(
        name="GCD",
        options=list_unique(gpu_ids, True),
        value=input_filters["gpu"] or [],
        placeholder="ALL",
        width=120,
    )
    disp_filt = pn.widgets.MultiChoice(
        name="Dispatch Filter",
        options=dispatch_ids,
        value=input_filters["dispatch"] or [],
        placeholder="ALL",
        width=180,
    )
    top_n_filt = pn.widgets.Select(
        name="Top N",
        options=[1, 5, 10, 15, 20, 50, 100],
        value=input_filters["top_n"],
        width=80,
    )
    kernel_filt = pn.widgets.MultiChoice(
        name="Kernels",
        options=list_unique(kernel_names, False),
        value=input_filters["kernel"] or [],
        placeholder="ALL",
        width=400,
    )

    # Section anchors for nav (same ids as before for deep links)
    section_links = [
        ("Roofline", "roofline"),
        ("Top Stats", "top_stats"),
        ("System Info", "system_info"),
        ("System Speed-of-Light", "system_speed-of-light"),
        ("Command Processor", "command_processor_cpccpf"),
        ("Workgroup Manager (SPI)", "workgroup_manager_spi"),
        ("Wavefront", "wavefront"),
        ("Instruction Mix", "compute_units_-_instruction_mix"),
        ("Compute Pipeline", "compute_units_-_compute_pipeline"),
        ("LDS", "local_data_share_lds"),
        ("Instruction Cache", "instruction_cache"),
        ("Scalar L1", "scalar_l1_data_cache"),
        ("TA/TD", "address_processing_unit_and_data_return_path_tatd"),
        ("Vector L1", "vector_l1_data_cache"),
        ("L2 Cache", "l2_cache"),
        ("L2 per channel", "l2_cache_per_channel"),
    ]
    menu = pn.widgets.Select(
        name="Menu",
        options=[""] + [label for label, _ in section_links],
        value="",
        width=180,
    )

    widget_dict = {
        "norm_filt": norm_filt,
        "gcd_filt": gcd_filt,
        "disp_filt": disp_filt,
        "top_n_filt": top_n_filt,
        "kernel_filt": kernel_filt,
        "menu": menu,
        "section_links": dict(section_links),
    }

    filter_row = pn.Row(
        menu,
        pn.Spacer(width=20),
        norm_filt,
        gcd_filt,
        disp_filt,
        top_n_filt,
        kernel_filt,
        pn.layout.HSpacer(),
        pn.pane.HTML(
            '<a href="https://github.com/ROCm/rocm-systems/issues" target="_blank">'
            '<button class="pn-btn">Report Bug</button></a>'
        ),
        sizing_mode="stretch_width",
        styles={"background": "#1e1e1e", "padding": "8px", "border-radius": "4px"},
    )

    banner = pn.pane.Markdown(
        "Placeholder. Guided Analysis coming soon...",
        styles={"color": "white", "padding": "8px"},
    )

    header_col = pn.Column(
        filter_row,
        banner,
        sizing_mode="stretch_width",
        styles={"background": "rgb(30, 30, 30)", "padding": "12px"},
    )
    return header_col, widget_dict
