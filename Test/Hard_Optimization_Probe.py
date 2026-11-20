import ast
import builtins
import importlib.util
import json
import math
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns
import numpy as Numpy
# Isolated verification for hard optimization.
def _Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Outcome(Function, Source, Output):
    try:
        return "value", Function(Source, Output) is Output
    except Exception as Error:
        return "error", type(Error).__name__, str(Error)

def _Bits(Array):
    return Numpy.ascontiguousarray(Array).view(Numpy.uint8)

def _Shape(Name, Size):
    if Name.endswith("_Volume"):
        return 4, 8, max(1, Size // 32)
    return (8, max(1, Size // 8)) if "Nested" in Name else (Size,)

def _Input(Name, Size):
    Shape = _Shape(Name, Size)
    Count = math.prod(Shape)
    if Name.startswith("Array_"):
        return (Numpy.arange(Count, dtype=Numpy.int64) % 37 - 18).reshape(Shape)
    return Numpy.linspace(0.05, 20.0, Count, dtype=Numpy.float64).reshape(Shape)

def _Compare(Original, Native, Name, Source, Line, Parallel, Expect_Native=False, Layout="normal"):
    Expected = Numpy.full_like(Source, -12345)
    Actual = Expected.copy()
    Left, Right = Source.copy(), Source.copy()
    if Layout == "alias":
        Expected, Actual = Left, Right
    elif Layout == "readonly":
        Expected.flags.writeable = Actual.flags.writeable = False
    elif Layout == "strided":
        Expected = Numpy.full((*Source.shape[:-1], Source.shape[-1] * 2), -12345, dtype=Source.dtype)[..., ::2]
        Actual = Numpy.full((*Source.shape[:-1], Source.shape[-1] * 2), -12345, dtype=Source.dtype)[..., ::2]
    elif Layout == "mismatch":
        Expected = Numpy.full((*Source.shape[:-1], Source.shape[-1] - 1), -12345, dtype=Source.dtype)
        Actual = Expected.copy()
    elif Layout == "overlap":
        Left_Base = Numpy.concatenate((Source.ravel(), Numpy.zeros(1, dtype=Source.dtype)))
        Right_Base = Left_Base.copy()
        Left, Expected = Left_Base[:-1].reshape(Source.shape), Left_Base[1:].reshape(Source.shape)
        Right, Actual = Right_Base[:-1].reshape(Source.shape), Right_Base[1:].reshape(Source.shape)
    elif Layout == "input_readonly":
        Left.flags.writeable = Right.flags.writeable = False
    Hook = getattr(Native, f"_Pyceler_Fast_{Line}_Stats", None)
    Before = Hook() if Hook else None
    Native._Pyceler_Dispatch_Stats(True, Reset=True)
    with Numpy.errstate(all="raise"):
        Python_Result = _Outcome(getattr(Original, Name), Left, Expected)
        Native_Result = _Outcome(getattr(Native, Name), Right, Actual)
    assert Python_Result == Native_Result, (Name, Layout, Python_Result, Native_Result)
    assert Numpy.array_equal(_Bits(Expected), _Bits(Actual)), (Name, Layout, "output bits differ")
    assert Numpy.array_equal(_Bits(Left), _Bits(Right)), (Name, Layout, "input mutation differs")
    Observation = Native._Pyceler_Dispatch_Stats().get("Execution", {})
    if Expect_Native:
        assert Observation.get("Native_Entry"), (Name, Observation)
        if Name.startswith("Math_"):
            assert Hook is not None, (Name, "missing unboxed kernel")
            After = Hook()
            assert After["Native_Elements"] - Before["Native_Elements"] == Source.size, (Name, Before, After)
            assert After["Team"] == (2 if Parallel else 1), (Name, After)
        if Parallel and Source.nbytes > 65536:
            assert Observation["Actual_Team"] == 2, (Name, Observation)
    return dict(Name=Name, Layout=Layout, Size=Source.size, Outcome=Native_Result, Native=Observation, Elements=(Hook()["Native_Elements"] - Before["Native_Elements"]) if Hook else None)

def _Run():
    Source, Binary, Destination = map(Path, sys.argv[1:4])
    Parallel = sys.argv[4] == "parallel"
    Benchmark = sys.argv[5] == "benchmark"
    Original = _Load(Source, "Original_Hard")
    Native = _Load(Binary, Binary.stem)
    Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Source.read_text()).body if isinstance(Node, ast.FunctionDef)}
    Rows, Timings = [], []
    for Name, Line in Locations.items():
        Values = _Input(Name, 32768)
        Rows.append(_Compare(Original, Native, Name, Values, Line, Parallel, True))
        Rows.append(_Compare(Original, Native, Name, Values, Line, Parallel, True, "input_readonly"))
        for Layout in ("alias", "readonly", "strided", "mismatch", "overlap"):
            Rows.append(_Compare(Original, Native, Name, _Input(Name, 128), Line, Parallel, False, Layout))
        Rows.append(_Compare(Original, Native, Name, _Input(Name, 128).astype(Numpy.float32), Line, Parallel))
        for Empty in (Numpy.empty((0,) * Values.ndim, dtype=Values.dtype), Numpy.empty((*Values.shape[:-1], 0), dtype=Values.dtype)):
            Rows.append(_Compare(Original, Native, Name, Empty, Line, Parallel))
        if Name.startswith("Math_"):
            for Bad in (-1.0, -0.0, math.inf, math.nan):
                Values = _Input(Name, 10000)
                Values.flat[5000] = Bad
                Rows.append(_Compare(Original, Native, Name, Values, Line, Parallel))
            if Values.ndim > 1:
                Values = Numpy.linspace(0.05, 20.0, 10006).reshape((2, 5003) if Values.ndim == 2 else (2, 1, 5003))
                Rows.append(_Compare(Original, Native, Name, Values, Line, Parallel, True))
                Calls = []
                def Tracked_Range(*Arguments):
                    Calls.append(Arguments)
                    return builtins.range(*Arguments)
                Original.range = Native.range = Tracked_Range
                try:
                    Values = _Input(Name, 128)
                    Expected, Actual = Numpy.empty_like(Values), Numpy.empty_like(Values)
                    getattr(Original, Name)(Values, Expected)
                    Expected_Calls = list(Calls)
                    Calls.clear()
                    Before = getattr(Native, f"_Pyceler_Fast_{Line}_Stats")()["Native_Elements"]
                    getattr(Native, Name)(Values, Actual)
                    After = getattr(Native, f"_Pyceler_Fast_{Line}_Stats")()["Native_Elements"]
                    assert Calls == Expected_Calls and Before == After and Numpy.array_equal(_Bits(Expected), _Bits(Actual)), (Name, Calls, Expected_Calls)
                    Rows.append(dict(Name=Name, Layout="rebound_range", Calls=Calls))
                finally:
                    del Original.range
                    del Native.range
        else:
            for Dtype in (Numpy.int32, Numpy.int64):
                Rows.append(_Compare(Original, Native, Name, _Input(Name, 32768).astype(Dtype), Line, Parallel, True))
                Values = _Input(Name, 128).astype(Dtype)
                Values.flat[13] = Numpy.iinfo(Dtype).max
                Rows.append(_Compare(Original, Native, Name, Values, Line, Parallel))
        if Benchmark:
            for Size in (64, 4096, 262144):
                Values = _Input(Name, Size)
                Left, Right = Numpy.empty_like(Values), Numpy.empty_like(Values)
                _Compare(Original, Native, Name, Values, Line, Parallel, True)
                Samples = {"Python": [], "Native": []}
                Native._Pyceler_Dispatch_Stats(False)
                for Round in range(4):
                    Order = [("Python", Original, Left), ("Native", Native, Right)]
                    if Round % 2:
                        Order.reverse()
                    for Label, Module, Output in Order:
                        Hook = getattr(Native, f"_Pyceler_Fast_{Line}_Stats", None)
                        Before = Hook() if Label == "Native" and Hook else None
                        if Label == "Native":
                            Native._Pyceler_Dispatch_Stats(True, Reset=True)
                        Started = perf_counter_ns()
                        getattr(Module, Name)(Values, Output)
                        Duration = perf_counter_ns() - Started
                        if Label == "Native":
                            assert Native._Pyceler_Dispatch_Stats()["Execution"]["Native_Entry"], Name
                            if Hook:
                                After = Hook()
                                assert After["Native_Elements"] - Before["Native_Elements"] == Values.size and After["Team"] == (2 if Parallel else 1), (Name, Before, After)
                        if Round:
                            Samples[Label].append(Duration)
                    assert Numpy.array_equal(_Bits(Left), _Bits(Right)), Name
                Medians = {Label: statistics.median(Sample) for Label, Sample in Samples.items()}
                Timings.append(dict(Function=Name, Elements=Values.size, Samples_Ns=Samples, Median_Ns=Medians, Speedup=Medians["Python"] / Medians["Native"]))
    Report = dict(Parallel=Parallel, Functions=list(Locations), Comparisons=len(Rows), Results=Rows, Benchmarks=Timings)
    Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(dict(Functions=list(Locations), Comparisons=len(Rows), Large_Timings=[Row for Row in Timings if Row["Elements"] == 262144])), flush=True)

if __name__ == "__main__":
    _Run()
