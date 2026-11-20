# Running the PyCeler tests

Run `python -B -m unittest Test.Test_Indexed_Filters` for the indexed float64 distance filter. It compares native and fallback calls with Python, including order, duplicates, exact ties, strided tables and partial output on index errors.

Implementation and test comments explain contracts, guard decisions and validation intent. The 2026-11-19 documentation pass preserves executable tokens and existing source locations, including line-sensitive fixtures. For readable workload inputs and on-demand Cython generation, see the [Example catalogue](../Example/README.md). Bulk example folders contain only Python sources; generated outputs belong under ignored Test_Run/Examples.

## Direct-source lexical scopes

Run `python -B -m unittest Test.Test_Direct_Scopes Test.Test_Readable_Pyx -v` after rebuilding and loading the compiler environment. The independent fixture checks deleted and rebound captures, nonlocal updates, repeated/partial deletion, class-private names, defaults, shadowing, annotation-only/dead-walrus locals, late globals and replaced builtins. Compare exact exception classes, arguments, name attributes and observable results. The five catalogue fixtures additionally reuse Branch_Bindings_Probe, Nested_Scope_Probe, Iterator_Scope_Probe, Module_Scalar_Probe and Scalar_Math_Probe; eligible cases require actual native execution. Final installed-wheel evidence is in Test_Run/Direct_Scope_Fix_20261119/Qualification.json.

## Array extrema, clamped indices and sequential loops

Run `python -B -m unittest Test.Test_Array_Extrema -v` after rebuilding and loading the compiler environment. One combined fixture checks typed two- and multi-argument min/max, selected-operand precision and ties, rank-three clamped convolution, histogram scatter, Python-integer floor division, repeated reduction loops, borrowed return identity and fallback for non-finite/large values, aliases, strides, read-only outputs and partial index errors. Large independent convolutions require actual parallel workers. Both repeated reduction loops must be extracted. Generated source must contain no baseline source-string wrapper or runtime exec/compile calls.

The shared prior-binding analysis is also checked with `python -B -m unittest Test.Test_Numeric_Regions.Numeric_Regions.test_Compiled_Control_And_List_Families -v`, which covers exact list arithmetic, object identity, errors and floating environment behavior. Build-specific image-pipeline timings and qualification are recorded in Session.md and Test_Run/Image_Performance_20261119.

## Single readable Cython file

Run `python -B -m unittest Test.Test_Readable_Pyx Test.Test_Module_Scalar -v` after rebuilding and loading the compiler environment. The focused readable-source fixture checks one .pyx with no generated exec/compile calls or Python sidecar, edits its application message, recompiles with Convert=False, compares ordinary code and ordered reductions, and requires actual eight-worker native array execution. Static scope cases check shadowed builtins, local arguments, comprehensions, imports and global assignments. Module checks cover callbacks, empty ranges, big integers, shadowed builtins and partial exceptions.

Generated application definitions now follow Cython function semantics. FunctionType identity, mutable __code__ and CPython tracing are not promised. Guarded fallback bodies remain visible callable code in the same file. Runtime signal/cancellation checks are in Test.Test_Observable_Semantics; all test execution evidence is recorded in Session.md.

## Integer array values and indirect indices

Run `python -B -m unittest Test.Test_Integer_Arrays -v` after rebuilding and loading the compiler environment. One combined native fixture covers unannotated compressed sparse traversals, integer-loaded range bounds, indirect and two-hop indexing, signed/unsigned widths, NumPy scalar promotion, float32 precision, integer prefix dependencies, overflow, large-value fallback, strides, aliasing and index errors. Comparisons include mutations, scalar types and warnings; eligible cases require native entries and independent large cases require actual OpenMP workers. Exact integer buffer preparation checks native integer values before conversion. Values outside the native representation retain Python execution.

Default selection also infers which buffers provide integer indices and gives offset arrays the required positive-index padding. Full graph qualification and the remaining per-iteration scratch-allocation limitation are recorded in Session.md and Test_Run/Graph_Performance_20261119.

## Complete native array writes and scalar powers

Run `python -B -m unittest Test.Test_Complete_Arrays Test.Test_Array_Powers -v` after rebuilding and loading the compiler environment. Complete-transaction checks require native element counts to include the final outer slice. They cover nested stencils, reverse ranges, conditional writes, f32/f64, strides, aliases, read-only and short outputs, integer destinations and first/last-element errors. Ordinary live-output, module, RNG and iterator paths keep their existing contracts.

Power checks compare exact dtype/values, ordered reductions, helper locals, branches between NumPy/Python scalar results, signed zero, negative bases, under/overflow, RNG state and broad finite inputs. The supported literal integer-exponent grammar is shared with numeric regions. NumPy scalar power uses its precision-specific math routine: see the official [scalar implementation](https://raw.githubusercontent.com/numpy/numpy/v2.5.4/numpy/_core/src/umath/scalarmath.c.src), [math declarations](https://raw.githubusercontent.com/numpy/numpy/v2.5.4/numpy/_core/include/numpy/npy_math.h), [float math implementation](https://raw.githubusercontent.com/numpy/numpy/v2.5.4/numpy/_core/src/npymath/npy_math_internal.h.src) and [platform exceptions](https://raw.githubusercontent.com/numpy/numpy/v2.5.4/numpy/_core/src/common/npy_config.h). Qualification remains build/platform-specific in Session.md.

## Live outputs and conditional loop tails

Run `python -B -m unittest Test.Test_Common_Values Test.Test_Region_Tails -v` after rebuilding and loading the compiler environment. One native fixture covers triangular and reverse nests, conditional tails, live final counters/aliases and dead temporary outputs across lists and float32/float64 arrays. Large independent cases require actual parallel workers; dead-output cases require native completion without a trailing fallback. Static checks retain module bindings, augmented assignments and enclosing-loop uses. Prefix recovery splits only unpublished range transactions, uses a bounded retry budget and preserves Python execution for the remaining work. Iterator transactions remain indivisible.

## Iterator and shape metadata checks

After loading the compiler environment and rebuilding, run `python -B -m unittest Test.Test_Iterator_Regions Test.Test_Shape_Only Test.Test_Iterator_Selection -v`. Each runtime matrix compiles one combined fixture. They compare exact results, mutations, exceptions, final target identities and constructor/callback ordering; eligible cases require native entries and independent large cases require actual OpenMP teams. The selection check uses one representative/held-out iterator function across lists and float32/float64 arrays. Qualification status is recorded per build in Session.md.

`Test.Test_Iterator_Scopes` covers tuple-bound outer row loops, captured inputs, once-only range evaluation and array-primary/list alternatives. `Test.Test_Common_Values` and `Test.Test_Affine_Aliases` check shared dependency proofs, including stable integer runtime offsets. The normal test runner discovers these modules automatically; focused commands avoid rebuilding unrelated large corpora.

## Read-only aliases, indexed lengths and math-map composition

Run `python -B -m unittest Test.Test_Planner_Composition Test.Test_Readonly_Storage Test.Test_Readonly_Selection -v` after rebuilding and loading the compiler environment. The raw serial/OpenMP matrix covers identical and overlapping read-only inputs, repeated read-only list rows, output collisions, float32/float64 arrays, negative/dynamic row indices, rectangular rank-three storage, ragged/empty storage and shared length-result identities. Each coordinate of an indexed length is checked before evaluating the next coordinate. Positive cases require native counters and large independent cases require real worker teams.

`python -B -m unittest Test.Test_Native_Prefix -v` checks that source-prefix assembly preserves user literals/comments, renames embedded C and native identifiers correctly, and handles large Unicode/CRLF inputs. The assembly pass collects replacements and joins the output once, avoiding a complete source copy for every replacement.

Compatible math maps offer list and float32 array alternatives while retaining original imported-library contracts. The separate selection test uses representative and held-out heavy math workloads with shared inputs, requires native observations for each storage family, and checks actual parallel execution after default selection. Build-specific results and preserved before/after reproductions are recorded in Session.md and Test_Run/Generalization_20261118.

## Pure helper calls and imported math aliases

Run `python -B -m unittest Test.Test_Helper_Calls -v` after rebuilding and loading the compiler environment. The serial/OpenMP matrix compares list float/integer/boolean inputs and float32/float64 ndarrays, nested helpers, ordered keyword and unused arguments, checked integer intermediates, shared output identities, partial errors, local/captured callables and changed code/default/global bindings. Eligible cases require actual native entry; large independent cases require parallel workers. A separate measured-selection test keeps the helper definitions and imports in the reference/probe modules.

Current helper contracts cover undecorated same-module functions with fixed signatures, optional straight-line local assignments/augmented assignments and a parameter-dependent numeric return. Native arguments and local expressions evaluate once in Python order, including unused computations. Helper math resolves through the helper's globals rather than caller shadows. Runtime guards compare exact function/code types, source globals, defaults, closures and behavior fields before computation and publication. Reference code is compiled in the complete original module context without executing that module, preserving compiler import-context differences. Direct imported math aliases share the registry's lexical binding facts across list/array planners. More general helper bodies, defaults and borrowed/constant return identities remain separate work.

Run `python -B -m unittest Test.Test_Helper_Locals Test.Test_Helper_Local_Selection -v` for the focused local-value extension. The raw matrix covers exact float32/float64/list arithmetic, nested local values, unused division errors and changed helper callbacks. Selected holdouts must enter native code. `Test.Test_Selection_Safety` checks that expected exceptions remain correctness evidence without supplying timing evidence; mismatched exceptions still veto a candidate, and inconclusive holdouts remain conservative.

Conditional helper and inline expressions carry the selected NumPy scalar dtype through later arithmetic, nested calls, negation and absolute values. Mixed float32/float64 cases require bit-exact output and positive native counters; comparisons include float32 weak-scalar rounding at branch boundaries. `Monitoring_Cases.py` and `Monitoring_Probe.py` require unmonitored native work, then exact helper/caller callback counts and no native work under global or code-local `sys.monitoring` events. Replacement monitoring getters, namespaces and frame getters must retain Python without invoking the replacements. On Python 3.11 the monitoring-specific cases are explicitly unavailable; unmonitored native checks still run.

`Test_Array_Regions.test_Ordered_Random_State_And_Transactional_Errors` builds serial and OpenMP variants of `Array_Random_Loops.py`. Its probe compares complete RNG state, including a populated Gaussian cache, alongside exact result/mutation/error observations. Conditional expressions, nested conditions, random conditions, statement branches, row loops, zero/all draws and multiple outer chunks are covered. Static branch draw bounds permit independent equal-draw branches to use OpenMP; variable draw counts run in ordered native code and publish only the actually consumed prefix. Required-native and actual-team assertions distinguish specialization from a correct Python fallback.

`Test_Array_Regions.test_Random_Range_Errors_And_Lazy_Branches` checks module state when an inner range has a zero step or is unreachable behind an empty range. It also requires native work for valid/reverse ranges and short-circuit random conditions with constant branches. Every case compares exact outputs, final loop bindings, exceptions and complete RNG state in serial and OpenMP builds. Primitive ndarray stores do not require fresh Python objects; numeric list stores retain their identity contracts.

`Random_Bound_Loops.py` checks random calls in range bounds, numeric extraction inside those bounds, unrelated nested list/array math, exact RNG state and actual parallel teams. Its default-selection test includes representative and held-out heavy workloads. Range sizing restores the probe's RNG state. A fully accepted enclosing typed region can replace contained scalar plans; unsupported enclosing work retains them. `Test_Random_Staging.py` injects null/short private staging into generated artifacts and requires exact original execution without publishing speculative work.

## Wrapped indices and range object identity

Run `python -B -m unittest Test.Test_Wrapped_Indices -v` after rebuilding and loading the compiler environment. The serial/OpenMP corpus covers negative and stepped indices, nested wrapped rows, float/integer/boolean lists, float32/float64 arrays, partial errors and normalized-address collisions. Shared range-index stores retain Python object identities, including cached small integers and distinct larger integers across worker chunks. Positive cases require native counters; independent large cases require actual parallel workers. The default-selection test separately verifies a measured negative-index math loop. Build-specific results remain recorded in Session.md.

## Shared value and lexical scope proofs

Run `python -B -m unittest Test.Test_Common_Values Test.Test_Affine_Aliases Test.Test_Scalar_Promotion Test.Test_Nested_Scopes -v` after rebuilding and loading the compiler environment. These fixtures exercise shared list/ndarray facts: stable preceding affine aliases, scalar parameters that immediately promote into floating arithmetic, and nested functions with distinct qualified names and captured bindings. Affine tests require real OpenMP teams for independent aliases and preserve serial execution for dependent, reassigned and conditional indices. Scalar tests compare exact types and bits and retain integer-only intermediates and subclass behavior.

Nested scope tests compare ordinary nested kernels, captured list/array inputs, changed captured scalars and math functions, shadowed builtins and nonlocal mutation. They also cover deleted closure cells, default-expression bindings, local/global shadows and class-private global names. A captured callable must pass the same live binding checks as a module callable; an unknown replacement must execute Python. Raw builds require actual native entry. Measured builds require native probe observations and verify the final reported policy, including Python when a candidate is slower. Qualification status and build-specific results are recorded in Session.md rather than implied by the existence of these tests.

## Competing storage backends and bounded selection probes

Run `python -B -m unittest Test.Test_Storage_Composition Test.Test_Storage_Rank Test.Test_Selection_Budget -v` after building and loading the compiler environment. Ordinary map syntax now offers guarded list alternatives and the newer ndarray arithmetic backend where the earlier map cannot handle composed floating operations. Synthetic and representative measurements keep `list_float`, `list_integer` and ndarray dtype keys separate. Extracted-region workload factories follow the region's argument order; for these maps the report records it in `List_Alternative.Names`.

The storage probe compares exact values, types, aliases, warnings, partial errors, ndarray bytes, strides and writeability across whole and extracted functions. It checks float/integer lists, float32/float64/int32/int64 arrays, normal measured dispatch, unselected native candidates and complete optional-build failure. Multiple floating operations on integer arrays still require further dtype lowering; simple supported integer maps remain native. The multidimensional regression verifies that selection observes the measured total element count rather than the number of outer rows.

Synthetic numeric probes receive a bounded preflight before validation and timing. The preflight copies inputs, restores RNG state when needed and restores the caller's trace hook. Expensive nested probes and explosive bigint growth cannot erase earlier completed measurements, and later manageable cases still run. The worker's separate hard process deadline remains necessary for operations that cannot be interrupted by Python tracing. This budget controls conversion probes, not valid user input sizes or the result of runtime calls.

Synthetic cases that exhaust a work, storage or measurement budget remain visible as inconclusive and do not create a new performance band. Unbounded synthetic selection may extrapolate an earlier completed band, explicitly labeled as unmeasured at the skipped size. Representative and holdout cases remain conservative: inconclusive evidence can still reject their band. Invalid output evidence always excludes the candidate, regardless of timing budgets.

## Shared list/array generalization and aliases

Run `python -B -m unittest Test.Test_Generalization Test.Test_Numeric_Regions Test.Test_Expanded_Numeric Test.Test_Array_Regions Test.Test_Common_Analysis Test.Test_Source_Analyzer Test.Test_Selection -v` after building and loading the compiler environment. Generalization_Cases.py generates14 unrelated families in one mixed list/NumPy module. The compiled probe compares exact values, array bytes/storage, object aliases, errors and real native counters. It covers nested accumulators, builtin abs binding changes,72scalar slots,12buffers, repeated index names, inner ranges exceeding1,048,576 iterations, read buffers exceeding4,194,304 cells, and affine/non-leading-axis independent writes. Integer abs of an existing positive int must preserve the original object; constant-folded float aliases must survive. Cases requiring these unsupported borrowed-object identities retain Python, while fresh computed values share native origin tokens and reuse boxed output objects.

Assignment metadata now scales with the region instead of a64-bit mask; buffer counts are plan-sized. List storage allocations use size-overflow and allocation-failure checks instead of fixed cell-count ceilings. List/array parallel eligibility shares affine storage proofs and verifies bounds, aliasing and original arithmetic order. Ordered reductions stay serial. Finite for ranges no longer share the while-loop work budget. Array annotation hints stay within their Python scope. These changes do not imply native arithmetic for every dtype or universal syntax coverage.

Enable `_Pyceler_Dispatch_Stats(True, True)` on a generated module to record optional dispatch and per-region guard observations; `_Pyceler_Guard_Stats()` returns guard counts. `Execution` is the last event; `Totals` accumulates `Native_Entries`, `Parallel_Entries` and `Maximum_Team` until reset. Check both for calls that run native spans before a Python fallback. Turn observation off for timing. A selected candidate still needs a positive native counter on the actual workload; static classification and selected status alone do not establish a speedup.

## Arbitrary-rank array regions and ordered random generation

Run `python -B -m unittest Test.Test_Array_Regions Test.Test_Expanded_Numeric Test.Test_Selection -v` with the built package and compiler environment. Eight array families cover 1D ordered sums, 2D stencils, four- and six-dimensional maps, strides, dependent recurrences and primitive output casting. Probes compare exact scalar types, floating bits, mutations, storage aliases, warnings and exceptions. They require native entry and actual OpenMP execution on eligible independent writes. Additional cases exercise overlapping/read-only storage, floating error settings, missing math bindings, rebound internal NumPy helpers and scratch allocation failure.

The random corpus tests unconditional rectangular standard `random.random` generation, exact final RNG state (including the Gaussian cache), multiple draws, domain/bounds failures and replaced callbacks. Selection checks preserve NumPy scalar dtype and identity, constant-width axes, inferred ndarray hints and representative outer ranges. `Benchmark_Pipeline.py` compares full program globals, NumPy/Open3D/Pandas data and both RNG states in fresh processes; `--profile` records whole-stage timing without disabling native guards.

Array kernels accept arbitrary statically known rank, positive/negative strides and f32/f64 reads; output-only buffers additionally support primitive integer and boolean storage. Floating operations retain their dtype rounding and reductions remain ordered. Unsupported arithmetic dtypes and ranges fall back to the original Python. Removing rank cutoffs does not remove bounds, alias, precision or memory-safety checks. Generated array chunks have no fixed four-million-cell ceiling; memory exhaustion before publication declines native work.

## Expanded numeric lists, volumes and fills

Run `python -B -m unittest Test.Test_Expanded_Numeric Test.Test_Numeric_Regions Test.Test_Selection -v` after building and loading the compiler environment. Eight reusable functions cover 3D initialization/stencils, a four-dimensional list, integer and boolean neighborhoods, negative/positive strides, scalar carries, integer matrix products and repeated indirect destinations. The probe compares exact values and alias graphs on empty, small and large inputs, mixed/overflowing cells, shared/ragged storage and failing bounds. Module cases cover partial globals after errors across a 65,536-iteration block, unchanged accumulator aliases and destructor order.

Numeric list regions now support arbitrary statically known rank and homogeneous float input cells or bounded integer/boolean input cells. Storage and exact-integer precision guards remain. Results retain their planned float, integer or boolean types. Successful finite for regions use one transactional snapshot and publication; OpenMP computation runs in chunks of up to65,536outer iterations with signal checks and persistent object-identity sequences. Regions containing while retain128outer blocks. A failed finite computation records its first failing iteration so a safe prefix can retry natively before the original Python continuation; guard failures and failures at the first iteration immediately preserve Python. The original final iteration preserves scalar values and aliases. Numeric_Fills.py recognizes affine writes of cached integer/boolean constants and validates only affected cells before direct publication. Measured selection includes large flat spans and retains Python where runtime costs outweigh savings. Stateful random calls and mixed tuple/append/generator loops remain outside this list path.

Run `python -B -m unittest Test.Test_List_Runtime Test.Test_Expanded_Numeric -v` to verify large shared identities, repeated reference lifetimes, nested spans, module carries, destructor boundaries, and partial errors in forward/reverse ranges. Runtime list access uses checked stable-ABI C API functions while snapshots retain the original objects; this does not remove type, alias, binding, mutation or arithmetic guards. Build-specific qualification remains recorded in Session.md.

`Benchmark_Programs.py` extends the fresh-process benchmark harness to compare the random generator state as well as values, aliases and native counters. Campaign orchestration and generated artifacts belong under Test_Run, never in maintained source or the user's original benchmark directory.

## Nested numeric list regions — 2026-11-17

Run `python -B -m unittest Test.Test_Numeric_Regions Test.Test_Source_Analyzer Test.Test_Selection -v` after building and loading the compiler environment. `Numeric_Region_Loops.py` covers escape-time images, pairwise interactions, in-place integration, ordered prefix recurrences, positive/negative integer powers, nested loops, `break`/`continue`, sparse writes, length bounds, aliases and partial mutations before math calls. The probe checks exact numeric bits and identity graphs, empty/short/aliased/ragged inputs, nonfinite/extreme values, domain/overflow failures, missing/rebound math bindings, observers, rounding and floating flags. Module cases check errors before and after native chunk boundaries, final temporary aliases and literal identity. Eligible cases must increase native counters.

`Numeric_Regions.py` builds guarded plans and the shared `Fast_Math.py` expression IR handles buffered reads, exact bounded integer operations and CPython powers. `Numeric_Region_Emitter.py`, `Numeric_Region_Kernel.py` and `Numeric_Region_Runtime.pxi.in` emit serial native control flow, buffer mutations in original order, validate the final iteration, prepare boxed outputs and recheck state before publication. Final original iterations preserve visible scalar values and aliases. Native entry requires homogeneous float or bounded integer/boolean input lists, supported scalar types, disjoint storage across names and an eligible observer/rounding environment. Integer output lists are supported. Native regions use bounded blocks with a bounded internal loop budget; unsafe or incompatible work retains the original Python behavior. Powers intentionally call CPython's numeric API instead of replacing exponentiation with a differently rounded multiplication sequence.

Automatic selection measures complete guarded calls. It can select native nested work while retaining a short neighboring update loop in Python. Prefix sums now qualify as ordered serial candidates; their dependency explanation still rules out parallel execution. Existing NumPy/OpenMP backends remain separate candidates. No benchmark filename, variable name, dimensions or mathematical constants select these transformations.

## Rectangular Python list grids — 2026-11-17

Run `python -B -m unittest Test.Test_List_Grids -v` after building the library and loading the compiler environment. Eleven maintained loop patterns cover weighted neighborhoods, diagonals, horizontal/vertical differences, branches, coordinates, division, aliases, repeated grid swaps, `len` bounds and multiple inputs. The probe compares exact float bits, errors, mutations and retained list/row identities. It exercises overlapping/shared rows, ragged shapes, out-of-bounds access, integer/tuple inputs, signed zero, nonfinite/extreme floats, rebound functions, profiling, rounding and floating flags. Separate module tests check final globals, constant aliases, partial state on division/index errors and destructor timing. Positive native counters are required for eligible cases.

`List_Grids.py` recognizes operation families without matching source filenames, identifiers or particular coefficients. `List_Grid_Kernel.py` emits typed double arithmetic using the shared math IR. It validates exact float lists and disjoint destinations, computes into temporary buffers, and boxes results before publishing. It validates the final cell before any publication, then executes that cell's original body to preserve final temporary aliases. Incompatible shapes, objects, bindings or observers use the original loop. This candidate is serial; initialization, outer time steps and ordered checksum work remain Python unless another existing specialization accepts them. Default selection measures complete guarded grid calls and can retain Python for small workloads.

For end-to-end module timing, run `python -B Test/Benchmark_List_Grids.py <source.py> <compiled.pyd> <results.json> '["grid","next_grid","total_energy","checksum"]'`, adapting the JSON field names to the module. It runs one warmup and three alternating fresh-process samples, compares exact state and identity graphs for the requested fields, and requires native execution. Keep original user source unchanged and compile it before timing.

## Shared math backend performance — 2026-11-17

The math emitter now obtains the thread's `errno` address once per scalar span or array worker evaluation and uses that pointer for every original reset/check. No error check is removed and no pointer is shared between workers. Inline binary64 finite checks are common to scalar and array kernels. Native state locals can stay in registers; volatile expression temporaries retain each intermediate rounding point. Exact C API type checks reduce scalar entry overhead while excluding subclasses and destructors.

Run `python -B -m unittest Test.Test_Scalar_Math Test.Test_Fast_Math Test.Test_Fast_Binary Test.Test_Fast_Binary_Plan Test.Test_Fast_Erf Test.Test_Fast_Erf_Backend Test.Test_Hard_Optimization Test.Test_Math_Unary_Signs -v`. The maintained `Scalar_Math_Families.py` builds 50 direct/nested functions spanning 25 math operations with renamed variables, 350 exact value/error comparisons and 100 positive native cases on CPython 3.12+. A separate OpenMP test requires distinct worker error pointers and independent values. Existing array tests cover unary/binary math, 2D/3D maps, domain and overflow errors, aliasing, partial writes, floating flags, rounding, and observed worker teams. Use `python -B Test/Exercise_Hard_Optimization.py --stage 3 --output Test_Run/Hard_Performance --benchmark` to validate and time the eleven-function scalar-expression/NumPy map corpus at three sizes in serial and parallel builds. These shared transformations do not match any benchmark filename, variable name or particular numeric constants.

## Scalar floating math recurrences — 2026-11-17

Run `python -B -m unittest Test.Test_Scalar_Math -v` after building the library and loading the compiler environment. `Scalar_Math_Loops.py` and `Scalar_Math_Probe.py` cover ordered sin/cos state updates, module aliases and direct imports, branches and short-circuit expressions, nested/descending/empty loops, signed zero, nonfinite values, domain/overflow errors, final and partial global state, rebound functions, profiling, rounding modes, floating exception flags and destructors on replaced values. Native counters must increase for eligible cases. The compiled probe runs in a fresh process so test-runner instrumentation cannot silently force fallback.

The scalar planner reuses the ordered math IR and libm contracts from array maps. Spans use exact float inputs and bounded integer indices, preserve intermediate rounding, and commit only after successful evaluation. Runtime incompatibility replays the original span. Short serial spans retain the GIL to prevent binding changes during calculation; observable globals are published before checkpoints. The original Python fallback can remain embedded in generated Cython even when the hot loop runs natively. Finite-value checks use the IEEE binary64 exponent bits, avoiding repeated Windows runtime calls without relaxing numerical checks. Selection probes include float arguments and short spans instead of timing unsupported integer inputs.

## Scalar operator eligibility audit — 2026-11-17

Run `python -B Test/Exercise_Scalar_Eligibility.py --output Test_Run/Eligibility_Manual` after loading the compiler environment. The reusable matrix crosses twenty expression/update families with whole functions, extracted regions, retained outer loops, module bodies and renamed equivalents. It requires 160 native plans across 120 functions and forty module regions. Both serial and OpenMP-requested builds perform 1320 comparisons, 240 positive native-call checks and forty native module checks each. Stateful loops deliberately remain ordered serial kernels.

The corpus includes AND/OR/XOR, both shifts, powers, negation, inversion, positive signs on fresh expressions, conditionals, modulo of a fresh expression, cached negative literals and augmented assignments. It compares result values, types, identity relationships, exceptions, empty ranges, negative/zero operands, bigint inputs, overflow and unsupported runtime types. `python -B -m unittest Test.Test_Scalar_Eligibility Test.Test_Nested_State_Regions -v` additionally checks retained alias/constant identities and the multi-branch stateful benchmark's final/partial globals.

Fresh-result analysis is shared by whole-function return checks and scalar-region output checks. It distinguishes operations that produce independent integer objects from aliases and compiler-folded constants. In particular, unary plus and modulo can preserve an operand, and a zero right shift can preserve a large negative integer. See the [CPython integer implementation](https://github.com/python/cpython/blob/3.14/Objects/longobject.c) and the corresponding 3.11 implementation; the audit's source snapshots are recorded with the campaign evidence. The optimizer must retain the identity guards instead of treating every integer expression as safe to rebox.

## Iterative hard optimization corpus — 2026-11-13

Run `python -B Test/Exercise_Hard_Optimization.py --stage 3 --output Test_Run/Hard_Manual --benchmark` after loading the compiler environment. Stages 1, 2 and 3 progressively add ordered math temporaries, conditional/short-circuit math, and nested math and multi-statement NumPy kernels in two and three dimensions. Both serial and OpenMP binaries are compiled from the maintained eleven-function `Hard_Optimization_Loops.py` fixture. Reports include exact output bytes, returned output identity, input mutations, exceptions, native element counts, thread teams and complete-call timings at 64, 4096 and 262144 elements. Inputs and compilation are excluded from timing; one warmup and three alternating timed samples are used. Each timed native call must show native execution. Alias, shifted overlap, read-only/strided outputs, mismatched/empty shapes, float32 fallback, wide rows/slabs, integer overflow and rebound inner `range` calls are checked separately.

`python -B -m unittest Test.Test_Hard_Optimization -v` runs the static coverage requirement, compiled correctness corpus without benchmarks, and a regression ensuring assignments to shape-bound aliases cannot incorrectly flatten later rows. It is also included in normal test discovery. These are guarded specializations: a declined runtime guard must preserve Python's values, mutations and exception order.

The workload-ordering regression also requires an unboxed math candidate's float64 cases to run before integer and float32 probes, preserving every other case and its inputs. This lets a limited automatic-selection budget reach the candidate's supported dtype.

## Compositional scalar extraction — 2026-11-13

The user reauthorized optimizer testing. `python -B -m unittest Test.Test_Scalar_Flow -v` covers six assignment/control-flow forms in four function placements, with renamed equivalents, plus twelve module regions. The maintained corpus crosses conditional expressions, tuple assignments, temporary copies followed by arithmetic, cached literals and branch merges with direct loops, outer `for`/`while` loops and preceding branches. Static checks require all 60 intended numeric regions to be recognized; compiled checks compare 384 function cases and twelve module results with Python and require per-call native counter deltas on positive cases. Empty ranges, negative strides/moduli, zero divisors, integer overflow and final alias exclusions are included. The measured-selection check requires validated native observations without executing surrounding Python work. These cases are discovered automatically by `Test/Run.py`.

The current release source is **0.5.0**. Its version assertions and wheel metadata fixtures are aligned with that version. Current focused scalar checks do not qualify every subsystem or the earlier release artifacts; the 0.2.0 results below are historical.

The 2026-11-12 testing pause was lifted for benchmark and optimizer work on 2026-11-13. Newly integrated binary-math source and tests have not run; the historical results below qualify the earlier installed ba1 checkpoint. Linux's full suite was interrupted when its registered WSL disk disappeared, so its full-suite/wheel qualification remains incomplete.

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
