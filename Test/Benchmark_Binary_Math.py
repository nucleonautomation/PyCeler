import argparse
import ast
import hashlib
import json
import os
import platform
import random
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter, perf_counter_ns

Root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Root))
from Test import Benchmark_Math

def _Digest(File):
    return hashlib.sha256(Path(File).read_bytes()).hexdigest()

def _Call(Module, Function, Left, Right, Output, Expected, Line, Variant, Threads, Timed, Eligible):
    import numpy as N
    Before = Benchmark_Math._Statistics(Module, Line) if Variant != "Python" else None
    Started = perf_counter_ns() if Timed else 0
    Result = getattr(Module, Function)(Left, Right, Output)
    Duration = perf_counter_ns() - Started if Timed else 0
    if Result is not Output or not N.array_equal(Output.view(N.uint64), Expected.view(N.uint64)):
        raise AssertionError((Function, Variant, "Output bits or identity differ"))
    if Before is not None:
        After = Benchmark_Math._Statistics(Module, Line)
        Count = len(Left) if Eligible else 0
        if After["Native_Elements"] - Before["Native_Elements"] != Count:
            raise AssertionError((Function, Variant, "Unexpected unboxed element count", Before, After, Count))
        Parallel_Count = Count if Variant == "OpenMP" else 0
        if After["Parallel_Elements"] - Before["Parallel_Elements"] != Parallel_Count:
            raise AssertionError((Function, Variant, "Unexpected parallel element count", Before, After))
        if Eligible and After["Team"] != (Threads if Variant == "OpenMP" else 1):
            raise AssertionError((Function, Variant, "Unexpected actual worker team", After))
    return Duration

def _Measure(Modules, Locations, Sizes, Samples, Threads):
    import numpy as N
    Generator = random.Random(20261112)
    Rows = []
    for Function, Eligible in (("Map_Copysign", True), ("Map_Fmod", True), ("Composed", True), ("Map_Fmod", False)):
        for Size in Sizes:
            Left = N.linspace(0.1, 1.1, Size) if Eligible else N.full(Size, 4.0)
            Right = N.full(Size, 1.7 if Eligible else 2.0)
            Left.flags.writeable = Right.flags.writeable = False
            Input_Hashes = (_Digest_Array(Left), _Digest_Array(Right))
            Expected = N.empty_like(Left)
            getattr(Modules["Python"], Function)(Left, Right, Expected)
            Outputs = {Variant: N.empty_like(Left) for Variant in Modules}
            Values = {Variant: [] for Variant in Modules}
            Observations = {}
            for Variant, Module in Modules.items():
                if Variant != "Python":
                    Module._Pyceler_Dispatch_Stats(True, True)
                try:
                    for Warmup in range(2):
                        _Call(Module, Function, Left, Right, Outputs[Variant], Expected, Locations[Function], Variant, Threads, False, Eligible)
                finally:
                    if Variant != "Python":
                        Observations[Variant] = Module._Pyceler_Dispatch_Stats(False).get("Execution", {})
                if Variant != "Python":
                    Expected_Team = Threads if Eligible and Variant == "OpenMP" else 1
                    Expected_Reason = "native_parallel" if Eligible and Variant == "OpenMP" else "native_serial"
                    if Observations[Variant].get("Native_Entry") is not True or Observations[Variant].get("Actual_Team") != Expected_Team or Observations[Variant].get("Reason") != Expected_Reason:
                        raise AssertionError((Function, Variant, Eligible, Observations[Variant]))
            Orders = []
            for Sample in range(Samples):
                Order = list(Modules)
                Generator.shuffle(Order)
                Orders.append(Order)
                for Variant in Order:
                    Values[Variant].append(_Call(Modules[Variant], Function, Left, Right, Outputs[Variant], Expected, Locations[Function], Variant, Threads, True, Eligible))
            assert Input_Hashes == (_Digest_Array(Left), _Digest_Array(Right))
            Medians = {Variant: statistics.median(Times) for Variant, Times in Values.items()}
            Rows.append(dict(Function=Function, Elements=Size, Case="Finite_Nonzero" if Eligible else "Zero_Remainder_Ordered", Exact_Bits=True, Output_Identity=True,
                             Inputs_Unchanged=True, Native_Elements_Per_Call=Size if Eligible else 0, Actual_Parallel_Team=Threads if Eligible else None,
                             Warmup_Observations=Observations, Sample_Order=Orders,
                             Timings={Variant: dict(Samples_Ns=Times, Median_Ns=Medians[Variant], Minimum_Ns=min(Times),
                                      CV=statistics.pstdev(Times) / statistics.mean(Times), Speedup_Vs_Python=Medians["Python"] / Medians[Variant],
                                      Speedup_Vs_Serial=Medians["Serial"] / Medians[Variant]) for Variant, Times in Values.items()}))
            print(f"{Function} [{Size}, {'unboxed' if Eligible else 'ordered'}]: " + ", ".join(f"{Variant} {Median / 1000000:.6f} ms" for Variant, Median in Medians.items()), flush=True)
    return Rows

def _Digest_Array(Value):
    return hashlib.sha256(Value.tobytes()).hexdigest()

def _Run():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--sizes", nargs="+", type=int, default=[64, 4096, 262144])
    Parser.add_argument("--samples", type=int, default=9)
    Parser.add_argument("--threads", type=int, default=2)
    Parser.add_argument("--expected-build-id", required=True)
    Options = Parser.parse_args()
    if not 3 <= Options.samples <= 31 or not 2 <= Options.threads <= 32 or not Options.sizes or any(Size < 1 or Size > 10000000 for Size in Options.sizes):
        Parser.error("Use 3..31 samples, 2..32 threads and sizes 1..10000000")
    import Cython
    import numpy as N
    import PyCeler
    assert getattr(PyCeler, "__build_id__", None) == Options.expected_build_id
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Binary_Math_Benchmark_", dir=Runs))
    print("Report directory: " + str(Run), flush=True)
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS=str(Options.threads), OMP_DYNAMIC="FALSE")
    Fixture = Root / "Test/Fast_Binary_Loops.py"
    Tree = ast.parse(Fixture.read_text(encoding="utf-8"))
    Tree.body = [Node for Node in Tree.body if isinstance(Node, (ast.Import, ast.ImportFrom)) or isinstance(Node, ast.FunctionDef) and Node.name in {"Map_Copysign", "Map_Fmod", "Composed"}]
    Text = ast.unparse(Tree) + "\n"
    Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Text).body if isinstance(Node, ast.FunctionDef)}
    Reference = Run / "Original_Binary_Math.py"
    Reference.write_text(Text, encoding="utf-8")
    Modules = {"Python": Benchmark_Math._Load(Reference.stem, Reference)}
    Builds = {}
    for Variant in ("Serial", "OpenMP"):
        Source = Run / (Variant + "_Binary_Math.py")
        Source.write_text(Text, encoding="utf-8")
        Started = perf_counter()
        Converted = PyCeler.Convert(Source, Run / (Variant + "_Source"), OpenMP=Variant == "OpenMP", Select=False)
        Binary = PyCeler.Compile(Converted, Run / Variant, Convert=False, OpenMP=Variant == "OpenMP")
        Builds[Variant] = dict(Binary=str(Binary), Binary_SHA256=_Digest(Binary), Generated_Source=str(Converted), Generated_SHA256=_Digest(Converted), Seconds=perf_counter() - Started)
        Modules[Variant] = Benchmark_Math._Load(Source.stem, Binary)
        Modules[Variant]._Pyceler_Dispatch_Stats(False)
    Rows = _Measure(Modules, Locations, sorted(set(Options.sizes)), Options.samples, Options.threads)
    Report = dict(Platform=platform.platform(), Machine=platform.machine(), Python=sys.version, Interpreter=sys.executable,
                  Cython=Cython.__version__, NumPy=N.__version__, PyCeler=PyCeler.__version__, Build_Id=PyCeler.__build_id__,
                  Fixture_SHA256=_Digest(Fixture), Benchmark_SHA256=_Digest(Path(__file__)), Reference_SHA256=_Digest(Reference),
                  Samples=Options.samples, Warmups=2, Threads=Options.threads, Builds=Builds, Selection=False,
                  Timing="Interleaved complete calls including guards, scratch work, commits and ordered continuation; builds, input preparation and verification excluded",
                  Contract="Exact float64 bits and identity on every call; real unboxed counts/teams for eligible inputs; zero unboxed work and ordered native entry for zero remainders. Raw candidates, not selected-dispatch claims.", Rows=Rows)
    File = Run / "Results.json"
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print("Report: " + str(File), flush=True)

if __name__ == "__main__":
    _Run()
