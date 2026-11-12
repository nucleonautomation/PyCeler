import argparse
import ast
import copy
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter, perf_counter_ns
from Benchmark_Math import _Load
from Dynamic_Scalar_Strides_Probe import _Value

def _Source(Fixture):
    Original = next(Node for Node in ast.parse(Fixture.read_text(encoding="utf-8")).body if isinstance(Node, ast.FunctionDef) and Node.name == "Mixed")
    Functions = []
    for Name, Period in (("Dense_Callbacks", 6), ("Sparse_Callbacks", 4096)):
        Function = copy.deepcopy(Original)
        Function.name = Name
        Loop = next(Node for Node in Function.body if isinstance(Node, ast.For))
        Loop.body[1].test.left.right = ast.Constant(value=Period)
        Functions.append(Function)
    return ast.unparse(ast.fix_missing_locations(ast.Module(body=Functions, type_ignores=[]))) + "\n"

def _Hook(Module, Suffix):
    return next(Value for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_") and Name.endswith(Suffix) and callable(Value))

def _Call(Module, Name, Size, Stride, Period, Native, Timed=False, Observe=False):
    Events, Callbacks = [], []
    def Callback(Index, Total, Current_Stride):
        Callbacks.append((Index, Total, Current_Stride))
        return Total + 1, -Current_Stride
    Statistics = _Hook(Module, "Region_Stats") if Native else None
    Dispatch = _Hook(Module, "Dispatch_Stats") if Native else None
    Before = Statistics() if Native else None
    if Dispatch is not None:
        Dispatch(Observe, Reset=True)
    Function = getattr(Module, Name)
    Start = perf_counter_ns() if Timed else 0
    Result = Function(0, Size * Stride, Stride, 17, Events, Callback)
    Duration = perf_counter_ns() - Start if Timed else 0
    Observation = {}
    if Native:
        After = Statistics()
        Interval = Period // math.gcd(Stride, Period)
        Expected_Callbacks = 1 + (Size - 1) // Interval
        Expected_Spans = Expected_Callbacks + ((Size - 1) % Interval != 0)
        if After[0] - Before[0] != Expected_Spans or After[1] != Before[1]:
            raise AssertionError((Name, Size, Stride, "Native span coverage differs", Expected_Spans, Before, After))
        Observation = dict(Native_Spans=After[0] - Before[0], Fallbacks=After[1] - Before[1])
        if Observe:
            Execution = Dispatch().get("Execution", {})
            if Execution.get("Reason") != "native_serial" or Execution.get("Actual_Team") != 1 or Execution.get("Native_Entry") is not True:
                raise AssertionError((Name, "Dynamic spans must enter serial native arithmetic", Execution))
            Observation["Execution"] = Execution
        Dispatch(False)
    return Duration, _Value((Result, Events, Callbacks)), Observation

def _Measure(Modules, Sizes, Samples, Report, Destination):
    Generator = random.Random(20261111)
    for Name, Period in (("Dense_Callbacks", 6), ("Sparse_Callbacks", 4096)):
        for Stride in (1, -1, 2, -3):
            for Size in Sizes:
                Ignored, Expected, Ignored_Observation = _Call(Modules["Python"], Name, Size, Stride, Period, False)
                Timings = {Variant: [] for Variant in Modules}
                Observations = {}
                for Variant, Module in Modules.items():
                    for Warmup in range(2):
                        Ignored, Actual, Observation = _Call(Module, Name, Size, Stride, Period, Variant != "Python", Observe=Variant != "Python")
                        if Actual != Expected:
                            raise AssertionError((Name, Size, Stride, Variant, "Warmup results or event traces differ"))
                        if Observation:
                            Observations[Variant] = Observation
                for Sample in range(Samples):
                    Order = list(Modules)
                    Generator.shuffle(Order)
                    for Variant in Order:
                        Duration, Actual, Observation = _Call(Modules[Variant], Name, Size, Stride, Period, Variant != "Python", Timed=True)
                        if Actual != Expected:
                            raise AssertionError((Name, Size, Stride, Variant, "Timed results or event traces differ"))
                        Timings[Variant].append(Duration)
                Medians = {Variant: statistics.median(Values) for Variant, Values in Timings.items()}
                Row = dict(Function=Name, Iterations=Size, Initial_Stride=Stride, Captured_Range=(0, Size * Stride, Stride), Callback_Period=Period,
                           Callback_Contract="Each callback records its arguments, adds one to Total and reverses the live body Stride; the original range stride stays fixed.",
                           Callback_Count=1 + (Size - 1) // (Period // math.gcd(Stride, Period)), Exact_Values_Types_And_Event_Traces=True,
                           Expected_SHA256=hashlib.sha256(json.dumps(Expected, separators=(",", ":")).encode("utf-8")).hexdigest(), Native_Observations=Observations,
                           Timings={Variant: dict(Samples_Ns=Values, Median_Ns=Medians[Variant], Minimum_Ns=min(Values),
                                    CV=statistics.pstdev(Values) / statistics.mean(Values), Speedup_Vs_Python=Medians["Python"] / Medians[Variant],
                                    Speedup_Vs_Serial=Medians["Serial"] / Medians[Variant]) for Variant, Values in Timings.items()})
                Report["Rows"].append(Row)
                Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
                print(f"{Name} stride={Stride} [{Size}]: " + ", ".join(f"{Variant} {Median / 1000000:.6f} ms" for Variant, Median in Medians.items()), flush=True)

def _Run():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--sizes", nargs="+", type=int, default=[64, 4096, 262144])
    Parser.add_argument("--samples", type=int, default=9)
    Options = Parser.parse_args()
    if not 3 <= Options.samples <= 31 or not Options.sizes or any(Size < 1 or Size > 1000000 for Size in Options.sizes):
        Parser.error("Use 3..31 samples and sizes 1..1000000")
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import Cython
    import PyCeler
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Dynamic_Strides_Benchmark_", dir=Runs))
    Destination = Run / "Results.json"
    print("Report directory: " + str(Run), flush=True)
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    Fixture = Root / "Test" / "Dynamic_Scalar_Strides.py"
    Fixture_Hash = hashlib.sha256(Fixture.read_bytes()).hexdigest()
    Text = _Source(Fixture)
    Source = Run / "Original_Dynamic_Strides.py"
    Source.write_text(Text, encoding="utf-8")
    Modules = {"Python": _Load(Source.stem, Source)}
    Report = dict(Status="running", Platform=platform.platform(), Machine=platform.machine(), CPU=platform.processor(), Python=sys.version,
                  Cython=Cython.__version__, PyCeler=PyCeler.__version__, Build_Id=getattr(PyCeler, "__build_id__", None),
                  Samples=Options.samples, Sizes=sorted(set(Options.sizes)), Source=str(Source), Source_SHA256=hashlib.sha256(Source.read_bytes()).hexdigest(),
                  Fixture=str(Fixture), Fixture_SHA256=Fixture_Hash, Builds={}, Rows=[],
                  Timing="Complete calls include guards, span transitions, arithmetic, callbacks, trace allocation and loop-else handling; input setup, validation and compilation are excluded. Two warmups precede shuffled interleaved samples. Dispatch observation is disabled while timing.",
                  Contract="Raw candidates, not measured-selection claims. Every native call must process the expected count of spans without fallback. Untimed checks require actual serial entry/team one, including the OpenMP-enabled build; dynamic reductions have no parallel proof yet.")
    Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    try:
        for Variant, Parallel in (("Serial", False), ("OpenMP_Enabled_Serial", True)):
            Candidate = Run / (Variant + "_Dynamic_Strides.py")
            Candidate.write_text(Text, encoding="utf-8")
            Started = perf_counter()
            Binary = PyCeler.Compile(Candidate, Run / Variant, Select=False, OpenMP=Parallel)
            Report["Builds"][Variant] = dict(Binary=str(Binary), SHA256=hashlib.sha256(Binary.read_bytes()).hexdigest(), Seconds=perf_counter() - Started)
            Modules[Variant] = _Load(Candidate.stem, Binary)
            Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
        _Measure(Modules, Report["Sizes"], Options.samples, Report, Destination)
        if hashlib.sha256(Fixture.read_bytes()).hexdigest() != Fixture_Hash:
            raise AssertionError("Maintained fixture changed during benchmarking")
        Report["Status"] = "passed"
    except BaseException as Error:
        Report.update(Status="failed", Error=repr(Error))
        raise
    finally:
        Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print("Report: " + str(Destination), flush=True)

if __name__ == "__main__":
    _Run()
