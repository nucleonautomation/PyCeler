# PyCeler

PyCeler takes a Python file, finds loops that spend time doing arithmetic or updating arrays, and tries compiling them with Cython. For loops whose iterations can run independently, it also tries a parallel version using OpenMP. It checks the results against Python and times the alternatives before choosing which version to use.

## Build from source

Use CPython 3.11 or newer. On Windows x64, install MSVC Build Tools with the C++ toolchain and Windows SDK. On Linux, you’ll need GCC, the Python development headers, and the OpenMP runtime.

From the project root, run:

```sh
python -m pip install -r requirements.txt
python -B Compile.py
```

The build puts the importable package in `Build/Lib/PyCeler`. To use it from another project, add `Build/Lib` to your Python import path.

A PyPI release is planned. Once published, the install command will be `pip install PyCeler`.

## Try it on a loop

The [example module](Test/Numeric_Loops.py) contains two loops. One clears an array by writing zero to each element. Each write is independent, so different threads can clear different parts of the array. The other computes a running sum. Each step needs the value written by the previous step, so those iterations must run in order.

To see what PyCeler finds, run this from the project root:

```sh
python -B Compile.py analyze --input Test/Numeric_Loops.py --rank
```

Analysis reads the Python source without importing it. When you’re ready to optimize a file, install the third-party libraries it uses in the same Python environment as PyCeler. Conversion and compilation can execute the code to check results and measure speed. NumPy is optional for PyCeler itself. For this array example, install it and build the module:

```sh
python -m pip install numpy
python -B Compile.py compile --input Test/Numeric_Loops.py --output Output/Native
```

Then call the compiled function from Python:

```python
import sys
import numpy as np

sys.path.insert(0, "Output/Native")
from Numeric_Loops import Clear_Elements

values = np.arange(8, dtype=np.int32)
Clear_Elements(values)
print(values.tolist())  # [0, 0, 0, 0, 0, 0, 0, 0]
```

The build writes a native extension alongside a selection report. The report shows which implementations were tested and how they performed at different input sizes. A short loop can finish before it’s worth starting extra threads. The compiled module can use different implementations for different sizes and fall back to Python for inputs outside the conditions it checked.

## Python API

| Call | Use it to |
| --- | --- |
| `PyCeler.Analyze(source)` | Find loops, their line numbers, and reasons they might benefit from compilation. |
| `PyCeler.Convert(source, output)` | Generate Cython source you can inspect. |
| `PyCeler.Compile(source, output)` | Build an importable extension for the current platform. |
| `PyCeler.Compile(source, output, Convert=False)` | Compile existing Python or Cython code directly, skipping optimization and timing. |

Inputs can be a file or a source directory. PyCeler writes generated files to a separate output directory. To see the available build options, run `python -B Compile.py compile --help`.

The [test guide](Test/README.md) includes commands for running the suite and benchmarking example workloads. PyCeler is distributed under the [MIT License](LICENSE.md).
