import argparse
import ast
import importlib.util
import json
import os
import platform
import random
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter, perf_counter_ns

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Statistics(Module, Line):
    return getattr(Module, "_Pyceler_Fast_" + str(Line) + "_Stats")()

def _Call(Module, Function, Source, Output, Expected, Line, Variant, Threads, Timed):
    import numpy as N
    Before = _Statistics(Module, Line) if Variant != "Python" else None
    Start = perf_counter_ns() if Timed else 0
    Result = getattr(Module, Function)(Source, Output)
    Duration = perf_counter_ns() - Start if Timed else 0
    if Result is not Output or not N.array_equal(Output.view(N.uint64), Expected.view(N.uint64)):
        raise AssertionError((Function, Variant, "Exact result or output identity mismatch"))
    if Before is not None:
        After = _Statistics(Module, Line)
        if After["Native_Elements"] - Before["Native_Elements"] != len(Source):
            raise AssertionError((Function, Variant, "Unboxed arithmetic did not handle the full input", Before, After))
        if Variant == "OpenMP" and (After["Parallel_Elements"] - Before["Parallel_Elements"] != len(Source) or After["Team"] != Threads):
            raise AssertionError((Function, Variant, "Requested worker team did not execute", After))
        if Variant == "Serial" and (After["Parallel_Elements"] != Before["Parallel_Elements"] or After["Team"] != 1):
            raise AssertionError((Function, Variant, "Serial arithmetic was not observed", After))
    return Duration

def _Measure(Modules, Locations, Sizes, Samples, Threads):
    import numpy as N
    Generator = random.Random(20261111)
    Rows = []
    for Function in ("Map_sin", "Composed", "Map_expm1"):
        for Size in Sizes:
            Source = N.linspace(0.1, 9.0, Size, dtype=N.float64)
            Source.flags.writeable = False
            Expected = N.empty_like(Source)
            getattr(Modules["Python"], Function)(Source, Expected)
            Outputs = {Variant: N.empty_like(Source) for Variant in Modules}
            Values = {Variant: [] for Variant in Modules}
            for Variant, Module in Modules.items():
                for Warmup in range(2):
                    _Call(Module, Function, Source, Outputs[Variant], Expected, Locations[Function], Variant, Threads, False)
            for Sample in range(Samples):
                Order = list(Modules)
                Generator.shuffle(Order)
                for Variant in Order:
                    Values[Variant].append(_Call(Modules[Variant], Function, Source, Outputs[Variant], Expected, Locations[Function], Variant, Threads, True))
            Medians = {Variant: statistics.median(Times) for Variant, Times in Values.items()}
            Rows.append(dict(Function=Function, Elements=Size, Exact_Bits=True, Native_Elements_Per_Call=Size, Actual_Parallel_Team=Threads,
                             Timings={Variant: dict(Samples_Ns=Times, Median_Ns=Medians[Variant], Minimum_Ns=min(Times),
                                      CV=statistics.pstdev(Times) / statistics.mean(Times), Speedup_Vs_Python=Medians["Python"] / Medians[Variant],
                                      Speedup_Vs_Serial=Medians["Serial"] / Medians[Variant]) for Variant, Times in Values.items()}))
            print(Function + f" [{Size}]: " + ", ".join(f"{Variant} {Median / 1000000:.6f} ms" for Variant, Median in Medians.items()), flush=True)
    return Rows

def _Run():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--sizes", nargs="+", type=int, default=[64, 4096, 262144])
    Parser.add_argument("--samples", type=int, default=9)
    Parser.add_argument("--threads", type=int, default=2)
    Options = Parser.parse_args()
    if not 3 <= Options.samples <= 31 or not 2 <= Options.threads <= 32 or not Options.sizes or any(Size < 1 or Size > 10000000 for Size in Options.sizes):
        Parser.error("Use 3..31 samples, 2..32 threads and sizes 1..10000000")
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import Cython
    import numpy as N
    import PyCeler
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Math_Benchmark_", dir=Runs))
    print("Report directory: " + str(Run), flush=True)
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS=str(Options.threads), OMP_DYNAMIC="FALSE")
    Tree = ast.parse((Root / "Test" / "Fast_Math_Loops.py").read_text(encoding="utf-8"))
    Tree.body = [Node for Node in Tree.body if isinstance(Node, (ast.Import, ast.ImportFrom)) or isinstance(Node, ast.FunctionDef) and Node.name in {"Map_sin", "Composed", "Map_expm1"}]
    Text = ast.unparse(Tree) + "\n"
    Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef)}
    Reference = Run / "Original_Math.py"
    Reference.write_text(Text, encoding="utf-8")
    Modules = {"Python": _Load("Original_Math", Reference)}
    Builds = {}
    for Variant in ("Serial", "OpenMP"):
        Source = Run / (Variant + "_Math.py")
        Source.write_text(Text, encoding="utf-8")
        Started = perf_counter()
        Binary = PyCeler.Compile(Source, Run / Variant, OpenMP=Variant == "OpenMP", Select=False)
        Builds[Variant] = dict(Binary=str(Binary), Seconds=perf_counter() - Started)
        Modules[Variant] = _Load(Source.stem, Binary)
        Modules[Variant]._Pyceler_Dispatch_Stats(False)
    Rows = _Measure(Modules, Locations, sorted(set(Options.sizes)), Options.samples, Options.threads)
    Report = dict(Platform=platform.platform(), Machine=platform.machine(), CPU=platform.processor(), Python=sys.version,
                  Cython=Cython.__version__, NumPy=N.__version__, PyCeler=PyCeler.__version__, Build_Id=getattr(PyCeler, "__build_id__", None),
                  Samples=Options.samples, Threads=Options.threads, Builds=Builds,
                  Timing="Complete calls including guards, domain preflight, library calls, writes and chunk checkpoints; input/output preparation and builds excluded; two warmups and shuffled interleaved samples",
                  Contract="Exact float64 output bits; every timed native call verifies unboxed element counters and actual worker team. These are raw candidate comparisons, not measured-selection dispatch claims.", Rows=Rows)
    File = Run / "Results.json"
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print("Report: " + str(File), flush=True)

if __name__ == "__main__":
    _Run()
