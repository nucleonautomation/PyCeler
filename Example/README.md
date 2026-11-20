# PyCeler examples

These are ordinary Python inputs. `Loops` and `Benchmarks` contain only `.py` files to keep the repository small. Generate editable Cython on demand into the ignored `Test_Run/Examples` folder. No PyCeler decorator, special loop syntax, or mandatory type annotation is needed in the input. Each generated `.pyx` contains application code and native support in one file, without requiring a Python sidecar.

Start with [Quick_Start.py](Quick_Start.py) and [Quick_Start.pyx](Quick_Start.pyx). The [catalogue](INDEX.md) lists the preserved full benchmarks and focused fixtures. The full benchmark inputs retain their original sizes; use the small quick start for an initial run. Focused fixtures mostly define functions for caller-supplied inputs. Some deliberately show cases that retain ordinary execution.

All 78 examples passed Cython translation before the generated bulk outputs were removed. The five previously failing scope fixtures are repaired and now live in `Loops`; their native results and expected errors were compared with Python. See the historical [verification](VERIFICATION.md).

From the project root, run the Python quick start:

```powershell
python Example/Quick_Start.py
```

Build its existing `.pyx` and run the compiled module:

```powershell
python -c "from PyCeler import Compile; print(Compile('Example/Quick_Start.pyx', 'Build/Examples/Quick_Start', Convert=False, OpenMP=True))"
python -c "import sys; sys.path.insert(0, 'Build/Examples/Quick_Start'); import Quick_Start"
```

For bulk examples, generate first and use the resulting path under `Test_Run/Examples/Loops` or `Test_Run/Examples/Benchmarks` when compiling. Building requires the compiler environment described in the [project README](../README.md). After editing a generated `.pyx`, keep `Convert=False`; regenerating from `.py` overwrites those edits.

Generation defaults to `Select=False, OpenMP=True`: it exposes eligible serial/parallel candidates without running the full benchmark suite. A candidate is not a measured speedup, and unsupported operations remain visible ordinary code. Runtime guards still check types, ranges, aliases, bindings and safe parallel execution. Source hashes and historical output/validation records remain in [Manifest.json](Manifest.json); `Generated_Present` distinguishes removed outputs from available files.

Generate one example or the whole catalogue; bulk `.pyx` and selection JSON outputs stay outside the source folders:

```powershell
python Example/Generate.py --name Image_Pipeline
python Example/Generate.py
```

To ask PyCeler to validate and measure candidate selection for one example, use `--measured`. This can execute representative candidate workloads and requires a working native compiler:

```powershell
python Example/Generate.py --name Quick_Start --measured
```

Check Python syntax and translate every generated file to C without executing the examples:

```powershell
python Example/Validate.py
```

This translation check is distinct from compiling every example into a native extension or validating every runtime input. The retained test probes in `Test/` perform behavioural comparisons and inspect actual native/worker counters. `VERIFICATION.md` records what was checked for this catalogue.

Run `Generate.py` before validating bulk examples whose outputs have been removed. Use `python Example/Validate.py --name Quick_Start` to check the retained small root example.

The broad math example expands the existing math/cmath/NumPy test corpus into regular function definitions. It demonstrates coverage and retained library-call boundaries; it does not claim that every math operation becomes a native libm call.
