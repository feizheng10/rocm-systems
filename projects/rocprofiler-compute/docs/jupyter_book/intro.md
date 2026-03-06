# ROCProfiler-Compute in Jupyter

This book describes how to use **rocprofiler-compute** inside Jupyter notebooks and Jupyter Book.

## What is the Jupyter API?

The `rocprof_compute_jupyter` module provides a small, stable API for:

1. **Loading** performance data from a workload directory
2. **Displaying** analysis results as tables in the notebook
3. **Accessing** raw tables as pandas DataFrames for custom analysis

## Quick start

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("path/to/rocprofiler-compute/src").resolve()))

import rocprof_compute_jupyter as rc

rc.open("/path/to/workload_dir")   # load data
rc.analysis()                      # show results in the notebook
df = rc.get_dataframe(1)           # get kernel top stats as DataFrame
```

## Requirements

- Profiling data produced by `rocprof-compute profile` (or equivalent)
- Python environment with rocprofiler-compute dependencies (see main docs)
- For notebooks: Jupyter or JupyterLab

## See also

- **API Reference** (next page) for full function and parameter details
- **Example notebook**: `examples/jupyter_analysis_example.ipynb` in the repo
