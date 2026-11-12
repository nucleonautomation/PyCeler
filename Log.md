# PyCeler changelog

## 0.3.0 — 2026-11-12

- Added versioned common loop/type/effect summaries and a repeatable source-coverage inventory, with explicit unsupported cases.
- Extended checked scalar loops with dynamic strides, richer expressions, loop else, early returns and bounded function/module extraction that preserves callback and observable-state ordering.
- Added a numeric-call registry and compiled ordered loops for recognized math, complex-math and NumPy calls. Added guarded unboxed real-math expressions, runtime-gated erf/erfc, and two-argument copysign/nonzero-result fmod lowering.
- Improved interpreter checkpoints, floating-point status and constant preservation, actual native-execution reporting, captured-range small-loop bypass and branch-binding analysis.
- Added optional compiler deadlines with owned-process cleanup, reusable Docker qualification tooling, and regression/benchmark fixtures for the new loop and math paths.
- Included the Markdown README and source repository link in wheel metadata. Updated release version assertions to 0.3.0.
- Release preparation, 2026-11-12 13:23 -05:00: runtime tests and benchmarks remain deferred at the user's request. Historical 0.2.0 results do not qualify the exact 0.3.0 release, particularly the newly integrated binary-math paths. PyPI publication is a separate user action.

## Requested Windows x64 wheel — 2026-11-12 10:11 -05:00

- Built the current source, including binary-math changes, with MSVC/OpenMP and the CPython 3.11 stable ABI as build 32bbdbb2. Packaged pyceler-0.2.0-cp311-abi3-win_amd64.whl under the chat's outputs/windows-x64-current directory; kept the earlier qualified wheel separate.
- Build succeeded and archive metadata records the requested Windows AMD64 tag. No runtime tests, benchmarks, installation or publication were performed. The no-tests instruction remains active; version is unchanged.

## Testing stopped at user request — 2026-11-12

- The user said "no tests". Stopped the active Windows build-and-test command; no owned compiler processes remain and no new binary-math tests ran.
- Eight reviewed binary-math files had already been integrated, including the explicit two-argument plan, guarded copysign/nonzero-result fmod and maintained fixtures/benchmark. The interrupted build leaves this development source unbuilt/unverified; the installed and delivered ba1 checkpoint is unchanged.
- Linux qualification was interrupted when the registered WSL disk disappeared. Preserved Windows-side build/deadline reports and source snapshot. Full Linux suite, wheel checks and observer repeats are incomplete; no recovery or further test execution is authorized by the latest instruction.

## Windows delivery qualified; Linux testing started — 2026-11-12 09:51 -05:00

- Completed both 271-test Windows suites (269 passed, two POSIX-only skips each), 30 observer probes per interpreter, exact wheel probes on both and 14 additional same-wheel regressions. Installed ba1 and verified all 20 artifacts. Fresh math and full-corpus coverage reports identify this build.
- The unchanged 100-million-iteration user benchmark passed all six complete imports. Default measured conversion won at 0.116342 seconds with 1530 parallel spans and actual team eight; the two-worker candidate took 0.1258658 seconds. Generalized the disposable delivery scripts to honor the observed winner and runtime environment. Updated Downloads/Benchmark.pyx and chat outputs, preserving Benchmark.py. The final runner passed exact values/counters. No version change or publication.
- Prepared an isolated Linux ARM64 WSL environment and hash-verified source snapshot. Its native package build succeeded. Preserved an initial test-workspace setup failure, corrected the disposable launcher, then passed all 12 executable deadline checks with one Windows-only skip. Full Linux suite is running; no Linux suite or wheel success is claimed yet.

## Qualification progress — 2026-11-12 09:30 -05:00

- Main Python 3.14 suite passed 271 discovered tests (269 passed, two POSIX-only skips) in 1020.834 seconds. The fresh isolated Python 3.11 package has identical maintained source hashes; its full suite is running and its large math corpus has passed.
- Retained the exact published 3.11 corpus and verified its copy hashes for repeated observer checks, avoiding a redundant compilation. Added a disposable sequential qualification launcher and prepared fresh installed-package verification scripts.
- Refreshed only binary-math staging metadata after the late probe edit. Verified all baseline source hashes; 27 pure checks passed on both interpreters, with 45 existing unary plans retained. Staging remains unmerged and has no native execution claims.

## Resumed checkpoint — 2026-11-12

- Verified current source, tests and compiled library against the saved pause snapshot with no differences. Repaired only the native bypass test's generated-source capture using Convert followed by Compile(Convert=False). Its 59-case native probe passed in 6.286 seconds; Test_Run/Resume_Bypass_20261112.log records the successful test. Production build ba1f9696 remains unchanged; broader qualification resumes.

## User-requested pause — 2026-11-11 14:24 -05:00

- Stopped all implementation and native work at the user's request and saved a resumable source/library/staging checkpoint. Current development build is ba1f9696; the installed and delivered acd44d98 benchmark fix remains unchanged.
- Integrated reviewed common branch bindings, opt-in compiler deadlines, a small extracted-loop bypass and integer/boolean unary-zero correction. The combined focused run passed branch/native math/module/cache/selection checks. Deadline tests now pass all 11 Windows-executable cases, with two POSIX skips, including a real bounded compiler/load and output preservation after an expired rebuild.
- Preserved the earlier cleanup observation race and native-bypass test FileNotFoundError. The bypass test still needs its generated-source capture fixed before its compiled probe can run. Full current-build suites, fresh 3.11 qualification and the bypass benchmark remain pending. Staged binary math is unmerged and its final probe edit left staging metadata stale. Session.md contains precise resume instructions; no further work is authorized while paused.

## Module constants and complete-call checks — 2026-11-11 14:12 -05:00

- Fixed module preparation changing IEEE status even for empty loops containing subnormal constants. Fragment templates compile before user source executes; fresh per-entry source constant identity uses integer bit keys instead of floating hex formatting. Moved observer guard imports to initialization. Build 8bf0e2d passed 32 new serial/OpenMP literal/status comparisons and 21 actual focused module/stride tests. The focused command additionally contained one nonexistent test-module name; the resulting loader error remains recorded rather than being represented as a clean command pass.
- Strengthened generated and large-survey native-entry evidence passed on the preserved 7b build: 10422 generated comparisons and 42 witnesses per binary, plus 44 observed native survey filter calls with actual teams one/two. Default whole-call stride checks passed all 24 cases, avoiding the dense-callback regression and giving 8.08–8.65x gains for large sparse cases. Small sparse-loop dispatch overhead remains open.
- Branch-binding and compiler-deadline proposals passed independent review and integration preflight but remain unmerged. A signed-zero math-expression defect is being reproduced before the next coordinated integration/build. No new installation, publication or version change.

## Runtime strides and math preparation — 2026-11-11 14:01 -05:00

- Integrated runtime nonzero strides for extracted scalar function/module spans, preserving the captured range independently of callback-rebound body variables. Focused Windows checks passed 36 tests. Raw complete-call benchmarks showed 7.29–7.77x gains for large sparse-callback cases and losses for dense callbacks; default measured-selection verification remains pending.
- Added runtime-gated unboxed erf/erfc maps for established CPython 3.12–3.14 backends; 3.11 retains original ordered calls. Fixed floating-status changes from runtime literal formatting/reconstruction and cold guard-module imports. Original constant identity, subnormal bits, signed zero and nested literal keys are retained.
- Active build 7b2845bb passed all 45 focused math tests and nine exact-bit benchmark rows with actual team two. Large two-worker gains were 3.76x for erf, 3.98x for erfc and 2.65x for composition; small inputs favored Python. Reports are Test_Run/Erf_Integrated_j7qudnnk/Summary.json and Test_Run/Erf_Benchmark_ty0te277/Results.json. Full-suite and 3.11 qualification remain pending; the installed qualified acd44d98 delivery is unchanged.
- Strengthened maintained generated-program and large-survey tests with independent native-entry witnesses. Native qualification is active. Branch-binding and compiler-deadline proposals remain staged, with substantive remaining roadmap work tracked in To-Do.md.

## Interpreter checkpoints and verified delivery — 2026-11-11 13:09 -05:00

- Fixed a real CPython 3.11 starvation case in ordered native math loops. Empty GIL release/reacquire blocks and an OS yield did not reliably permit a waiting Python observer to run. Ordered math/module loops now call a cached genuine Python function every 1024 iterations through stable-ABI APIs, allowing normal interpreter handoff. Module bulk spans and unboxed arithmetic retain their existing behavior. Failed attempts remain preserved in Test_Run.
- Strengthened observer tests to act only after committed progress, verify nonempty mutation/cancellation prefixes and inspect all 26 fast-math hooks. Added a private-prefix collision regression and a reusable retained-corpus verifier. The final build passed 30 fresh-process observer runs on each interpreter, all 223 tests on Python 3.14.8 in 725.983 seconds and all 223 on Python 3.11.9 in 696.306 seconds. Exact reports: Test_Run/Run_3v69jwwo/Results.txt and Test_Run/Run_0syg_rtg/Results.txt.
- Verified the exact acd44d98 stable-ABI wheel on both interpreters, plus eight same-artifact tests on 3.11 in 27.570 seconds; installed it locally and verified all 20 installed artifact hashes. Wheel SHA256: aea98c4db6bac1f7344dc58226e47d80aed0512dbb8f5021f2954cabb752ae69. No publication or version change.
- Repeated nine-sample whole-call math comparisons on the current build: at 262144 elements, two-worker gains were 3.84x for sin, 2.86x for a composition and 4.21x for expm1. Exact output bits and actual worker teams were checked. Test_Run/Math_Benchmark_qlmliwn2/Results.json records all sizes and variation; small inputs favored Python.
- Replaced Downloads/Benchmark.pyx with verified typed native/OpenMP code and delivered an executable runner while preserving the original Python source and old generated-source backup. Three interleaved complete runs per candidate measured median 0.264012 seconds for default native serial and 0.125739 seconds for the two-worker candidate, with all final/progress results equal. The delivered candidate executed 1531 parallel spans and zero fallback; the final runner independently passed with result 49999504352964. Evidence: Test_Run/Installed_Fairness_Verification/Results.json and the chat outputs Verification.json/Runner-results.txt. Explicit OpenMP generation was selected afterward by complete-call measurements; it is not mislabeled as default policy selection.
- The current Windows qualification and delivery are complete. General mixed-region proofs, wider unboxed algorithms and other-platform qualification remain open. Runtime-stride and erf/erfc extensions are staged separately and are not part of this qualified build.

## Execution reporting — 2026-11-11 11:17 -05:00

- Fixed measured module reports that could replace a genuine native dispatch observation with unchanged statistics from an unrelated scalar-reduction helper. Preserve actual native entry, actual worker count, and independent native/fallback evidence across module spans. Keep legacy region and reduction counters usable only when they supply fresh evidence.
- Added six regression tests, including real measured serial and OpenMP module candidates. All six passed in 7.303 seconds; the final full Python 3.14 suite passed all 222 tests in 744.528 seconds. The exact delivered wheel passed public pipeline probes on both interpreters and seven additional reporting/math-selection checks on 3.11. The separate final 3.11 full suite remains in progress. Earlier 216-test qualification reports remain archived.
- Installed the final local 0.2.0 wheel and compared complete unchanged benchmark imports with interleaved samples: default measured serial median 0.265336 seconds; explicit two-worker OpenMP median 0.1250368 seconds, 1531 actual parallel spans, zero fallback and exact progress/final values. The OpenMP candidate was generated with selection disabled and then chosen by these whole-call measurements; default small-probe policies legitimately retained serial. Report Test_Run/Final_Installed_Verification/Results.json links tested bytes by hashes. No publication.

## Optimizer implementation — 2026-11-11 09:58 -05:00

- Replaced the unchanged module-loop fallback in eligible numeric code with checked native arithmetic, bounded serial spans and exact OpenMP reduction spans. Preserved progress callbacks, globals, signal-visible state, exception prefixes, empty ranges and loop else behavior. The supplied unchanged 100-million-iteration benchmark now executes real prange work; complete-call default conversion measurements matched every result and progress total.
- Extended scalar lowering with dynamic nonzero range strides, loop else, early returns, chained comparisons, tuple locals, conditional expressions, checked powers, shifts and bitwise operations. Added deterministic common analysis plans and a source inventory accounting for every loop in the maintained test corpus.
- Added a versioned 217-record numeric registry, compiled ordered math/library-call loops covering 205 available callables on the development interpreter, and guarded unboxed float64 serial/OpenMP expressions for 24 unary real-math functions. Ordered library calls retain their original algorithms; they are reported separately from unboxed math.
- Fixed measured validation profiling that prevented eligible kernels from entering native spans. Added complete worker floating-environment restoration, source constant identity preservation, future-annotation compilation, private-name collision handling and independent reporting-boundary arithmetic.
- Removed duplicate math evaluation with a bounded scratch buffer, validating each chunk before ordered output commits. Invalid chunks resume original exception behavior, allocation failure declines safely, complete worker environments are restored, and standard IEEE status is merged without changing caller controls.
- The clean final Windows/AMD64 Python 3.14 suite passed all 216 tests in 628.412 seconds (Test_Run/Run_xl91t49w/Results.txt). Focused math checks passed 326 exact comparisons. Nine-sample large float64 whole-call comparisons measured OpenMP gains of 3.90x for sin, 2.90x for a composition and 4.76x for expm1; small inputs still favored Python (Test_Run/Math_Benchmark_f8d_vmai/Results.json). These measurements used AMD64 Python on the recorded ARM64 Windows host. Python 3.11 qualification and local installed-wheel update remain in progress. Version remains 0.2.0; no publication.

## Maintenance — 2026-11-11 07:21 -05:00

- Added a maintained Docker test launcher with disposable containers, cleanup on failure/interruption, isolated source copies and host-persisted reports. Documented the three required image names and added mocked lifecycle regressions to prevent abandoned test containers. Coordinated with the other cleanup agent, archived and removed four obsolete PyCeler containers, and retained required toolchain images. Syntax parsing and whitespace checks passed; no tests or builds were run for this change.

## Planning — 2026-11-10 19:56 -05:00

- Expanded the local math roadmap with function-level coverage and qualification criteria. This is planning only; no additional optimizer functionality is implemented.
- Documented a staged roadmap for broader loop and math optimization, building on the current engine with shared analysis, safe native regions, measured selection and regression criteria. These capabilities remain planned; implementation and version 0.2.0 are unchanged.

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
- Included the project README and GitHub source link in wheel metadata for the PyPI project page.

## 0.1.0 — 2026-11-09

- Added CPython 3.11 stable-ABI wheels for Windows x64, Linux x86-64 and Linux ARM64.
- Added `PyCeler.Analyze` to identify and rank expensive loops without running the source. Findings include source locations and reasons a loop may be unsuitable for optimization.
- Added `PyCeler.Convert` to generate serial Cython for supported numeric loops, including array fills, copies, thresholds and bounded arithmetic. Loops with independent iterations can also use OpenMP.
- Added `PyCeler.Compile` to build native extensions. Existing Cython sources can be compiled directly with `Convert=False`. Builds default to individual native modules and the CPython 3.11 stable ABI.
- Added behavior checks and workload-based timing to select among Python, serial Cython and OpenMP. Runtime guards fall back to Python when inputs fall outside the selected specialization.
- Added optional profiling, thread and tile tuning, and caching for selection results and compiled extensions.
- Added a requirements file for installing the Python build dependencies.
