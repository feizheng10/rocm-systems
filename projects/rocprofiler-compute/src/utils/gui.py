##############################################################################
# MIT License
#
# Copyright (c) 2021 - 2025 Advanced Micro Devices, Inc. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
##############################################################################

import html as html_module
from typing import Any

import pandas as pd

import holoviews as hv
import panel as pn

from utils.logger import console_error

pd.set_option("mode.chained_assignment", None)


def _html_escape(s: Any) -> str:
    """Escape for HTML attribute (e.g. title)."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return html_module.escape(str(s))

# HoloViews / Bokeh dark theme for consistency with app
BAR_OPTS = dict(
    width=500,
    height=400,
    toolbar=None,
    bgcolor="#323232",
    fontsize={"title": 11, "labels": 10, "xticks": 9, "yticks": 9},
    color="steelblue",
    fontcolor="white",
    xlabel="",
    ylabel="",
)


def multi_bar_chart(
    table_id: int, display_df: pd.DataFrame
) -> dict[str, dict[str, Any]]:
    nested_bar: dict[str, dict[str, Any]] = {}
    if table_id == 1604:
        for _, row in display_df.iterrows():
            coherency = row["Coherency"]
            if coherency not in nested_bar:
                nested_bar[coherency] = {}
            nested_bar[coherency][row["Xfer"]] = row["Avg"]
    elif table_id == 1705:
        for _, row in display_df.iterrows():
            transaction = row["Transaction"]
            if transaction not in nested_bar:
                nested_bar[transaction] = {}
            nested_bar[transaction][row["Type"]] = row["Avg"]
    return nested_bar


def _safe_numeric(series: pd.Series, as_int: bool = False):
    def _coerce(x):
        if x == "N/A" or pd.isna(x):
            return 0
        return int(x) if as_int else float(x)

    return series.apply(_coerce)


def create_instruction_mix_bar_chart(display_df: pd.DataFrame, df_unit: str) -> hv.Bars:
    display_df = display_df.copy()
    display_df["Avg"] = _safe_numeric(display_df["Avg"], as_int=True)
    return (
        hv.Bars(display_df, kdims="Metric", vdims="Avg")
        .opts(
            **BAR_OPTS,
            height=400,
            xlabel=f"# of {df_unit.lower()}",
            invert_axes=True,
        )
    )


def create_multi_bar_charts(
    display_df: pd.DataFrame, table_id: int, df_unit: str
) -> list[hv.Bars]:
    display_df = display_df.copy()
    display_df["Avg"] = _safe_numeric(display_df["Avg"], as_int=True)
    nested_bar = multi_bar_chart(table_id, display_df)
    charts = []
    for group, metric in nested_bar.items():
        df = pd.DataFrame(
            list(metric.items()), columns=["y", "x"]
        )  # orientation 'h' -> y=names, x=values
        bars = hv.Bars(df, kdims="y", vdims="x").opts(
            **BAR_OPTS,
            height=200,
            title=group,
            xlabel=df_unit,
            invert_axes=True,
        )
        charts.append(bars)
    return charts


def create_sol_charts(display_df: pd.DataFrame, table_id: int) -> list[hv.Bars]:
    display_df = display_df.copy()
    display_df["Avg"] = _safe_numeric(display_df["Avg"], as_int=False)
    charts = []

    if table_id == 1701:
        pct_data = display_df[display_df["Unit"] == "Pct"]
        if not pct_data.empty:
            charts.append(
                hv.Bars(pct_data, kdims="Metric", vdims="Avg")
                .opts(
                    **BAR_OPTS,
                    height=220,
                    xlabel="%",
                    invert_axes=True,
                    xlim=(0, 110),
                )
            )
        hbm_row = display_df[display_df["Metric"] == "HBM Bandwidth"]
        if not hbm_row.empty:
            hbm_bw = float(hbm_row["Avg"].iloc[0])
            gb_data = display_df[display_df["Unit"] == "Gb/s"]
            if not gb_data.empty:
                charts.append(
                    hv.Bars(gb_data, kdims="Metric", vdims="Avg")
                    .opts(
                        **BAR_OPTS,
                        height=220,
                        xlabel="GB/s",
                        invert_axes=True,
                        xlim=(0, hbm_bw),
                    )
                )
    elif table_id == 1101:
        display_df["Pct of Peak"] = _safe_numeric(
            display_df["Pct of Peak"], as_int=False
        )
        charts.append(
            hv.Bars(display_df, kdims="Metric", vdims="Pct of Peak")
            .opts(
                **BAR_OPTS,
                height=400,
                xlabel="%",
                invert_axes=True,
                xlim=(0, 110),
            )
        )
    else:
        charts.append(
            hv.Bars(display_df, kdims="Metric", vdims="Avg")
            .opts(
                **BAR_OPTS,
                height=400,
                xlabel="%",
                invert_axes=True,
                xlim=(0, 110),
            )
        )
    return charts


def build_bar_chart(
    display_df: pd.DataFrame,
    table_config: dict[str, Any],
    barchart_elements: dict[str, Any],
) -> list[hv.Bars]:
    """Build HoloViews bar charts. Returns list of hv.Bars for Panel embedding."""
    table_id = table_config["id"]
    charts: list[hv.Bars] = []
    df_unit = display_df["Unit"].iloc[0] if "Unit" in display_df.columns else ""

    if table_id in barchart_elements["instr_mix"]:
        charts.append(create_instruction_mix_bar_chart(display_df, df_unit))
    elif table_id in barchart_elements["multi_bar"]:
        charts.extend(create_multi_bar_charts(display_df, table_id, df_unit))
    elif table_id in barchart_elements["sol"]:
        charts.extend(create_sol_charts(display_df, table_id))
    else:
        console_error(
            f"Table id {table_id}. Cannot determine barchart type.", exit=False
        )
    return charts


def get_dark_mode_styles() -> tuple[
    dict[str, Any], dict[str, Any], list[dict[str, Any]]
]:
    """Legacy style dicts; Panel uses theme. Kept for any programmatic use."""
    style_header = {
        "backgroundColor": "rgb(30, 30, 30)",
        "color": "white",
        "fontWeight": "bold",
    }
    style_data = {
        "backgroundColor": "rgb(50, 50, 50)",
        "color": "white",
        "whiteSpace": "normal",
        "height": "auto",
    }
    style_data_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": "rgb(60, 60, 60)"}
    ]
    return style_header, style_data, style_data_conditional


def build_table_chart(
    display_df: pd.DataFrame,
    table_config: dict[str, Any],
    original_df: pd.DataFrame,
    display_columns: list[str],
    comparable_columns: list[str],
    decimal: int,
) -> list[pn.widgets.Tabulator]:
    """Build Panel Tabulator table(s) from dataframe.
    If original_df has a 'Description' column (metrics_description), it is included
    in the data but hidden; row hover shows it as a tooltip.
    """
    formatted = display_df.copy()
    for col in formatted.columns:
        col_lower = str(col).lower()
        if col_lower in {"pct", "pop", "percentage"} or col in comparable_columns:
            formatted[col] = pd.to_numeric(formatted[col], errors="coerce")

    # Include Description for row hover tooltip; do not show as a column
    has_description = "Description" in original_df.columns
    if has_description:
        formatted["Description"] = original_df["Description"].values

    tbl_kw: dict[str, Any] = dict(
        value=formatted,
        theme="midnight",
        layout="fit_data",
        sizing_mode="stretch_width",
        show_index=False,
        page_size=20,
    )
    if has_description:
        tbl_kw["hidden_columns"] = ["Description"]
        # Build first-column HTML in Python (JSON can't send formatter functions).
        # Use Tabulator's built-in "html" formatter so the cell renders as HTML and title= shows on hover.
        first_col = formatted.columns[0]
        desc_series = formatted["Description"]
        first_series = formatted[first_col]
        formatted[first_col] = [
            f'<span title="{_html_escape(d)}">{_html_escape(v)}</span>'
            for d, v in zip(desc_series, first_series)
        ]
        tbl_kw["configuration"] = {
            "columns": [
                {"title": str(col), "field": str(col), "formatter": "html"}
                if col == first_col
                else {"title": str(col), "field": str(col)}
                for col in formatted.columns
            ]
        }
    tbl = pn.widgets.Tabulator(**tbl_kw)
    return [tbl]
