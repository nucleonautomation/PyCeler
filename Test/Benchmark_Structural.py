import importlib.util
import json
import os
import platform
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter_ns
import numpy as Numpy
import Structural_Workloads

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Name] = Module
    Spec.loader.exec_module(Module)
    return Module

def _Copy(Args):
    return tuple(Value.copy() if type(Value) is Numpy.ndarray else Value for Value in Args)

def _Observe(Function, Args):
    Result = Function(*Args)
    State = tuple((Value.dtype.str, Value.shape, Value.tobytes()) if type(Value) is Numpy.ndarray else Value for Value in Args)
    return tuple(Index for Index, Value in enumerate(Args) if Result is Value), State

def _Main():
    Root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Root))
    import PyCeler
    Runs = Root / "Test_Run"
    Runs.mkdir(exist_ok=True)
    Run = Path(tempfile.mkdtemp(prefix="Structural_Benchmark_", dir=Runs))
    os.environ.update(PYCELER_BUILD_DIR=str(Run / "Build"), OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    Source = Root / "Test" / "Structural_Loops.py"
    Names = ("Fused_Maps", "Repeated_Scores", "Local_Values", "Versioned_Reads", "Column_First", "Invariant_Scale", "Temporary_Pipeline")
    Workloads = {Name: dict(File=Path(Structural_Workloads.__file__), Factory=Name) for Name in Names}
    print(Run, flush=True)
    Binary = PyCeler.Compile(Source, Run / "Native", Workloads=Workloads, Elide_Temporaries=True)
    Selection = json.loads(Binary.with_suffix(".selection.json").read_text(encoding="utf-8"))
    for Item in Selection["Items"]:
        if Item["Function"] in Names:
            assert Item["Cases"], Item
            assert any("Optimized" in Case["Timings"] for Case in Item["Cases"]), Item
            assert not any(Status.startswith("invalid") for Case in Item["Cases"] for Status in Case["Validation"].values()), Item
    Native = _Load("Native.Structural_Loops", Binary)
    Reference = _Load("Reference.Structural_Loops", Source)
    Report = dict(Platform=platform.platform(), Python=sys.version, NumPy=Numpy.__version__, OpenMP_Threads=2, Selection=str(Binary.with_suffix(".selection.json")), Cases=[])
    for Name in Names:
        for Case in getattr(Structural_Workloads, Name)():
            if not Case["Holdout"]:
                continue
            Args = Case["Args"]
            Functions = {"Python": getattr(Reference, Name), "PyCeler": getattr(Native, Name)}
            Expected = _Observe(Functions["Python"], _Copy(Args))
            assert _Observe(Functions["PyCeler"], _Copy(Args)) == Expected, (Name, Case["Label"])
            Samples = {Key: [] for Key in Functions}
            for Repeat in range(11):
                Order = ("Python", "PyCeler") if Repeat % 2 else ("PyCeler", "Python")
                for Key in Order:
                    Values = _Copy(Args)
                    Start = perf_counter_ns()
                    Functions[Key](*Values)
                    Duration = perf_counter_ns() - Start
                    if Repeat >= 2:
                        Samples[Key].append(Duration)
            Medians = {Key: statistics.median(Values) for Key, Values in Samples.items()}
            Result = dict(Function=Name, Label=Case["Label"], Size=Args[0].size, Status="valid", Samples_Ns=Samples,
                          Median_Ns=Medians, Speedup=Medians["Python"] / Medians["PyCeler"])
            Report["Cases"].append(Result)
            print(f"{Case['Label']}: {Result['Speedup']:.2f}x", flush=True)
    Result = Run / "Results.json"
    Result.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(Result, flush=True)

if __name__ == "__main__":
    _Main()
