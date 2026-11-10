import argparse
import importlib.util
import json
import os
import platform
import random
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter_ns

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Measure(Modules, Count, Samples):
    Rows = []
    Cases = (("Modulo_Total", (Count, 999983)), ("Signed_Total", (-Count, Count, 7)), ("Reverse_Total", (Count, -Count, -7)))
    Generator = random.Random(20261110)
    for Name, Args in Cases:
        Expected = getattr(Modules["Python"], Name)(*Args)
        Timings = {Variant: [] for Variant in Modules}
        for Variant, Module in Modules.items():
            for Warmup in range(2):
                Actual = getattr(Module, Name)(*Args)
                if type(Actual) is not type(Expected) or Actual != Expected:
                    raise AssertionError((Name, Variant, Actual, Expected))
        for Sample in range(Samples):
            Order = list(Modules)
            Generator.shuffle(Order)
            for Variant in Order:
                Start = perf_counter_ns()
                Actual = getattr(Modules[Variant], Name)(*Args)
                Duration = perf_counter_ns() - Start
                if type(Actual) is not type(Expected) or Actual != Expected:
                    raise AssertionError((Name, Variant, Actual, Expected))
                Timings[Variant].append(Duration)
        Medians = {Variant: statistics.median(Values) for Variant, Values in Timings.items()}
        Team = Modules["OpenMP"]._Pyceler_Parallel_Stats()[1]
        if Team != 2:
            raise AssertionError((Name, "Expected two actual OpenMP workers", Team))
        Serial_Statistics = Modules["Serial"]._Pyceler_Reduction_Stats()
        if Serial_Statistics["Last_Mode"] != "serial" or not Serial_Statistics["Serial_Calls"]:
            raise AssertionError((Name, "Expected interval-proven serial arithmetic", Serial_Statistics))
        Rows.append(dict(Function=Name, Arguments=Args, Result=Expected, Actual_Team=Team,
                         Serial_Contract="Same interval proof and unchecked integer term as OpenMP; sequential accumulation",
                         Timings={Variant: dict(Samples_Ns=Values, Median_Ns=Medians[Variant], Minimum_Ns=min(Values),
                                  CV=statistics.pstdev(Values) / statistics.mean(Values),
                                  Speedup_Vs_Python=Medians["Python"] / Medians[Variant],
                                  Speedup_Vs_Serial=Medians["Serial"] / Medians[Variant]) for Variant, Values in Timings.items()}))
        print(Name + ": " + ", ".join(f"{Variant} {Median / 1000000:.3f} ms" for Variant, Median in Medians.items()), flush=True)
    return Rows

def _Selected(Run, Fixture, Reference):
    import PyCeler
    Source = Run / "Selected_Reduction.py"
    Source.write_text(Fixture.read_text(encoding="utf-8").split("\ndef Signed_Total", 1)[0], encoding="utf-8")
    Binary = PyCeler.Compile(Source, Run / "Selected", OpenMP=True, Tuning=dict(Threads=[2], Budget_Seconds=30),
                            Workloads={"Modulo_Total": dict(File=str(Fixture), Factory="Workloads")})
    Module = _Load(Source.stem, Binary)
    Report = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
    Item, = Report["Items"]
    Checks = []
    for Case in Item["Cases"]:
        Args = tuple(Case["Arguments"])
        Winner = Case["Dispatch_Winner"]
        Statistics = getattr(Module, "_Pyceler_Parallel_Stats", lambda: (0, 0))
        Before = Statistics()[0]
        Baseline_Calls = []
        def _Observe(Frame, Event, Value):
            if Event == "call" and Frame.f_code.co_name == "Modulo_Total" and Frame.f_code.co_filename == Source.name:
                Baseline_Calls.append(Event)
        sys.setprofile(_Observe)
        try:
            Actual = Module.Modulo_Total(*Args)
        finally:
            sys.setprofile(None)
        Expected = Reference.Modulo_Total(*Args)
        Calls, Team = Statistics()
        if type(Actual) is not int or Actual != Expected or bool(Baseline_Calls) != (Winner == "Python"):
            raise AssertionError((Args, Winner, Actual, Expected, Baseline_Calls))
        if Winner.startswith("OpenMP") and (Calls != Before + 1 or Team != 2):
            raise AssertionError((Args, Winner, Calls, Before, Team))
        if not Winner.startswith("OpenMP") and Calls != Before:
            raise AssertionError((Args, Winner, "Unexpected parallel dispatch"))
        Checks.append(dict(Arguments=Args, Winner=Winner, Exact=True, Parallel_Entered=Calls > Before, Actual_Team=Team if Calls > Before else None))
    if not Checks:
        raise AssertionError("Selection produced no validated cases")
    return dict(Binary=str(Binary), Report=str(Binary.with_suffix(".selection.json")), Cases=Checks)

def _Run():
    Parser = argparse.ArgumentParser()
    Parser.add_argument("--iterations", type=int, default=2000000)
    Parser.add_argument("--samples", type=int, default=7)
    Options = Parser.parse_args()
    if not 1 <= Options.iterations <= 100000000 or not 3 <= Options.samples <= 30:
        Parser.error("Use 1..100000000 iterations and 3..30 samples")
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import Cython
    import PyCeler
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Parallel_Reductions_", dir=Runs))
    print("Report directory: " + str(Run), flush=True)
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    Fixture = Root / "Test" / "Parallel_Reductions.py"
    Modules = {"Python": _Load("Original_Reductions", Fixture)}
    for Variant in ("Serial", "OpenMP"):
        Source = Run / (Variant + "_Reductions.py")
        Source.write_bytes(Fixture.read_bytes())
        Binary = PyCeler.Compile(Source, Run / Variant, OpenMP=Variant == "OpenMP", Select=False)
        Modules[Variant] = _Load(Source.stem, Binary)
    Rows = _Measure(Modules, Options.iterations, Options.samples)
    Selected = _Selected(Run, Fixture, Modules["Python"])
    Report = dict(Platform=platform.platform(), CPU=platform.processor(), Python=sys.version, Cython=Cython.__version__,
                  PyCeler=PyCeler.__version__, ABI="3.11", Iterations=Options.iterations, Samples=Options.samples,
                  Timing="Complete calls including guards; builds excluded; interleaved order after two warmups",
                  Numerical_Contract="Exact integer results with proven expression and arbitrary partial-sum bounds", Rows=Rows, Selected_Dispatch=Selected)
    File = Run / "Results.json"
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(File, flush=True)

if __name__ == "__main__":
    _Run()
