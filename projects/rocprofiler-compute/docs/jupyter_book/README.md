# Jupyter Book for ROCProfiler-Compute

This directory contains the source for the **Jupyter Book** build: intro, API reference, and links to the example notebook.

## Build the book

From the **project root** (rocprofiler-compute):

```bash
pip install jupyter-book
jupyter book build docs/jupyter_book/
```

Output is in `docs/jupyter_book/_build/html/`. Open `index.html` in a browser.

## Contents

- **intro**: Introduction and quick start
- **api**: Jupyter API reference (`open`, `analysis`, `get_dataframe`, `list_tables`)

The **example notebook** lives in the repo at `examples/jupyter_analysis_example.ipynb`.

## API module

The Python API is implemented in `src/rocprof_compute_jupyter.py`. Use it in any Jupyter notebook or script by adding `src` to `sys.path` and `import rocprof_compute_jupyter as rc`.
