# Verification of the example catalogue

Storage update: the user requested source-only `Loops` and `Benchmarks` folders after this qualification. Their generated `.pyx` and selection JSON files have been removed. The results below describe the earlier verified outputs, not a new run. All Python inputs remain; regenerate bulk outputs under ignored `Test_Run/Examples` with `Example/Generate.py`. The small root Quick_Start pair is retained.

Checked on 2026-11-19 with PyCeler 0.4.0, build `0c683325ac3781ac51f5a9023fe9e776f9e295e038e509026747a1b27424a450`. Host: Windows 11 ARM64 running AMD64 CPython 3.14.8, NumPy 2.5.4 and Cython 3.3.1; native builds use MSVC and OpenMP.

- All 78 ordinary Python inputs parsed and were converted to readable `.pyx` files with this converter using `Select=False, OpenMP=True`.
- All 78 generated files pass Cython-to-C translation, including all 17 full benchmarks and the broad math/cmath/NumPy corpus. No full benchmark was rerun for these scope fixes.
- The five formerly failing fixtures now live in `Loops`. The exact wheel was installed into an isolated directory; all 49 packaged files were verified byte-for-byte against the wheel. That installation compiled all five catalogue outputs and passed the maintained behavioral probes, including exact errors, mutations, module state and required native/parallel entry.
- Branch bindings passed 160 comparisons with 32 native entries and two workers; nested scopes passed 69 exact comparisons with 20 native entries. Iterator checks cover list/float32/float64 storage, module replacement of zip/range, and empty/nonempty deleted captures. Scalar math includes rounding/exception-flag probes appended only to its qualification copy, leaving the catalogue output unchanged.
- Quick_Start was compiled from its paired output and matched Python bytes with actual parallel execution. A fresh ordinary shell also loaded and ran that binary successfully.
- A separate 27-observation regression covers deleted/rebound/nonlocal/private cells, partial deletion, defaults, lexical shadowing, dead bindings, late globals and replaced builtins. The readable-source regression also passed editing/rebuilding, native execution and absence of a Python sidecar.
- All generated files have no generated executable source-string baseline, exec, or compile wrapper. The neighboring Python inputs are references, not runtime companions.
- This verifies the stated fixtures and inputs; compilation alone does not validate every runtime input or establish a speedup. Candidate selection and large-workload performance were not remeasured. Cython reflection and frame-sensitive builtin boundaries remain.

Per-file provenance is in [Manifest.json](Manifest.json). Current logs, native binaries, installed-wheel checks and the final report are under `Test_Run/Direct_Scope_Fix_20261119`. The earlier comments-only catalogue had 73 translation passes and five failures; this pass repairs those failures and regenerates all pairs. The previous comments-only performance evidence is not presented as new timing.

Reproduce generation with `python Example/Generate.py` and translation with `python Example/Validate.py`. Runtime fixtures and commands are documented in [Test/README.md](../Test/README.md).

Wheel SHA256: `89afa29eed4dccac689fc959039834a7395058a22041e04c5ee8c7fcb9eaf71c`.
