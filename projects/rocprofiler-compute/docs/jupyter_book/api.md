# Jupyter API Reference

The Jupyter API is provided by the module `rocprof_compute_jupyter`. Import it as:

```python
import rocprof_compute_jupyter as rc
```

All functions use shared state: call `rc.open(perf_data_dir)` once to load data, then call `rc.analysis()`, `rc.get_dataframe()`, or `rc.list_tables()` as needed.

---

## `open(perf_data_dir, **kwargs)`

Load performance data from a directory and prepare for analysis.

**Parameters**

| Parameter        | Type  | Description |
|-----------------|-------|-------------|
| `perf_data_dir` | `str` | Path to the workload directory (must contain `sysinfo.csv`, PMC data, etc.). |
| `**kwargs`      |       | Optional: `kernel_filter`, `gpu_filter`, `dispatch_filter`, `time_unit`, `normal_unit`, `max_stat_num`, `decimal`, `spatial_multiplexing`, and other options. |

**Raises**

- Exits if `perf_data_dir` is not a valid directory.

**Example**

```python
rc.open("/path/to/workload_dir")
rc.open("/path/to/workload", time_unit="us", max_stat_num=20)
```

---

## `analysis(filter_kernel=None, filter_gpu=None, filter_dispatch=None, show_basic_only=False)`

Display analysis results in the notebook (tables rendered inline).

**Parameters**

| Parameter         | Type           | Default | Description |
|------------------|----------------|--------|-------------|
| `filter_kernel`  | `list[str]`    | `None` | Kernel IDs to include. |
| `filter_gpu`     | `list[int]`    | `None` | GPU IDs to include. |
| `filter_dispatch`| `list[int]`    | `None` | Dispatch IDs to include. |
| `show_basic_only`| `bool`         | `False`| If `True`, show only basic panels (e.g. Top Stats, System Info). |

**Raises**

- Exits if `open()` has not been called first.

**Example**

```python
rc.analysis()
rc.analysis(filter_kernel=["0", "1"])
rc.analysis(filter_gpu=[0], show_basic_only=False)
```

---

## `get_dataframe(table_id)`

Return a table by ID as a pandas DataFrame.

**Parameters**

| Parameter   | Type | Description |
|------------|------|-------------|
| `table_id` | `int`| Table ID (e.g. `1` = kernel top stats, `2` = dispatch list). |

**Returns**

- `pandas.DataFrame` or `None` if the table is not found.

**Raises**

- Exits if `open()` has not been called first.

**Example**

```python
kernel_stats = rc.get_dataframe(1)
dispatch_list = rc.get_dataframe(2)
if kernel_stats is not None:
    display(kernel_stats.head())
```

---

## `list_tables()`

Print available table IDs and their titles to stdout.

**Raises**

- Exits if `open()` has not been called first.

**Example**

```python
rc.open("/path/to/workload_dir")
rc.list_tables()
```

---

## Design notes

- **Stateful**: One workload is loaded at a time via `open()`. Calling `open()` again replaces the current workload.
- **Tables only**: Results are shown as pandas DataFrames (no embedded GUI or charts in this API).
- **Architecture**: The module uses the same analysis pipeline as the CLI; the workload’s `sysinfo.csv` determines the GPU architecture and which metrics are available.
