# Running the PyCeler tests

The current release source is **0.3.0**. Its version assertions and wheel metadata fixtures are aligned with that version. Runtime tests and benchmarks have not been run for this release; the 0.2.0 results below are historical and do not establish 0.3.0 qualification.

Testing and benchmarks are stopped at the user's request on 2026-11-12. The commands below document how to resume after renewed authorization. Newly integrated binary-math source and tests have not run; the results below qualify the earlier installed ba1 checkpoint. Linux's full suite was interrupted when its registered WSL disk disappeared, so its full-suite/wheel qualification remains incomplete.

## Historical 0.2.0 qualification — 2026-11-12

Build ba1f9696 is installed and delivered locally, with version 0.2.0 unchanged. Both full Windows interpreter suites discovered 271 tests: 269 passed and two POSIX-only ownership checks were skipped on each. Python 3.14 took 1020.834 seconds (`Test_Run/Run_kkg5qexw/Results.txt`); isolated Python 3.11 took 1107.706 seconds (`Test_Run/Run_8sbovsvt/Results.txt`, build d101c94f). `Test_Run/Resume_Full_Suites_20261112.json` verifies all 63 maintained package source hashes and 20 artifacts for each build.

Both exact-wheel pipeline probes passed in `Test_Run/Resume_Wheel_314_20261112` and `Test_Run/Resume_Wheel_311_20261112`; the latter also passed all 14 additional same-artifact checks. Observer reports passed 30/30 each at `Test_Run/Math_Observers_7ems8ihw/Verification_nc6655qi/Results.json` (3.14) and `Test_Run/Resume_Observers_Corpus_311_20261112/Verification_rqj7g3cc/Results.json` (3.11). The second report reuses the hash-verified binary retained from the successful full suite.

The unchanged user benchmark passed three interleaved complete imports per candidate with exact final globals and all nine progress values. Default measured conversion won with median 0.116342 seconds, 1,530 native parallel spans, actual team eight and one tiny Python span. The separate two-worker candidate took 0.1258658 seconds. `Test_Run/Resume_Installed_20261112/Results.json` records the selection; the delivered runner reproduces the winning runtime environment and checks its actual counters. Downloads/Benchmark.py remains unchanged; Downloads/Benchmark.pyx contains the verified generated code.

Fresh nine-sample math reports are `Test_Run/Math_Benchmark_wovm2kpt/Results.json` and `Test_Run/Erf_Benchmark_v6b1h7mb/Results.json`. They preserve exact output bits and observed native elements/teams. Small inputs favor Python. All 1,131 Python loop forms in 139 maintained files are accounted for in `Test_Run/Coverage_Baseline_doio90rz/Summary.json` (1,140 total findings, sources unchanged). Static accounting does not establish native execution.

New maintained regressions cover extracted runtime strides, branch bindings, captured-range small-loop bypass, unary integer/boolean zero signs, module/literal floating status, erf/erfc backend gates and opt-in compiler deadlines. Run `python -B Test/Benchmark_Dynamic_Strides.py` and `python -B Test/Benchmark_Erf.py` for the corresponding raw-candidate measurements. The complete Windows suites qualify these additions; Linux ARM64 under WSL is now being tested from a separate hash-verified snapshot. Linux AMD64 and the wider roadmap remain open. Historical reports below retain their original build identities.

From the project root on Windows, build the engine and run the tests.

```powershell
python -B Compile.py
.\Test\Run.ps1
```

On Linux AMD64 or ARM64, run `python3 -B Compile.py` followed by `python3 -B Test/Run.py`. The build writes the complete compiled library to `Build/Lib/PyCeler`; checkout imports use that package rather than an in-place engine binary. Install Cython, setuptools and NumPy in the test interpreter and provide the platform compiler and OpenMP runtime. The suite builds and imports real native modules in disposable directories under `Test_Run/`.

Use `python -B Test/Run.py --no-wheels` or `.\Test\Run.ps1 --no-wheels` when wheel creation is deferred. The report names the two excluded wheel-producing tests. All other tests, including the compiler ABI-tag check, remain enabled.

## Disposable Docker testing

Run the maintained Docker launcher from the project root on Windows or Linux:

```powershell
python -B Test/Run_Docker.py --no-wheels
python -B Test/Run_Docker.py --architecture all --python all --no-wheels
```

The default is Linux AMD64 with Python 3.14. The second command runs AMD64 and ARM64 with Python 3.11 and 3.14 sequentially. Omit `--no-wheels` to include wheel-producing tests. `--timeout 7200` increases the per-container build/test deadline from one hour to two hours. ARM64 on an AMD64 host requires Docker emulation and does not qualify native ARM64 performance or replace native CI.

Keep `cython_linux_amd:latest` and `cython_linux_arm:latest` for the existing Python 3.14 toolchains, and the `python:3.11-trixie` platform variants for AMD64 and ARM64. The custom Cython images must already exist. The full Python 3.11 image supplies the compiler toolchain; Python dependencies are installed from `requirements.txt` plus NumPy inside each disposable container. Network access is required for dependency installation and any missing official image. `python:3.11-slim-trixie` is not used by this launcher. No database, browser, PHP or Singularity service is required for PyCeler.

Each run stages a separate source copy and keeps its logs, native build and test reports under `Test_Run/Docker/Run_<id>/`. The original checkout and its Windows build are unchanged. Console logs sit directly in that directory; suite reports are under each platform/interpreter workspace's `Test_Run/`. Containers use `--rm`, unique `pyceler-test-*` names and the label `org.pyceler.test=true`. A `finally` cleanup also removes the specific owned container after failure, timeout or Ctrl+C. A daemon outage or forcibly terminated launcher can prevent that fallback; cleanup errors are reported and labelled containers can be inspected with `docker ps -a --filter label=org.pyceler.test=true`. The launcher never prunes images, volumes or other projects' containers.

`Test_Docker_Lifecycle.py` is discovered by the existing runner and uses mocks to cover disposable arguments and cleanup after success, failure, timeout and interruption. It starts no Docker containers.

## Coverage, module loops and math

The broader analysis and numeric paths have these focused checks:

```powershell
python -B -m unittest Test.Test_Common_Analysis Test.Test_Coverage_References Test.Test_Scalar_Control Test.Test_Module_Scalar Test.Test_Math_Registry Test.Test_Math_Maps Test.Test_Fast_Math -v
```

`Coverage_Loops.py` supplies independent for/while, nested, enumerate/zip, comprehension, generator/async, callback, method, array and simulated transport cases. `Test_Common_Analysis.py` checks immutable/versioned plans, deterministic serialization, name-independent shape keys, dependencies, live values, conservative annotations and math-call effects. `Test_Coverage_References.py` verifies the reference results and event traces. Record a read-only coverage snapshot with:

```powershell
python -B Test/Inventory_Coverage.py
python -B Test/Inventory_Coverage.py --input Test/Module_Nested_Loops.py --input Test/Fast_Math_Loops.py
```

The inventory writes input copies, SHA256 hashes, findings and capability rows to `Test_Run/Coverage_*/Coverage.json`. Static candidate status and actual native execution are separate fields. Additional `--input` files or directories can include Python and Cython sources; analysis does not import them. The historical external Xenonix checkout is not required for these maintained tests.

`Test_Scalar_Control.py` exercises checked powers, bitwise operators/shifts, dynamic whole-function range strides, tuple assignment, conditional expressions, loop `else` and early returns. `Test_Module_Scalar.py`, `Module_Scalar_Loops.py` and `Module_Nested_Loops.py` compare fresh source/native imports, callback mutations, range snapshots, big integers, partial exceptions, nested module control flow, main guards, ordered float bits and actual OpenMP teams. Module and extracted-function `for...else` tests check normal completion, empty ranges and exception ordering. A numeric loop may be extracted from inside a Python exception handler or outer loop while that surrounding control flow stays in Python. Unknown inner control flow and function-local reporting values remain explicit boundaries.

The math registry has separate records for recognition, runtime binding, ordered library-call loops and guarded unboxed evaluation. `Math_Map_Corpus.py` generates recipes for the available registered `math`, `cmath`, NumPy and numeric built-in callables. `Test_Math_Maps.py` checks compiled ordered loops with original library calls, aliases, constants, warnings, complex values, exceptions and mutations. This path retains the GIL and library algorithms. `Test_Fast_Math.py` and `Fast_Math_Probe.py` separately check the 24 implemented unary real-math functions, compositions, exact float64 bytes, binding changes, observers, domain failures, worker rounding/flush modes, actual teams and cache/selection behavior. A native-entry event alone does not imply that a library call was replaced by unboxed arithmetic; the fast-path counters report native and parallel element counts. Current platform/interpreter qualification is recorded in `Session.md` and the matching run reports.

Ordered math and module execution call a cached CPython function every 1,024 iterations, allowing the interpreter to service pending thread handoff requests. This function executes ordinary Python bytecode while the caller holds the GIL; it avoids repeatedly releasing and immediately reacquiring the lock before a waiting thread requests a handoff. Module bulk spans retain their existing checkpoint behavior. The math corpus regression runs three fresh probe processes against one compiled binary. Each real competing worker waits for committed progress before replacing a math binding or raising SIGINT; the probe requires a nonempty original prefix, the expected replacement or untouched suffix, and no unboxed execution while these observers are active. The shared helper also has a compiled private-prefix collision regression that verifies it is an actual Python function.

For repeated qualification, run `python -B Test/Verify_Math_Observers.py --repeats 30` separately under each interpreter being qualified, using its configured PyCeler package. This retains the source, recipes, compiled corpus, hashes and per-process results under `Test_Run/Math_Observers_*/`. Reuse an unchanged corpus without rebuilding with `python -B Test/Verify_Math_Observers.py --reuse Test_Run/Math_Observers_<id> --repeats 30`; each run writes a new verification directory. The retained corpus records its build interpreter, and cross-interpreter reuse additionally requires compatible dependencies and availability of every recorded library function.

The earlier acd44d98 interpreter checkpoint passed all 30 fresh-process observer probes on each Windows interpreter: `Test_Run/Math_Observers_npyvrj3c/Verification__efk434p/Results.json` for 3.14 and `Test_Run/Math_Observers_yvxajmty/Verification_ema706qe/Results.json` for 3.11. Earlier fixed-timer races and genuine ordered-loop GIL starvation remain preserved in failed reports. The final probes require committed progress before acting and reject empty prefixes; an OS yield alone did not fix the observed 3.11 starvation. Both complete suites below include the checkpoint/private-prefix regression and progress-aware mutation/cancellation cases.

The unboxed path evaluates each element once into bounded scratch storage before committing a valid block. Maintained probes check allocation-failure fallback, invalid-block discard and ordered continuation, full worker floating-point environment restoration, caller-visible standard IEEE exception flags and uneven work partitions when a requested 32-worker team is reduced to eight. The historical focused scratch-buffer run on build `8d2567701f1a7e53737a78cfbc0458f32398d3fe1677854f9c4005d5453fd304` passed all five FastMath tests, including 156 serial and 170 parallel exact comparisons. That report qualifies its earlier build; current integrated interpreter qualification is recorded below, and other-platform qualification remains open.

To benchmark an existing module script without changing its bytes:

```powershell
python -B Test/Benchmark_Module_Scalar.py --input path/to/Benchmark.py --samples 3 --threads 2
```

This runner snapshots the input, builds serial and OpenMP variants before timing, then runs each variant in fresh processes. It compares final values and every progress result while excluding clock text, verifies native/parallel counters and the requested team, and records complete import times, build cost, binary paths, source hashes and raw output under `Test_Run/Module_Benchmark_*/`. The original script still runs as Python when launched directly.

The earlier acd44d98 installed-package run of the unchanged 100-million-iteration `Downloads/Benchmark.py` passed three interleaved complete imports per candidate on build `acd44d98...`: `Test_Run/Installed_Fairness_Verification/Results.json`. Default measured conversion selected serial work, with median 0.2640124 seconds, 1,530 native spans and one tiny fallback. A separate candidate generated with `Select=False, OpenMP=True` and executed with two workers had median 0.1257394 seconds, 1,531 parallel spans, actual team two and zero fallback. All six samples preserved exact globals, the final result 49999504352964 and every progress total. The delivered `Parallel_Two` candidate was selected by this 2.10x complete-call gain over default; raw candidate generation itself remains explicitly unmeasured. Finalization replaced `Downloads/Benchmark.pyx` with the verified generated source and preserved the original `.py` bytes. This qualification is specific to the recorded source, build and host.

For representative unboxed math workloads, run `python -B Test/Benchmark_Math.py --sizes 64 4096 262144 --samples 9 --threads 2`. It validates exact bytes and output identity, proves the native/parallel element counts for every call, warms up each candidate and interleaves full-call timings. Reports include medians, minima, variation and comparisons against Python and serial execution. Run either benchmark alone, without concurrent builds or tests.

The earlier acd44d98 scratch-buffer benchmark is `Test_Run/Math_Benchmark_qlmliwn2/Results.json`, using build `acd44d98f702c728a84f2ad1dc9d35d97ecca6d53840fdb56cfdfed3a4c64210` on AMD64 CPython 3.14.8 on the recorded Windows ARM64 host. Nine samples per variant at 262,144 elements produced these complete-call medians:

| Workload | Python | Serial | OpenMP, two workers | Serial/OpenMP gain over Python |
| --- | ---: | ---: | ---: | ---: |
| `sin` | 197.9733 ms | 94.0325 ms | 51.5145 ms | 2.11x / 3.84x |
| Composed expression | 804.8911 ms | 544.8963 ms | 281.4901 ms | 1.48x / 2.86x |
| `expm1` | 139.8810 ms | 54.4598 ms | 33.2214 ms | 2.57x / 4.21x |

Every timed native call checked exact bytes and native element counts; OpenMP calls observed actual team two. The 64-element cases favored Python. These raw candidate timings include guards, scratch evaluation, commits and checkpoints, exclude compilation, and do not claim measured-selection dispatch for those workloads. `Test_Run/Math_Benchmark_f8d_vmai/Results.json` remains historical evidence for build `8d256770...`, whose corresponding serial/two-worker gains were 2.08x/3.90x, 1.49x/2.90x and 2.60x/4.76x. Its timings do not qualify later binaries.

## Where to find results

Scalar arithmetic, extracted progress loops, diagnostics and workload sizing have focused regression coverage:

```powershell
python -B Compile.py
python -B -m unittest Test.Test_Scalar_Arithmetic Test.Test_Scalar_Regions Test.Test_Diagnostics Test.Test_Scalar_Sizing -v
```

The scalar tests compare exact values, types, float bit patterns, integer boundaries, negative remainders and division errors. Region tests exercise module and function scopes, implicit `None`, progress ordering, frozen clocks, empty loops, callback mutations, overflow continuation, shadowed builtins, object identity and partial module globals on exceptions. Selection must validate isolated numeric spans without executing module setup or progress callbacks.

The extended scalar/OpenMP and cache checks are:

```powershell
python -B -m unittest Test.Test_Parallel_Reductions Test.Test_Scalar_Strides Test.Test_Structural Test.Test_Optimization_Selection -v
```

`Test_Parallel_Reductions.py` verifies real two-worker execution, exact signed modulo/floor results, every-expression and partial-sum overflow guards, zero divisors, empty loops, bigint fallback, background-thread serial execution, and tuned candidate validation. `Scalar_Parallel_Proof_Probe.py` independently enumerates randomized interval expressions and 1,500 complete reduction proofs, including shuffled accumulation order. Its private proof wrappers exist only in the generated test extension.

`Test_Scalar_Strides.py` compares 5,670 signed start/stop/step/period combinations with a separate iteration oracle, then checks native function/module spans, callback mutations, break/continue, exceptions and range shadowing. Descending selection probes must use iteration counts and reachable callback intervals.

`python -B Test/Benchmark_Parallel_Reductions.py` builds Python-reference, serial and OpenMP variants before timing. It validates exact results, uses two warmups and seven interleaved complete-call samples by default, records proof-based serial entry and real two-worker entry, compares OpenMP with the same optimized serial arithmetic, and checks the final measured extension against each recorded dispatch decision. Results are saved to `Test_Run/Parallel_Reductions_*/Results.json`. Use `--iterations 100000 --samples 3` for a smaller run. Run benchmarks sequentially without concurrent native builds or tests.

`python -B Test/Benchmark_Scalar_Regions.py` builds and measures the three reported arithmetic variants (`%`, `/`, `*`) at 100 million iterations in module and function scope. It verifies final results and all progress totals against Python and writes complete outputs, elapsed times and ratios under `Test_Run/Scalar_Benchmark_*/Results.json`. Use `--iterations 1000000` for a smaller smoke benchmark. Run timing commands sequentially without concurrent builds or tests; the oversized multiplication case can legitimately retain Python bigint execution.

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

`Test_Package_Build.py`, `Test_Environment_Checker.py`, and `Test_Source_Bootstrap.py` cover the compiled-only distribution layout, resource embedding, interpreter-target checks, diagnostics and checkout import routing. Package publication tests import the builder from root `Compile.py` and use a mocked backend. `Test_Distribution.py` copies the built native modules and initializer into an isolated directory, then runs Analyze, Convert and measured Compile without helper sources or templates. The maintained `.github/workflows/Native_Regression.yml` covers native Windows x64, Linux AMD64 and Linux ARM64 on CPython 3.11 and 3.14, including the same stable-ABI artifact on the other interpreter. These jobs require an actual CI run; local Windows checks do not establish their results.

Historical verification on 2026-11-10 passed **all 144 tests then enabled by `--no-wheels` in 613.262 seconds**, with no failures or skips; that suite had 146 tests including its two excluded packaging cases. It used AMD64 CPython 3.14.8, Windows 11 build 26100, Cython 3.3.0 and MSVC. Results were recorded in `Test_Run/Run_1apdn_7d/Results.txt` and `Test_Run/Verification_020/Integrity.json`. The broader coverage/module/math tests described above were added later. Use the current runner report and latest `Session.md` handoff for the actual test count, loaded build identity and verification status of the current checkout. Historical results do not qualify later source changes.

The historical 2026-11-11 Windows suites passed **all 223 tests including wheel tests**, with no failures or skips, on the recorded ARM64 Windows host running AMD64 binaries:

- CPython 3.14.8: 725.983 seconds, `Test_Run/Run_3v69jwwo/Results.txt`, build `acd44d98f702c728a84f2ad1dc9d35d97ecca6d53840fdb56cfdfed3a4c64210`.
- Isolated CPython 3.11.9: 696.306 seconds, `Test_Run/Run_0syg_rtg/Results.txt`, build `2c464f2f8ba04e5a3ede9981d8a38fca670b15feee76328ba0eaad30294f08d9`.

`Test_Run/ABI311/Qualification_Interpreter/Summary.json` records verified package artifact hashes, the preserved 3.11 snapshot and identical maintained package sources across these two builds; dependency versions are recorded separately. The 3.11 manifest is `Test_Run/ABI311/Qualification_Interpreter/Lib/PyCeler.manifest.json`. These are separately built interpreter qualifications.

The exact current delivery wheel also passed isolated public Analyze/Convert/Compile/OpenMP probes on 3.14 and 3.11, both with actual team two. Reports are `Test_Run/Interpreter_Wheel_314/Installed_Wheel.json` and `Test_Run/Interpreter_Wheel_311/Installed_Wheel.json`; both identify build `acd44d98...` and wheel SHA256 `aea98c4db6bac1f7344dc58226e47d80aed0512dbb8f5021f2954cabb752ae69`. All eight same-artifact 3.11 observation/checkpoint/math-selection checks passed in 27.570 seconds, recorded in `Test_Run/Interpreter_Wheel_311/Observation.json` and `Test_Run/Interpreter_Wheel_311_Observation.log`. The main 3.14 installation passed all 20 manifest artifact hashes; `Test_Run/Installed_Fairness_Verification/Installation.json` and `Test_Run/Interpreter_Installation_Verification.log` record its exact package path, build and source fingerprint. The fresh installed module benchmark also passed, as recorded above. These same-artifact checks supplement the complete interpreter suites; Windows execution does not qualify unexecuted Linux or physical-host configurations.

Historical 216-test runs remain at `Test_Run/Run_xl91t49w/Results.txt` (3.14, 628.412 seconds) and `Test_Run/Run_zgjefz_j/Results.txt` (3.11, 718.648 seconds), with the older 3.11 summary in `Test_Run/ABI311/Qualification/Summary.json`. An earlier signal-test timer fired after module completion; its report remains preserved. The progress-aware probe retains all mutation/cancellation assertions and deliberately delays preparation. Later ordered-math observer failures led to the interpreter-checkpoint fix and the historical 223-test and 30-probe qualifications, rather than being treated as passing historical evidence.

The earlier acd44d98 static coverage refresh in `Test_Run/Coverage_Baseline_np9d7gpp/Coverage.json` and `Summary.json` snapshots 115 maintained Test sources and reports 889 findings. An independent AST count accounts for all 880 Python loop forms, with nine Cython findings handled separately and no source-byte changes. The hash-verified isolated analyzer is build `acd44d98f702c728a84f2ad1dc9d35d97ecca6d53840fdb56cfdfed3a4c64210`. Static rows explicitly mark native execution as unobserved; actual entry evidence comes from differential/native tests and benchmarks. The earlier 113-source, 871-finding, 862-form snapshot remains preserved under `Test_Run/Coverage_Baseline_xj0t94tk/`.

The final fair reduction benchmark used two warmups and seven interleaved complete-call samples. At two million iterations, modulo medians were 767.4053 ms Python, 13.6751 ms proof-based serial and 7.6757 ms two-worker OpenMP: 1.78x over serial. Exact results, real teams and all seven selected dispatch decisions were checked. These are host-specific measurements, with compilation excluded.

For a source-only check, run `python -B Test/Check_Syntax.py`. It parses maintained Python files and translates every distribution module into disposable C sources under `Test_Run/Cython_Review_*/`, including embedded runtime resources. It does not invoke a native compiler, load the generated engine, run behavioral tests or benchmark code. `Results.json` records the platform, versions and translation diagnostics.

## Audit regression coverage

`Test_Observable_Semantics.py` reproduces modulo/input/loop-index identity, exact unsupported-function exceptions, returning signal handlers that mutate module globals, and cancellation with visible partial state. Eligible module arithmetic can run natively with observable-state continuation; unsupported operations and failed guards preserve Python execution.

`Test_Generated_Scalar_Programs.py` generates 54 programs from arithmetic, ordered-loop, identity and callback forms, then compares 10,422 cases per serial/OpenMP binary. This complements fixed-fixture input randomization. `Test_Selection_Safety.py` checks nested identity graphs, cycles, view backing storage, byte limits, budget ordering and live OpenMP setting changes. Cases include inconclusive outcomes instead of silently promoting timed-out workloads.

`Test_Build_Identity.py` rejects stale sources/dependencies, missing or modified artifacts and invalid inventories. `Test_Wheel.py` verifies deterministic wheel metadata/RECORD and exercises a pip-installed wheel in isolation, including actual OpenMP execution. `Test/Run.py` verifies freshness before discovery and records engine path, build ID and source fingerprint.

Run `python -B Compile.py wheel --library Build/Lib` to package the verified local build and `python -B Test/Verify_Wheel.py WHEEL_PATH` to preserve an installed-wheel smoke report. Run package builds and native tests sequentially on Windows to avoid loaded-library locks.

## Optimizer follow-up checks

`Test_Structural.py` runs `Randomized_Probe.py` for both serial and OpenMP builds: 960 deterministic cases each, covering eight dtypes and ten structural families, including augmented local/indexed arithmetic and multiple independent updates. Comparisons include result types, bytes, signed zero, warnings, exceptions, mutations, overlapping views, strides, read-only arrays, shape errors and nonnative byte order. Eligible integral-valued float maps must actually enter the native kernel. Failed cases save their seed, case index and a replay command under `Test_Run/Randomized_Failures/`. An untransformed uninitialized-local case requires the exact CPython exception type, message and unchanged state. Converted Python source runs through CPython glue; direct native Cython inputs retain their separate semantics.

Selection-cache tests require corrupted entries to be repaired, valid entries to remain reusable, failed publication to restore the prior entry and entries outside the cache root to be rejected.

`Test_Native_Optimization.py` compares unchanged and optimized typed Cython fills, checks special float values and invalid arguments, rejects unsafe source context, and compiles standalone `.pxi` input. A deliberately unattainable speed threshold must preserve the original source exactly. `Test_Numeric_Extensions.py` uses independent partition-based median and scalar channel-distance oracles, including empty/thin arrays and borders, and requires native entry for eligible cases. Temporary-list elision remains explicit.

`Test_Binary_Cache.py` verifies repeated builds without a compiler worker, include and external compiler-header invalidation, per-module rebuilds, artifact corruption repair, flag changes and grouped loaders. Run `python -B Test/Benchmark_Binary_Cache.py` for cold-versus-cached wall times on a 500-function module (about 1,500 lines); all functions execute correctly after each build and cached binary bytes must match.

`Test_Tuning.py` builds serial, two tile sizes and two OpenMP team configurations for a real filter. It checks validation evidence, profiling summaries, independent output values and unchanged caller thread settings, including rejected-candidate fallback. Additional native builds cover tuned fills, element-wise maps, structural maps and medians. For a focused run, use:

```powershell
python -B -m unittest Test.Test_Structural Test.Test_Native_Optimization Test.Test_Numeric_Extensions Test.Test_Binary_Cache Test.Test_Tuning -v
```

## Prepared Linux checks

Linux execution requires a native AMD64 or ARM64 host. `.github/workflows/Native_Regression.yml` builds the package, runs the complete suite and installed-wheel pipeline, and imports the same stable-ABI fixture on both Python versions. The presence of the workflow is not a successful platform qualification. The following commands remain available for manual execution on each native Linux host:

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

`Test_Selection_Observation.py` checks that selection observations use fresh dispatch events or counter changes, never stale statistics from an unrelated kernel. For module calls containing both native and fallback spans, `Native_Entry` and `Python_Fallback` each record whether that behavior occurred anywhere in the call. `Actual_Mode` records the final dispatch event, while `Actual_Team` records the last native span's observed team when native work occurred. Thus a call ending in fallback can correctly report `Native_Entry: true`, `Python_Fallback: true`, `Actual_Mode: "python_fallback"` and a nonzero `Actual_Team`. Its measured module regression requires valid serial and OpenMP candidates to report their actual native teams without requiring a particular timing winner.

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

A local isolated Windows CPython 3.11.9 runtime was prepared under `Test_Run/ABI311/python.3.11.9/tools/python.exe` for this qualification work, with Cython 3.3.0, setuptools 84.2.1 and NumPy 2.4.6. `Test_Run/ABI311/Runtime.json` records its source, package hash and verified Python Software Foundation executable signature. The 3.11 smoke reports in `Test_Run/ABI311/Smoke/` verify the recorded 3.14-built package snapshot, native scalar/array calls, exact math output and actual team-two module/math execution. They are smoke checks rather than a complete 3.11 regression run, and their build ID must be compared with the current package before reuse.

The later full 3.11 qualification uses its own dependency-matched package under `Test_Run/ABI311/Qualification/Lib`, selected through `PYCELER_LIBRARY_DIR`; it leaves the normal `Build/Lib` package unchanged. The clean suite report and source/artifact comparison are recorded above. This is a full regression run of the 3.11-built package; importing a delivered 3.14-built wheel on 3.11 remains a distinct stable-ABI check.

That distinct delivered-wheel check also passed on both interpreters: `Test_Run/Delivered_Wheel_314/Installed_Wheel.json` and `Test_Run/Delivered_Wheel_311/Installed_Wheel.json` record isolated public `Analyze`, `Convert`, `Compile` and actual OpenMP execution using the delivered artifact. These installed-wheel probes supplement the two full suites; they do not constitute a full suite against the same wheel on both interpreters.

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
