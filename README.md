# PyCeler

This checkout contains **PyCeler 0.5.0**. Build from source to use this checkout, or install a published release with pip.

Version 0.5.0 expands guarded native execution for numeric lists and arrays, iterator loops, pure helper calls, and indexed distance filters. Conversion produces one readable Cython file and preserves Python scope and fallback behavior across supported transformations. Eligible loops get serial Cython and OpenMP candidates, with behavior checks and whole-call measurements guiding selection. See [the changelog](Log.md) for coverage and measured results.

Browse the [Example catalogue](Example/README.md) for ordinary Python inputs, including preserved full benchmarks and broad math fixtures. Bulk example folders contain only `.py` files; generate readable Cython on demand under ignored `Test_Run/Examples`. Start with the small `Example/Quick_Start.py` and its retained `.pyx`; no PyCeler-specific syntax is required.

PyCeler looks for numeric loops in Python code and tries compiling them with Cython. A loop that clears an array, for example, can split the work across threads because each write is independent. An array prefix sum reads a preceding write and must keep that order. PyCeler checks which transformations apply, compares their results with Python, and measures whether they save time on the inputs it tried.

## Installation

Install a published release in your Python environment with pip:

```sh
pip install PyCeler
```

The pip command installs the published release. PyCeler targets standard CPython 3.11 and newer on Windows x64, Linux x86-64, and Linux ARM64. Build each native distribution on its target host. Linux portability qualification is tracked in the development plan.

You can analyze Python files with the installed package. To generate and benchmark native candidates or compile your own extensions, you’ll also need a C compiler. On Windows, use MSVC Build Tools with the C++ toolchain and Windows SDK. On Linux, use GCC, Python development headers, and the OpenMP runtime.

Install the third-party libraries your code uses in the same environment before optimizing it. Static analysis reads the source without importing it. Validation and timing can execute the code. NumPy is optional for PyCeler itself and is used for array optimizations.

## Try it on a Python file

Point the analyzer at an existing file. Each finding tells you where the loop is and why PyCeler considers it a candidate or skips it.

```python
import PyCeler

source = "my_loops.py"
for loop in PyCeler.Analyze(source):
    print(loop.Function, loop.Line, loop.Reason)
```

To see the generated Cython, call `PyCeler.Convert(source, "output/cython")`. To build an importable extension directly, call `PyCeler.Compile(source, "output/native")`. Both take a file or source directory and write their output separately from your originals. If you already have Cython code, use `PyCeler.Compile("existing.pyx", "output/native", Convert=False)` to compile it directly.

For eligible loops, the selection report shows how Python, serial Cython, and OpenMP performed at different input sizes. A small array can take longer to split across threads than to process on one. At runtime the module uses the implementation selected for the input and falls back to Python when the input falls outside the conditions it checked.

## Optimization coverage

PyCeler does not promise to accelerate every Python loop. Arbitrary objects, unknown calls, dependent writes and unsupported control flow keep Python execution. Successful compilation alone does not mean that every loop was transformed. OpenMP is considered automatically during default measured selection; `OpenMP=True` explicitly enables it and `OpenMP=False` excludes it.

| Supported family | Candidates and transformations |
| --- | --- |
| Independent array fills and maps | Typed native loops, proven bounds-check removal, eligible `prange` with `nogil` |
| Multiple statements and augmented array assignments | Initialized local arithmetic, per-index `+=`, `-=`, `*=`, guarded independent writes |
| Extracted ndarray regions | Arbitrary statically known rank, tuple indexing and row unpacking, float32/float64 arithmetic, primitive output casts, ordered sums and independent outer `prange` workers |
| Rectangular standard random generation | Ordered `random.random` staging, exact RNG state, guarded native scalar math and independent parallel output writes |
| Nested numeric Python lists | Arbitrary statically known rank, guarded float or bounded integer/boolean cells, stepped ranges, carries and proven-independent OpenMP work with ordered publication |
| Numeric `enumerate` and `zip` loops | Guarded scalar-target indexing over named lists/arrays, optional enumerate starts, strict mismatch fallback, original iterator construction and final target identities |
| Indexed distance filters | Guarded serial squared-distance comparisons over fixed float64 columns, with candidate order, duplicates and threshold ties preserved |
| Array extrema and clamped indices | Ordered multi-argument min/max with selected-operand dtype, clamped native indexing, checked Python-integer floor division and sequential reduction loops |
| Stable integer index offsets | Shared dependency proofs for parameterized offsets in range and iterator loops, with checked wrapped-address bounds |
| Shape-only inputs | Guarded lengths and dimensions without converting or copying unused element data, including object-filled templates |
| Pure numeric helpers | Same-module fixed-signature calls with ordered local assignments, nested helper calls, reused values and preserved unused computations |
| Structural array loops | Common-expression reuse, invariant motion, adjacent-loop fusion, row-major interchange |
| Stencils and clipped medians | Guarded borders, tiled serial filters, row-local scratch, eligible parallel rows |
| Counts, projections and row selection | Specialized guarded kernels and eligible OpenMP reductions/rows |
| Integer scalar sums | Matching proof-based serial and OpenMP arithmetic when every expression and partial sum fits int64 |
| General supported scalar control flow | Checked arithmetic, dynamic range strides, nested ranges/while loops, loop `else`, early returns and preserved break/continue order |
| Numeric spans with periodic callbacks | Function and module extraction, positive/negative literal strides, ordered callback boundaries |
| Module numeric loops | Bounded serial spans, eligible exact OpenMP sums, observable-global continuation and original surrounding Python control flow |
| Broad math, complex math and NumPy calls | Compiled ordered loops retaining the original library operations, Python objects, warnings and exceptions |
| Supported real-math array expressions | Guarded unboxed float64 arithmetic, eligible `prange`, runtime-gated `erf`/`erfc`, and two-argument `copysign`/nonzero-result `fmod`; qualification is recorded per build in the test evidence |
| Byte spans and fragmented reads | Serial specializations preserving stream order and exceptions |
| Existing typed Cython | Conservative contiguous-fill bounds/wraparound elimination |

Native eligibility is separate from valid Python input. Rank handling is generated for the detected indexing structure, while runtime checks validate actual shapes, bounds, dtypes and overlapping storage. The extracted ndarray path currently lowers float32/float64 reads; complex, half and integer arithmetic need another supported specialization or Python fallback. Exact-integer and allocation safeguards remain. Floating reductions keep their original order rather than using a reassociated parallel sum. See [the test guide](Test/README.md) for executable coverage and qualification limits.

Supported maps can now carry multiple storage implementations: numeric lists, composed float32/float64 ndarray regions and the existing typed ndarray map. Backend routing uses runtime storage checks and separate measured list/dtype bands. Recognizing a loop with an earlier planner no longer prevents these compatible implementations from being generated. This does not remove arithmetic, alias or binding checks, and small calls can still favor Python after whole-call measurement.

Direct iterator candidates use a complete transaction and retain the original iterator for fallback. Current direct lowering covers scalar targets over named rank-one sources; numeric work inside tuple-bound row loops can be extracted separately. Helper defaults, keyword-only signatures, general statement bodies and borrowed return identities remain outside the current pure-helper contract. Shape-only support does not imply arithmetic support for the template's element dtype.

Enable bounded thread/tile tuning and cache reuse when compiling:

```python
binary = PyCeler.Compile(
    "my_loops.py", "output/native",
    OpenMP=True, Tuning=True, Cache=True,
)
```

Selection validates candidates, measures complete calls repeatedly and retains the simpler candidate when a gain is uncertain. Representative `Workloads` and holdouts improve decisions for real inputs. `Elide_Temporaries=True` separately permits supported temporary-allocation elimination; it is explicit because removing an allocation also removes its potential allocation failure. Compiler settings preserve floating-point ordering and do not enable unsafe fast-math. OpenMP execution requires independent writes or an exact reduction proof; changing every `range` to `prange` would break that contract.

Synthetic selection, including `Tuning=True` alone, extrapolates the largest validated band to larger sizes subject to the same correctness guards. Reports label this as extrapolation, not a measured performance gain. Representative `Workloads` use bounded dispatch: calls above the largest supplied size use Python. Supply production sizes and holdouts, then inspect `Coverage` and `Dispatch`. The largest default synthetic probes are 32,768 scalar iterations, 65,536 array elements and 4,096 stencil/median pixels.

Validation checks nested object identities, shared array backing storage, mutations, exception arguments and warnings. Holdouts and production cases run before synthetic cases. Each isolated worker has a hard time limit covering imports, factories, isolation, validation and timing, plus a five-second termination allowance; compilation is separate. Copied backing storage is limited to 64 MiB per timing batch, including a small view's full owner allocation. Arbitrary workload factories execute in that worker and can allocate their own storage. Inconclusive cases stay on Python. Live OpenMP settings are checked before measured dispatch. Validation reports record each actual native entry and worker team separately from the requested candidate. For application diagnosis, generated modules expose a private `_Pyceler_Dispatch_Stats(True, Reset=True)` hook; call it before an invocation and inspect `Selection` and `Execution` afterwards, then disable it with `_Pyceler_Dispatch_Stats(False)`. Generated prefixes can change on name collisions. Reset before each observed call; unsupported functions have no native-entry event. Instrumentation is off during normal timing and adds no per-iteration checks when disabled.

`Execution` describes the most recent execution event. For a call that completes native spans and then falls back, inspect `Totals.Native_Entries`, `Totals.Parallel_Entries` and `Totals.Maximum_Team` as well. These accumulate recorded native events until `Reset=True`; they do not establish a whole-call speedup. A final `python_fallback` event remains visible even when earlier native work succeeded.

## Scalar loops and progress reporting

The source build supports checked integer addition, subtraction, multiplication, modulo, floor division, nonnegative integer powers, bitwise operations and shifts. Supported whole functions can use dynamic nonzero range strides, chained comparisons, conditional expressions, flat tuple/list assignment, loop `else`, and early returns. A bounded floating reduction also supports true division and ordered floating addition, subtraction and multiplication. Integer true division retains Python's rounding behavior, including operands too large to convert exactly to a double. Unsupported types, negative powers and integer overflow keep Python behavior.

Eligible `range` loops with nonzero literal strides up to `2**31 - 1` in magnitude can be extracted from longer functions, including functions returning `None`. A trailing progress condition such as `if i % 10_000_000 == 0 and i != 0:` can remain in place. Pure arithmetic runs in spans ending at the original reporting boundaries; timing calls, printing and callback updates run in their original order. Selection measures isolated numeric spans without executing module setup or reporting callbacks. It limits probe sizes by the number of iterations between reachable reporting boundaries, including descending ranges.

Eligible module-level numeric loops now call native helpers. This includes pure numeric loops inside module conditionals, main guards, exception/finally blocks, context managers and outer loops; the surrounding Python code remains in place. Helpers preserve progress callbacks, final loop targets, partial exception state and global updates. Bounded serial spans and exact OpenMP reductions require the runtime observer checks to pass; custom signal handlers, other Python threads, tracing or profiling use the observable-state path. Global-state functions have additional restrictions on local values in reporting code. Direct modulo assignments and copied results that may alias an existing integer retain Python execution; modulo terms inside a fresh addition can qualify.

Extraction remains conservative around reflection, nested scopes, identity-sensitive assignments and arbitrary calls inside arithmetic. More general callback conditions and dynamic strides inside extracted regions retain the original loop, even though dynamic strides are supported in eligible whole scalar functions. Exception handlers can surround an extracted module loop; handlers inside its arithmetic body remain a boundary. A checked native span can retry its pure arithmetic before committing results, preserving partial updates if Python raises and avoiding duplicate progress calls.

An eligible extracted `for` loop can retain its `else` suite. The original suite runs once after normal completion, including an empty range, and does not run after an exception. Unsupported `break`, `continue` and `return` within an extracted arithmetic body still prevent that extraction.

A whole function that initializes an integer total, adds independent integer terms over one range, and returns that total can receive an OpenMP candidate. Eligible module progress loops can use the same exact reduction proof within bounded spans ending at reporting boundaries. Python integer interval arithmetic proves that every intermediate expression and every possible partial reduction fit int64. The serial reduction candidate uses the same proof and unchecked arithmetic, so OpenMP comparisons isolate the additional threading benefit. Failed proofs preserve Python bigint behavior. Floating sums and nonreduction scalar work remain ordered. Parallel reductions check Python signals between bounded blocks and use serial execution when called from a Python worker thread. Generated modules expose `_Pyceler_Module_Stats()` with native chunk/step counts, parallel chunk counts, actual last team size and fallback counts.

Findings expose immutable `Diagnostics` records with codes, source locations, messages and suggestions. Python findings also have a versioned `Plan` describing control flow, inputs, live values, dependencies, effects, math-call contracts, guards and eligibility. Static plans describe candidates; they do not prove native execution or measured speedup. Selection reports distinguish no candidates, candidate build failures, validation failures and measured selection. Static overflow warnings describe possible ranges rather than claiming that a fallback was observed. Comprehensions, generators and asynchronous loops receive explicit findings and retain Python behavior. Conversion writes a report even when there are no loops. A completed native compilation can still contain unchanged loops.

Converted `.py` inputs produce one readable `.pyx` containing the application definitions and native Cython kernels. Generated application and fallback bodies are emitted as code, not escaped source strings or runtime `exec`/`compile` calls. There is no companion Python file. Python-style definitions in that file are compiled by Cython; they are Cython function objects rather than CPython `FunctionType` objects. Cython function-code replacement, tracing and unsupported Python syntax therefore follow Cython behavior. Native fast paths keep explicit guards and readable fallback code for incompatible runtime inputs. Generated private helper names remain implementation details.

Edit the generated `.pyx` and rebuild with `Compile(path, output, Convert=False)` to compile those edits directly. Edit the original `.py` and run conversion again when changing application logic that should be replanned into optimized kernels. String literals belonging to the application remain ordinary data. The format change does not establish native coverage for every Python operation.

Run the generated extension by importing it from its output directory. Running the original `.py` file continues to execute that source. Module-level statements execute on import; a function inside an `if __name__ == "__main__":` entry point must be called explicitly from a separate runner.

## Math functions

The versioned registry recognizes the standard `math` and `cmath` APIs, numeric built-ins and a broad NumPy inventory, including aliases, optional arguments and interpreter-version differences. Eligible array maps can compile their loop control while continuing to call the original library functions under the GIL. This ordered path preserves arbitrary-precision integers, complex results, dtype conversions, warnings, live bindings and mutation-before-error behavior. Calls such as `fsum`, `hypot`, `gamma`, factorials and NumPy reductions keep their existing algorithms.

A narrower path emits native double arithmetic for 26 unary `math` functions: `sqrt`, `cbrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `exp`, `exp2`, `expm1`, `log`, `log10`, `log1p`, `fabs`, `isfinite`, `isinf`, `isnan`, `erf` and `erfc`. It supports eligible compositions in one-dimensional, contiguous, aligned float64 arrays with disjoint output storage. It validates bindings, finite domains and intermediate values, preserves operation order, and checks the observer and floating-point environment before committing bounded blocks. Other layouts, float32 storage and unproven inputs use the ordered path or Python fallback. `erf` and `erfc` require the runtime CPython 3.12–3.14 backend gate: local native verification covers 3.14, while 3.11 retains ordered calls. `log2` remains ordered.

Each block evaluates its expression once per element into a reusable buffer of at most 4,096 doubles, then commits only a fully valid block. A failed domain, binding or observer check discards that block and resumes ordered original-library execution from the last committed position, preserving mutation prefixes and exceptions. Buffer allocation failure takes the original path without introducing a new allocation exception. Each worker saves its complete floating-point environment, evaluates its assigned span using the caller's environment, then restores its previous state. Standard IEEE exception flags from committed work are reflected on the calling thread. Non-nearest rounding and unproven observer conditions retain the ordered path.

For example, this expression can receive serial and OpenMP candidates on eligible float64 inputs:

```python
import math

def Transform(Source, Output):
    for Index in range(len(Output)):
        Output[Index] = math.sin(Source[Index]) + math.sqrt(Source[Index])
    return Output
```

`OpenMP=True` permits a parallel candidate; it does not parallelize ordered library calls or guarantee selection. Inspect the selection report and actual native-entry/team evidence for the inputs that matter. Broad registry coverage, compiled ordered iteration and unboxed mathematical evaluation are reported separately.

Recorded whole-call benchmarks at 262,144 elements measured these median speedups against Python, including guards and buffer work:

| Workload | Serial | Two-worker OpenMP |
|---|---:|---:|
| `sin` map | 2.11x | 3.86x |
| Composed math expression | 1.49x | 2.91x |
| `expm1` map | 2.71x | 4.99x |

These are nine-sample raw candidate comparisons from build `ba1f96960cd910f2d6d5177dfa8a8ae2e6c7ed9d81bc9dae09a6bf2e15fc8451`, using AMD64 CPython 3.14.8 on the recorded Windows ARM64 host. Every timed native call matched exact output bytes and recorded actual worker entry. The 64-element cases favored Python. The report is `Test_Run/Math_Benchmark_wovm2kpt/Results.json`; these measurements do not establish default dispatch choices or performance on other machines. The separate `Test_Run/Erf_Benchmark_v6b1h7mb/Results.json` records approximately 3.97x/3.96x two-worker gains for large erf/erfc maps.

## Build from source

From the root of the GitHub checkout, install the build dependencies and run the build script:

```sh
python -m pip install -r requirements.txt
python -B Compile.py
```

The built package is in `Build/Lib/PyCeler`. Its manifest records source/dependency fingerprints, artifact hashes and a build ID. Checkout imports and the test runner reject stale or modified binaries and name the rebuild command. The runner records the loaded engine path and build ID.

The earlier 0.2.0 Windows qualification discovered 271 tests on each of CPython 3.14.8 and 3.11.9: 269 passed and two POSIX-only deadline checks were explicitly skipped on each. Both builds have identical maintained package source hashes. Thirty fresh-process math observer probes passed per interpreter, both exact-wheel pipeline probes passed, and 14 additional same-wheel regressions passed on 3.11. These checks used AMD64 Python on an ARM64 Windows host. `Test/README.md` identifies the reports and the read-only inventory accounting for all 1,131 Python loop forms. Those counts apply to that earlier checkpoint.

Extracted scalar regions support signed runtime range strides, preserving the captured range when a body rebinds its step variable. Branch binding proofs allow existing region planners to consume values assigned on both branches. Small supported loops can bypass span dispatch using their complete captured range size. `PYCELER_BUILD_TIMEOUT_SECONDS` enables a per-compiler-worker deadline; unset or zero leaves it unlimited. Deadline failure preserves existing published artifacts and prevents cache publication. It is not an aggregate optimization budget.

Run the regression suite after building the library. The suite includes wheel creation and installed-wheel checks, so use it when packaging verification is intended.

```sh
python -B Test/Run.py
```

To verify the optimizer while deferring wheel creation, run `python -B Test/Run.py --no-wheels`. The report explicitly lists the two excluded packaging tests.

For release packaging after verification, use the following commands. The example filename is for the Windows x64 build of 0.5.0. Running the verification command is separate from building the wheel.

```sh
python -B Compile.py wheel --library Build/Lib
python -B Test/Verify_Wheel.py Build/Wheels/pyceler-0.5.0-cp311-abi3-win_amd64.whl
```

Use the wheel filename produced on your native host; Linux wheels use `linux_x86_64` or `linux_aarch64` tags. Wheel packaging is deterministic for identical built files. It does not claim manylinux qualification or identical native binaries across compiler runs. The maintained CI matrix builds and tests native Windows x64/Linux AMD64/Linux ARM64 on CPython 3.11 and 3.14, then verifies the same artifact on the other interpreter. Local verification does not imply those remote jobs have run. These source changes do not update an already published wheel.

To try the analyzer from the checkout, run:

```sh
python -B Compile.py analyze --input Test/Numeric_Loops.py --rank
```

The example contains both the array fill and the running sum. [Example source](https://github.com/nucleonautomation/PyCeler/blob/main/Test/Numeric_Loops.py)

## Project

[GitHub repository](https://github.com/nucleonautomation/PyCeler) · [Changelog](https://github.com/nucleonautomation/PyCeler/blob/main/Log.md) · [Test guide](https://github.com/nucleonautomation/PyCeler/blob/main/Test/README.md) · [MIT license](https://github.com/nucleonautomation/PyCeler/blob/main/LICENSE.md)

## Reading the implementation

Start with `PyCeler/Engine.pyx` and `Generator.pxi` for the public analysis/conversion flow. `Common_Analysis.py`, `Common_Scopes.py` and `Common_Calls.py` supply shared facts; the scalar, numeric and array planners turn those facts into guarded plans. Their emitters and `.pxi.in` runtime templates implement native work and continuation. `Direct_Source.py` assembles readable output, `Selection_Worker.py` validates before timing, and `Native_Build.py` stages native compilation. Comments explain why guards and ordering constraints are required.

In `Test/`, workload fixtures describe source patterns, probes compare Python/native behavior and inspect actual worker counters, and `Test_*.py` files orchestrate isolated checks. `Example/` presents the corresponding inputs/output pairs for readers without mixing them with test drivers or temporary binaries.
