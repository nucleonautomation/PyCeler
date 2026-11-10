# PyCeler changelog

## 0.2.0 — Unreleased

- Added `Test/Run.py --no-wheels` to run optimizer regressions while excluding wheel creation. The PowerShell runner forwards command-line options.
- Added Python-compatible scalar modulo, floor division and guarded true-division reductions, plus exact serial and OpenMP integer sums with matching arithmetic proofs.
- Extended function-local numeric regions to signed literal strides and periodic callbacks, and structural maps to independent augmented assignments.
- Preserved Python behavior for module code and fallback functions, including identity-sensitive values, exceptions, annotations, decorators and signal-visible globals.
- Added location-specific diagnostics, comprehension detection, reports for empty and unmeasured conversions, and more accurate workload sizing.
- Strengthened selection validation for aliases, cycles, array storage and exceptions. Added bounded input copies, measurement deadlines, representative-workload priorities and explicit coverage/extrapolation reporting.
- Added opt-in reporting of selected policies, actual native entry, fallback and OpenMP worker teams. Runtime setting changes invalidate measured dispatch.
- Added source/dependency fingerprints, build IDs and artifact hashes to detect stale or modified development packages. Improved recovery from corrupted selection-cache entries.
- Added deterministic wheel packaging from verified native artifacts and native-platform CI definitions, plus generated-program, signal, dispatch and ABI regressions.

## 0.1.0 — 2026-11-09

- Added CPython 3.11 stable-ABI wheels for Windows x64, Linux x86-64 and Linux ARM64.
- Added `PyCeler.Analyze` to identify and rank expensive loops without running the source. Findings include source locations and reasons a loop may be unsuitable for optimization.
- Added `PyCeler.Convert` to generate serial Cython for supported numeric loops, including array fills, copies, thresholds and bounded arithmetic. Loops with independent iterations can also use OpenMP.
- Added `PyCeler.Compile` to build native extensions. Existing Cython sources can be compiled directly with `Convert=False`. Builds default to individual native modules and the CPython 3.11 stable ABI.
- Added behavior checks and workload-based timing to select among Python, serial Cython and OpenMP. Runtime guards fall back to Python when inputs fall outside the selected specialization.
- Added optional profiling, thread and tile tuning, and caching for selection results and compiled extensions.
- Added a requirements file for installing the Python build dependencies.
