# Running the PyCeler tests

From the project root on Windows, build the engine and run the tests.

```powershell
python -B Compile.py
.\Test\Run.ps1
```

On Linux AMD64 or ARM64, run `python3 -B Compile.py` followed by `python3 -B Test/Run.py`. The build writes the complete compiled library to `Build/Lib/PyCeler`; checkout imports use that package rather than an in-place engine binary. Install Cython, setuptools and NumPy in the test interpreter and provide the platform compiler and OpenMP runtime. The suite builds and imports real native modules in disposable directories under `Test_Run/`.

## Where to find results

The runner prints `Report:` followed by the absolute path to `Test_Run/Run_<id>/Results.txt` before the first test. At the end it prints the contents of that file, including the platform, Python version, each test outcome, failure tracebacks when present, and the summary. A successful run exits with code 0. A failed or empty suite exits with a nonzero code. Test workspaces use bounded retries for transient Windows locks on recently loaded native images; persistent cleanup errors still fail the run.

Each invocation gets a fresh directory. The standalone benchmarks create sibling directories under the same root.

```text
Test_Run/
├── Run_<id>/Results.txt
├── Benchmark_Loops_<id>/Timings.json
└── Survey_<id>/
    ├── Survey_Workload.py
    ├── Analysis.json
    ├── Results.json
    ├── Converted/
    ├── Native/
    └── Plain/
```

The survey’s `Converted/` directory contains the generated Cython source, `Native/` contains the PyCeler build, and `Plain/` contains the plain-Cython comparison build. The two benchmark commands below create their respective JSON reports. Git ignores all of `Test_Run/`.

## What the regression suite checks

The baseline cases use lists and check values and object identity for empty, single-element and multi-element inputs. The detector cases assert classifications, inclusive line spans, indexed accesses and reasons. `Static_Only_Loops.py` deliberately raises at module scope so that importing or executing it during analysis fails the test.

The pipeline tests compare serial and OpenMP execution with Python, exercise unsupported arrays and Python objects, check preview and conversion, and import a package built in both native layouts. Inspect the reference loops from the project root with this command.

```powershell
python -B -c "import PyCeler; print(*PyCeler.Analyze('Test/Numeric_Loops.py'), sep=chr(10))"
```

`Map_Loops.py` and `Map_Probe.py` cover typed 1D/2D kernels with four numeric dtypes. The suite builds both serial and OpenMP versions, compares them with Python, and observes native dispatch and fallback separately. Cases include shape locals, read-only sources, incompatible destinations, exact and shifted aliases, signed zero, NaN, intermediate integer overflow, floating-point overflow, partial mutation before an exception, and worker-thread calls. Run `python -B Compile.py analyze --input Test/Map_Loops.py --openmp` to inspect the plans.

`Analyze` accepts a Python file path and returns a tuple of `Loop_Finding` records in source traversal order. Line numbers are one-based and inclusive. Indexed accesses describe the loop body's subscript expressions, with nested loops reported separately. A potential independent write still requires the built-in iteration functions and verified array properties described in its reason.

Add cases in `Test_*.py` files using `unittest.TestCase` and `test_` methods. The runner discovers these files automatically. Keep reusable input programs in this folder and generated artifacts under the project's `Test_Run/` directory.

## Structural optimization and distribution coverage

`Structural_Loops.py`, `Structural_Probe.py` and `Test_Structural.py` exercise adjacent-loop fusion, invariant scalar products, repeated expressions, typed local values, versioned reads, column-first interchange and explicitly enabled temporary elimination. Native comparisons include integer dtypes, floating fallback, empty and tiny arrays, exact/shifted aliases, overflow warnings, too-short outputs with partial mutation, and noncontiguous inputs. Profiling verifies that eligible calls actually enter native kernels. The measured case requires valid unfused serial and optimized serial timings, then forces a Python-only policy to check fallback generation.

`Test_Cython_Sources.py` checks native parser findings, included source locations, source-byte preservation and unsupported compile-time expressions. `Test_Compile_Only.py` covers direct Python/Cython/include builds, dependency staging, grouped packages and bypass of analysis/selection. `Test_Ranking.py` checks conservative static ranking without changing finding order.

`Test_Optimization_Selection.py` covers representative factories, holdout dispatch, alias-preserving input copies, warnings, signed zero, cache integrity and compatibility changes. Its public conversion case verifies holdouts, a cache miss followed by a hit, no repeated probe builds, and byte-identical generated source. `Representative_Workloads.py` supplies input factories independently of chat or agent state.

`Test_Package_Build.py`, `Test_Environment_Checker.py`, and `Test_Source_Bootstrap.py` cover the compiled-only distribution layout, resource embedding, interpreter-target checks, diagnostics and checkout import routing. Package publication tests import the builder from root `Compile.py` and use a mocked backend. `Test_Distribution.py` copies the built native modules and initializer into an isolated directory, then runs Analyze, Convert and measured Compile without helper sources or templates. GitHub Actions defines Windows x64, Linux AMD64 and Linux ARM64 jobs for CPython 3.11 and 3.14.

The maintained suite contains **85 optimizer tests**, all of which passed in the latest full run on 2026-11-09. That run used AMD64 CPython 3.14.8 on Windows 11 ARM64, MSVC 14.44, Cython 3.3.0 and NumPy 2.5.4. The one-time installer tests have been removed permanently and are outside this project's verification scope. No tests were rerun for that removal. Linux native execution awaits a host as requested. Exact commands and historical result paths are recorded in `Session.md`.

For a source-only check, run `python -B Test/Check_Syntax.py`. It parses maintained Python files and translates every distribution module into disposable C sources under `Test_Run/Cython_Review_*/`, including embedded runtime resources. It does not invoke a native compiler, load the generated engine, run behavioral tests or benchmark code. `Results.json` records the platform, versions and translation diagnostics.

## Optimizer follow-up checks

`Test_Structural.py` runs `Randomized_Probe.py` for both serial and OpenMP builds: 576 deterministic cases each, covering eight dtypes and six structural families. Comparisons include result types, bytes, signed zero, warnings, exceptions, mutations, overlapping views, strides, read-only arrays, shape errors and nonnative byte order. Eligible integral-valued float maps must actually enter the native kernel. Failed cases save their seed, case index and a replay command under `Test_Run/Randomized_Failures/`.

`Test_Native_Optimization.py` compares unchanged and optimized typed Cython fills, checks special float values and invalid arguments, rejects unsafe source context, and compiles standalone `.pxi` input. A deliberately unattainable speed threshold must preserve the original source exactly. `Test_Numeric_Extensions.py` uses independent partition-based median and scalar channel-distance oracles, including empty/thin arrays and borders, and requires native entry for eligible cases. Temporary-list elision remains explicit.

`Test_Binary_Cache.py` verifies repeated builds without a compiler worker, include and external compiler-header invalidation, per-module rebuilds, artifact corruption repair, flag changes and grouped loaders. Run `python -B Test/Benchmark_Binary_Cache.py` for cold-versus-cached wall times on a 500-function module (about 1,500 lines); all functions execute correctly after each build and cached binary bytes must match.

`Test_Tuning.py` builds serial, two tile sizes and two OpenMP team configurations for a real filter. It checks validation evidence, profiling summaries, independent output values and unchanged caller thread settings, including rejected-candidate fallback. Additional native builds cover tuned fills, element-wise maps, structural maps and medians. For a focused run, use:

```powershell
python -B -m unittest Test.Test_Structural Test.Test_Native_Optimization Test.Test_Numeric_Extensions Test.Test_Binary_Cache Test.Test_Tuning -v
```

## Prepared Linux checks

Linux execution is deferred until a native AMD64 or ARM64 host is available. `.github/workflows/Native_Regression.yml` prepares Windows x64, Linux AMD64 and Linux ARM64 jobs with CPython 3.11 and 3.14. Each job builds the package, runs the complete suite, probes serial/OpenMP support and imports the same stable-ABI fixture on both Python versions. Upload the project to an authorized GitHub repository and run the workflow, or execute these commands on each native Linux host:

```sh
python3 -m pip install "Cython>=3.1" setuptools numpy
python3 -B Compile.py
python3 -B Test/Run.py
python3 -B Compile.py doctor --build-check --build Test_Run/Doctor
python3 -B Compile.py compile --input Test/ABI_Loops.py --output Test_Run/ABI/Native --no-select --openmp
python3.11 -B Test/Verify_ABI.py Test_Run/ABI/Native
python3.14 -B Test/Verify_ABI.py Test_Run/ABI/Native
```

Install GCC/G++, Python development headers and the OpenMP runtime through that host's package manager first. Both smoke-test interpreters need NumPy and Cython. Preserve `Test_Run/**/Results.txt`, JSON reports and `Build/Logs/*.log`. No Linux success is claimed from Windows verification.

`Loop_Workloads.py` and `Loop_Probe.py` exercise native scalar counting, dependent while conditions, nested ranges with negative steps, break/continue, zero iterations, integer overflow, and mixed for/while array loops in three and four dimensions.

`Test_Selection.py` exercises the default measured conversion and compilation paths, including three actual candidates on independent arrays, grouped loop findings, exact result and mutation checks, optional build failures, Python wins, and bounded probing of a nonterminating function. `Selection_Probe.py` imports the final extension in a fresh process and checks each measured case against its recorded dispatch decision. A second import changes the thread environment and checks Python fallback. The raw-kernel regression cases explicitly pass `Select=False`.

To produce an inspectable selection report and generated source for scalar counting and nested arrays, run the following from the project root.

```powershell
$env:OMP_NUM_THREADS = "2"
python -B Compile.py convert --input Test/Loop_Workloads.py --output Test_Run/Measured_Loops --build Test_Run/Measured_Build
```

Run `python -B Test/Benchmark_Loops.py` separately to benchmark scalar counting and a 3D int32 threshold. It builds the extensions before timing, checks outputs against Python, warms up each candidate, then interleaves their timings in a reproducible shuffled order. Calls include runtime dispatch and guards. Array inputs and output buffers are prepared outside the timed region. The runner configures two OpenMP threads and measures nine batches per case, extending to eighteen for noisy or close comparisons. `Test_Run/Benchmark_Loops_*/Timings.json` records workload shapes, calls per batch, raw per-call samples, medians, minima, coefficient of variation, speedups and environment.

## Large mixed Python module

`python -B Test/Benchmark_Large_Source.py --compile-only` generates 699-, 3,499- and 10,499-line structural modules. It checks read-only analysis, complete loop coverage and transformation membership across three runs per size. It then compiles the largest module without conversion, imports it in an isolated process, exercises every one of its 1,500 functions, checks source preservation and rejects nonbinary output. Results stay in `Test_Run/Large_Source_*/Results.json`. Omit `--compile-only` for an analysis-only measurement.

`python -B Test/Benchmark_Structural.py` supplies six representative sizes per function through `Structural_Workloads.py`, with three marked as holdouts. It requires valid serial and optimized candidates, compiles the selected policy, independently compares the final module with Python on all 21 holdouts, then interleaves nine timed full calls after two warmups. Results and detailed selection timings against the unfused serial control stay in `Test_Run/Structural_Benchmark_*/`. Temporary allocation elimination is explicitly enabled for this benchmark.

To compare two existing structural binaries on the same inputs in one process, run `python -B Test/Compare_Structural.py BEFORE/Structural_Loops.pyd AFTER/Structural_Loops.pyd` (use `.so` on Linux). It validates both against Python, then interleaves 15 timed batches after two warmups for every holdout. `Test_Run/Structural_Comparison_*/Results.json` records the binary paths/hashes, complete-call samples and before/after speed ratios.

Each of the 22 masked neighborhood filters contributes two loop findings and one extracted kernel.

Run `python -B Test/Benchmark_Survey.py` from the project root with the local engine built. Each run writes a standalone `Survey_Workload.py` under `Test_Run/Survey_*/`. The generator combines `Survey_Pipeline.py.in` and 22 distinct filter definitions into one module. The survey pipeline thresholds a 3D volume, calibrates and compares 2D frames, counts scalar scan positions, builds a prefix profile, labels connected regions, and runs mask-aware neighborhood filters on a downsampled frame.

The runner records separate wall times for the public `Analyze`, `Convert` and `Compile` calls. `Compile` repeats selection as part of its normal workflow. A separate control compiles the original Python source as plain Cython with the same backend and ABI. The source hash, detected loop locations, emitted Cython, both binaries, and selection reports stay in the run directory.

The correctness checks compare all three implementations on fixed-seed holdout shapes and exercise return identity, input mutation, exceptions, warnings and partial writes. A vectorized reference checks every filter on a masked noncontiguous grid and a grid smaller than its kernel. A constant survey provides independent expected values for the combined pipeline. A fresh process inherits the two-thread OpenMP settings, warms each implementation and interleaves nine timed batches per workload. Preparation runs outside the timer. The complete survey includes its own allocations, filtering and reporting. `Results.json` contains per-call samples, medians, minima, variation, and dispatch observations for each eligible kernel. Seven separate instrumented large runs measure how much time each stage takes within the complete survey.

Structural fixtures also cover implicit and explicit `None` returns. The probe checks the returned value as well as mutations, tests partial writes before an exception, and requires eligible cases to enter the native implementation.

## Stable-ABI smoke check

Build the fixture with the current interpreter, then run it with another installed GIL-enabled CPython version at or above the 3.11 ABI floor. NumPy must be available to that runtime. For example, on Windows:

```powershell
python -B Compile.py compile --input Test/ABI_Loops.py --output Test_Run/ABI/Native --build Test_Run/ABI/Build --no-select --openmp
py -3.11 -B Test/Verify_ABI.py Test_Run/ABI/Native
```

`Verify_ABI.py` imports the actual package from `Build/Lib`, exercises Analyze and Convert, checks four scalar cases and twelve typed-array calls, and asserts that the array cases avoid Python fallback. It writes `ABI_<minor>.json` beside the native output directory. Its optional `--numpy DIRECTORY` supports a separate runtime-specific dependency directory. On Linux use the corresponding installed Python executable.

## Classic image processing and EnIP transport

The reference review covered 84 Python and Cython source files under XenonixLib Classic and 16 each under EnIP Adapter and Scanner. Classic contained 66 `prange` sites across 23 files. Both transport directories used ordered I/O and buffer helpers. PyCeler accepts Python source. The portable tests use Python equivalents of the operations in the reference code.

| Reference pattern | Current conversion | Regression or boundary |
| --- | --- | --- |
| Classic edge fitting, line-inlier scan | Score direct or indexed 2D points using a signed projection, optional label/stripe gates and an integer count. Check index bounds and preserve arithmetic order. Try parallel scoring over points. | Equal-scoring models keep the first winner. Random sampling and model selection run in sequence. |
| Classic texture assignment | Scan each row for the first best index. Distinct rows can run in parallel. | Strided distances, equal scores, empty columns, partial row ranges, NaN fallback and uint8 label capacity. |
| Classic image and depth processing | Fixed-offset weighted sums with a boolean validity mask can use typed source views and independent destination rows. | All 22 survey filters have an independent oracle. A clipped median fixture checks missing pixels and round-to-even border values on the preserved path. |
| Classic point and texture pipelines | Extract eligible element-wise loops after local allocation or calls and inside longer functions or class methods. | The callback test records exactly one call. Channel-wise floating reductions, voting tables and arbitrary calls inside the hot loop remain outside the supported patterns. |
| Narrow integer pixel transforms | Use typed element-wise kernels for int8, uint8, int16 and uint16 when input scalars, literals and arithmetic fit. | The map probe checks native dispatch, overflowing intermediate arithmetic, out-of-range thresholds and partial writes. |
| EnIP Adapter and Scanner consumed buffers | Copy a verified byte span and zero-fill the unused tail. Sources can be bytes, bytearrays or supported byte memoryviews. | Validate short frames, fallback after partial mutation and output identity. The helper requires a bound local or argument for the target buffer. |
| EnIP TCP exact reads and ordered receive/send loops | Generate a serial Cython candidate for the recognized fragmented-read loop. Extract eligible buffer operations from other receive loops. | Scripted reads exercise request lengths, partial EOF, timeouts and errors. A local socket pair checks the same receive function with OS sockets. Scheduler deadlines, socket readiness and send order stay with the original code. |

Run `python -B Test/Run.py` for the regression report. `Test_Classic_Transport.py` builds manual serial, manual OpenMP and measured variants, then `Classic_Transport_Probe.py` imports each binary in a fresh process. To inspect per-region source and timings separately, run the following from the project root.

```powershell
$env:OMP_NUM_THREADS = "2"
python -B Compile.py convert --input Test/Classic_Transport_Loops.py --output Test_Run/Classic_Transport
```

The resulting `Classic_Transport_Loops.selection.json` records candidates, validation, timings and winners per region. The receive timings cover in-memory fragment handling. Live network latency and controller performance require measurements on the deployment workload.

The largest concentrations of explicit parallel loops in the reference were the cloud, cloud-selection and cloud-pixel files (23 sites together), depth and its related includes (14 sites), texture (7) and image skeleton processing (6). These counts describe the reference implementation. `Classic_Dependencies.py` exercises three boundaries from this review: colliding scatter writes with first-winner ties, per-group floating additions whose result depends on order, and clipped depth medians with mutable scratch storage. The suite checks their skip reports and builds the module to verify the resulting behavior.
