# PyCeler changelog

## 0.1.0 — 2026-11-09

- Added `PyCeler.Analyze` to identify and rank expensive loops without running the source. Findings include source locations and reasons a loop may be unsuitable for optimization.
- Added `PyCeler.Convert` to generate serial Cython for supported numeric loops, including array fills, copies, thresholds and bounded arithmetic. Loops with independent iterations can also use OpenMP.
- Added `PyCeler.Compile` to build native extensions. Existing Cython sources can be compiled directly with `Convert=False`. Builds default to individual native modules and the CPython 3.11 stable ABI.
- Added behavior checks and workload-based timing to select among Python, serial Cython and OpenMP. Runtime guards fall back to Python when inputs fall outside the selected specialization.
- Added optional profiling, thread and tile tuning, and caching for selection results and compiled extensions.
- Added a requirements file for installing the Python build dependencies.
