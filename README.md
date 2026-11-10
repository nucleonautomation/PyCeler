# PyCeler

This checkout contains **PyCeler 0.2.0**, currently unreleased. Build from source to use the changes described here.

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
| Structural array loops | Common-expression reuse, invariant motion, adjacent-loop fusion, row-major interchange |
| Stencils and clipped medians | Guarded borders, tiled serial filters, row-local scratch, eligible parallel rows |
| Counts, projections and row selection | Specialized guarded kernels and eligible OpenMP reductions/rows |
| Integer scalar sums | Matching proof-based serial and OpenMP arithmetic when every expression and partial sum fits int64 |
| General supported scalar control flow | Checked serial arithmetic, nested ranges and while loops, preserved break/continue order |
| Numeric spans with periodic callbacks | Function-local extraction, positive/negative literal strides, ordered callback boundaries |
| Byte spans and fragmented reads | Serial specializations preserving stream order and exceptions |
| Existing typed Cython | Conservative contiguous-fill bounds/wraparound elimination |

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

## Scalar loops and progress reporting

The source build supports checked integer addition, subtraction, multiplication, modulo and floor division. A bounded floating reduction also supports true division and ordered floating addition, subtraction and multiplication. Integer true division retains Python's rounding behavior, including operands too large to convert exactly to a double. Unsupported types and integer overflow keep Python's arbitrary-precision behavior.

Eligible `range` loops with nonzero literal strides up to `2**31 - 1` in magnitude can be extracted from longer functions, including functions returning `None`. A trailing progress condition such as `if i % 10_000_000 == 0 and i != 0:` can remain in place. Pure arithmetic runs in spans ending at the original reporting boundaries; timing calls, printing and callback updates run in their original order. Selection measures isolated numeric spans without executing module setup or reporting callbacks. It limits probe sizes by the number of iterations between reachable reporting boundaries, including descending ranges.

Module-level scalar loops stay in CPython because signal handlers and other threads can observe and change module globals during a loop. Put numeric work in a function with local state to make it eligible. Direct modulo assignments and copied results that may alias an existing integer also stay in Python; modulo terms inside a fresh addition can still qualify.

Extraction remains conservative around reflection, exception handlers, nested scopes, identity-sensitive assignments and arbitrary calls inside arithmetic. More general callback conditions and dynamic strides retain the original loop. A checked native span can retry its pure arithmetic inline in Python before committing results, preserving partial updates if Python raises and avoiding duplicate progress calls.

A whole function that initializes an integer total, adds independent integer terms over one range, and returns that total can now receive an OpenMP candidate. Before running it, Python integer interval arithmetic proves that every intermediate expression and every possible partial reduction fit int64. The serial candidate uses the same up-front proof and unchecked arithmetic, so reported OpenMP speedups against serial isolate the additional threading benefit. Failed proofs preserve Python bigint behavior. Floating sums and progress regions remain ordered. Parallel reductions check Python signals between bounded blocks and use serial native execution when called from a Python worker thread.

Findings expose immutable `Diagnostics` records with codes, source locations, messages and suggestions. Selection reports distinguish no candidates, candidate build failures, validation failures and measured selection. Static overflow warnings describe possible ranges rather than claiming that a fallback was observed. Comprehensions and generator expressions receive explicit unsupported findings. Conversion writes a report even when there are no loops. A completed native compilation can still contain unchanged loops.

For converted `.py` inputs, PyCeler compiles the user-facing module and function code with CPython and exposes guarded native helpers. Unsupported code and failed guards therefore run Python code rather than an unvalidated Cython translation. Original exceptions and module-global updates retain Python behavior. Native `.pyx`/`.pxi` inputs and `Convert=False` use Cython semantics and have a separate compilation contract. Generated modules expose private helper names; reflective inspection of those names, native frames and tracing is outside the preservation contract.

Run the generated extension by importing it from its output directory. Running the original `.py` file continues to execute that source. Module-level statements execute on import; a function inside an `if __name__ == "__main__":` entry point must be called explicitly from a separate runner.

## Build from source

From the root of the GitHub checkout, install the build dependencies and run the build script:

```sh
python -m pip install -r requirements.txt
python -B Compile.py
```

The built package is in `Build/Lib/PyCeler`. Its manifest records source/dependency fingerprints, artifact hashes and a build ID. Checkout imports and the test runner reject stale or modified binaries and name the rebuild command. The runner records the loaded engine path and build ID.

Run the regression suite after building the library. The suite includes wheel creation and installed-wheel checks, so use it when packaging verification is intended.

```sh
python -B Test/Run.py
```

To verify the optimizer while deferring wheel creation, run `python -B Test/Run.py --no-wheels`. The report explicitly lists the two excluded packaging tests.

For release packaging after verification, use the following commands. The example filename is for the Windows x64 build of 0.2.0.

```sh
python -B Compile.py wheel --library Build/Lib
python -B Test/Verify_Wheel.py Build/Wheels/pyceler-0.2.0-cp311-abi3-win_amd64.whl
```

Use the wheel filename produced on your native host; Linux wheels use `linux_x86_64` or `linux_aarch64` tags. Wheel packaging is deterministic for identical built files. It does not claim manylinux qualification or identical native binaries across compiler runs. The maintained CI matrix builds and tests native Windows x64/Linux AMD64/Linux ARM64 on CPython 3.11 and 3.14, then verifies the same artifact on the other interpreter. Local verification does not imply those remote jobs have run. These source changes do not update an already published wheel.

To try the analyzer from the checkout, run:

```sh
python -B Compile.py analyze --input Test/Numeric_Loops.py --rank
```

The example contains both the array fill and the running sum. [Example source](https://github.com/nucleonautomation/PyCeler/blob/main/Test/Numeric_Loops.py)

## Project

[GitHub repository](https://github.com/nucleonautomation/PyCeler) · [Changelog](https://github.com/nucleonautomation/PyCeler/blob/main/Log.md) · [Test guide](https://github.com/nucleonautomation/PyCeler/blob/main/Test/README.md) · [MIT license](https://github.com/nucleonautomation/PyCeler/blob/main/LICENSE.md)
