import hashlib
import importlib.util
import json
import os
import random
import statistics
import sys
import warnings
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from time import perf_counter_ns
import numpy as Numpy
from Survey_Source import _Filters

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Equal(Expected, Actual, Path_Name):
    if type(Expected) is not type(Actual):
        raise AssertionError(f"{Path_Name}: {type(Expected)} differs from {type(Actual)}")
    if isinstance(Expected, Numpy.ndarray):
        if Expected.dtype != Actual.dtype or Expected.shape != Actual.shape or Expected.tobytes() != Actual.tobytes():
            raise AssertionError(f"{Path_Name}: array dtype, shape or content differs")
    elif isinstance(Expected, dict):
        if list(Expected) != list(Actual):
            raise AssertionError(f"{Path_Name}: dictionary keys or order differ")
        for Key in Expected:
            _Equal(Expected[Key], Actual[Key], f"{Path_Name}.{Key}")
    elif isinstance(Expected, (list, tuple)):
        if len(Expected) != len(Actual):
            raise AssertionError(f"{Path_Name}: length differs")
        for Index, (Left, Right) in enumerate(zip(Expected, Actual)):
            _Equal(Left, Right, f"{Path_Name}[{Index}]")
    elif Expected != Actual:
        raise AssertionError(f"{Path_Name}: {Expected!r} != {Actual!r}")

def _Observe(Function, Args):
    with warnings.catch_warnings(record=True) as Captured:
        warnings.simplefilter("always")
        try:
            Result = Function(*Args)
        except Exception as Error:
            Outcome = ("raise", type(Error), Error.args)
        else:
            Outcome = ("return", Result, tuple(Index for Index, Value in enumerate(Args) if Result is Value))
    return Outcome, Args, [(Warning.category, str(Warning.message)) for Warning in Captured]

def _Check(Modules, Name, Make, Label, Expected_Error=None):
    Expected = _Observe(getattr(Modules["Python"], Name), Make())
    for Kind, Module in Modules.items():
        if Kind != "Python":
            Actual = _Observe(getattr(Module, Name), Make())
            _Equal(Expected, Actual, f"{Kind} {Label}")
    if Expected_Error is None and Expected[0][0] != "return":
        raise AssertionError(f"{Label}: unexpected exception {Expected[0]}")
    if Expected_Error is not None and Expected[0][:2] != ("raise", Expected_Error):
        raise AssertionError(f"{Label}: expected {Expected_Error}")

def _Check_Filters(Modules):
    Random = Numpy.random.default_rng(6201)
    Frame = Random.integers(-50, 51, (15, 21), dtype=Numpy.int32)[:, ::2]
    Valid = Random.random(Frame.shape) > 0.06
    Missing = -(1 << 50)
    Shapes = ((Frame, Valid), (Frame[:2, :1], Valid[:2, :1]))
    Count = 0
    for Name, Weights, Divisor in _Filters():
        for Data, Mask in Shapes:
            Rows, Columns = Data.shape
            Height, Width = len(Weights), len(Weights[0])
            Inner_Rows, Inner_Columns = Rows - Height + 1, Columns - Width + 1
            Expected = Numpy.full(Data.shape, Missing, dtype=Numpy.int64)
            if Inner_Rows > 0 and Inner_Columns > 0:
                Total = Numpy.zeros((Inner_Rows, Inner_Columns), dtype=Numpy.int64)
                Present = Numpy.ones(Total.shape, dtype=bool)
                for Y, Row in enumerate(Weights):
                    for X, Weight in enumerate(Row):
                        if Weight:
                            Present &= Mask[Y:Y + Inner_Rows, X:X + Inner_Columns]
                            Total += Weight * Data[Y:Y + Inner_Rows, X:X + Inner_Columns].astype(Numpy.int64)
                Center = Expected[Height // 2:Height // 2 + Inner_Rows, Width // 2:Width // 2 + Inner_Columns]
                Center[Present] = Total[Present] // Divisor
            for Module in Modules.values():
                _Equal(Expected, getattr(Module, Name)(Data, Mask, Missing), Name)
            Count += 1
    return Count

def _Check_Constant_Survey(Modules):
    Shape = (2, 7, 8)
    for Kind, Module in Modules.items():
        Volume = Numpy.full(Shape, 10, dtype=Numpy.int32)
        Survey = Module.Process_Survey(Volume, 10, 2, 1)
        _Equal(Numpy.ones(Shape, dtype=Numpy.int32), Survey["Marked"], Kind)
        _Equal(Numpy.full(Shape[1:], 12, dtype=Numpy.int32), Survey["Peak"], Kind)
        _Equal(Numpy.arange(1, 9, dtype=Numpy.int64) * 14, Survey["Cumulative"], Kind)
        _Equal([(56, 30, (0, 0, 6, 7))], Survey["Regions"], Kind)
        _Equal({1: 56}, Survey["Histogram"], Kind)
        _Equal([12] * 8, Survey["Envelope"], Kind)
        _Equal(364, Survey["Scan_Score"], Kind)
        _Equal(Numpy.full(Shape, 10, dtype=Numpy.int32), Volume, Kind)

def _Edges(Modules):
    def _Aliased():
        Values = Numpy.arange(4097, dtype=Numpy.int32)
        return Values[:-1].reshape(2, 2048), Values[1:].reshape(2, 2048), 1
    def _Read_Only():
        Values = Numpy.arange(4096, dtype=Numpy.int32).reshape(2, 2048)
        Output = Numpy.empty_like(Values)
        Output.fill(-7)
        Output.flags.writeable = False
        return Values, Output, 3
    Cases = (
        ("list clear", "Clear_Profile", lambda: ([3, 7, -2],), None),
        ("empty clear", "Clear_Profile", lambda: (Numpy.empty(0, dtype=Numpy.int64),), None),
        ("prefix dependence", "Prefix_Profile", lambda: ([9, 2, -3, 7],), None),
        ("shifted overlapping views", "Calibrate_Grid", _Aliased, None),
        ("read-only output", "Calibrate_Grid", _Read_Only, ValueError),
        ("error after partial write", "Calibrate_Grid", lambda: (Numpy.arange(4098).reshape(2, 2049), Numpy.full((2, 2048), -8), 4), IndexError),
        ("overflow warning", "Calibrate_Grid", lambda: (Numpy.full((1, 2600), 2**63 - 1, dtype=Numpy.int64), Numpy.zeros((1, 2600), dtype=Numpy.int64), 1), None),
        ("unsupported dtype", "Mark_Volume", lambda: (Numpy.ones((3, 31, 33), dtype=Numpy.uint16), Numpy.zeros((3, 31, 33), dtype=Numpy.uint16), 1), None),
        ("arbitrary precision empty range", "Count_Scan_Positions", lambda: (-(2**75), 7), None),
        ("invalid stride", "Process_Survey", lambda: (Numpy.zeros((2, 3, 4), dtype=Numpy.int32), 3, 2, 0), ValueError),
        ("invalid depth", "Process_Survey", lambda: (Numpy.zeros((1, 3, 4), dtype=Numpy.int32), 3, 2, 1), ValueError),
        ("invalid stencil mask", "Sobel_East", lambda: (Numpy.zeros((3, 3)), Numpy.ones((2, 3), dtype=bool), -1), ValueError),
    )
    for Label, Name, Make, Error in Cases:
        _Check(Modules, Name, Make, Label, Error)
    return [Label for Label, Name, Make, Error in Cases]

def _Workloads(Shape):
    Rows, Columns = Shape[1:]
    Volume = Numpy.random.default_rng(9241).integers(-60, 61, Shape, dtype=Numpy.int32)
    Volume[0, ::11, ::5] = -128
    Volume.flags.writeable = False
    Frame = Volume[0]
    Mask = Frame != -128
    Mask.flags.writeable = False
    def _Buffer(Values):
        return Numpy.full_like(Values, -9)
    return (
        ("Count_Scan_Positions", lambda: (Rows, Columns)),
        ("Clear_Profile", lambda: (Numpy.full(Rows * Columns, 7, dtype=Numpy.int64),)),
        ("Calibrate_Grid", lambda: (Frame, _Buffer(Frame), 7)),
        ("Select_Peaks", lambda: (Frame, Volume[-1], _Buffer(Frame))),
        ("Mark_Volume", lambda: (Volume, _Buffer(Volume), 13)),
        ("Prefix_Profile", lambda: (Numpy.ones(Columns, dtype=Numpy.int64),)),
        ("Sobel_East", lambda: (Frame, Mask, -(1 << 50))),
        ("Process_Survey", lambda: (Volume, 13, 7, 4)),
    )

def _Sample(Function, Make, Calls):
    Inputs = [Make() for Index in range(Calls)]
    Start = perf_counter_ns()
    for Args in Inputs:
        Function(*Args)
    return (perf_counter_ns() - Start) / Calls

def _Dispatch(Module, Item, Make, Filename):
    Args = Make()
    if Item["Kind"] == "scalar":
        Key, Work = "int", 1
        for Index in Item["Size_Arguments"]:
            Work *= Args[Index]
    else:
        Output = Args[Item["Destination"]]
        Key, Work = Output.dtype.str, Output.size
    Band = max((Case for Case in Item["Cases"] if Case["Key"] == Key and Case["Size"] <= Work),
               key=lambda Case: Case["Size"], default=None)
    Selected = Band["Winner"] if Band else "Python"
    Calls = []
    def _Track(Frame, Event, Value):
        if Event == "call" and Frame.f_code.co_filename == Filename and Frame.f_code.co_name == Item["Function"]:
            Calls.append(Event)
    Previous = sys.getprofile()
    sys.setprofile(_Track)
    try:
        getattr(Module, Item["Function"])(*Args)
    finally:
        sys.setprofile(Previous)
    if bool(Calls) != (Selected == "Python"):
        raise AssertionError(f"Unexpected baseline dispatch for {Item['Function']} at {Work} ({Selected})")
    return dict(Selected=Selected, Band=Band["Size"] if Band else None, Python_Fallback=bool(Calls))

def _Measure(Modules, Name, Make, Shape, Size):
    Functions = {Kind: getattr(Module, Name) for Kind, Module in Modules.items()}
    _Check(Modules, Name, Make, f"{Name} {Size}")
    Calls = {}
    Samples = {Kind: [] for Kind in Functions}
    for Kind, Function in Functions.items():
        _Sample(Function, Make, 1)
        Warm = _Sample(Function, Make, 1)
        Calls[Kind] = min(32, max(1, round(3000000 / max(1, Warm))))
    Shuffle = random.Random(514)
    for Round in range(9):
        Order = list(Functions)
        Shuffle.shuffle(Order)
        for Kind in Order:
            Samples[Kind].append(_Sample(Functions[Kind], Make, Calls[Kind]))
    Times = {Kind: dict(Median_ms=statistics.median(Values) / 1e6, Min_ms=min(Values) / 1e6,
                        CV=statistics.pstdev(Values) / statistics.mean(Values), Calls_Per_Batch=Calls[Kind], Samples_ns=Values)
             for Kind, Values in Samples.items()}
    Speedup = Times["Python"]["Median_ms"] / Times["Compiled"]["Median_ms"]
    return dict(Function=Name, Size=Size, Volume_Shape=Shape, Times=Times, Speedup=Speedup,
                Speedup_Vs_Plain_Cython=Times["Plain_Cython"]["Median_ms"] / Times["Compiled"]["Median_ms"])

def _Stage_Profile(Modules):
    Shape = (5, 127, 211)
    Make = dict(_Workloads(Shape))["Process_Survey"]
    Stages = ("Count_Scan_Positions", "Calibrate_Grid", "Clear_Profile", "Select_Peaks", "Mark_Volume", "Prefix_Profile",
              "_Components", "_Histogram", "_Rolling_Maximum")
    Captured = {Kind: Counter() for Kind in Modules}
    Samples = {Kind: [] for Kind in Modules}
    def _Track(Function, Stage, Counter_Ns):
        def _Call(*Args):
            Start = perf_counter_ns()
            Result = Function(*Args)
            Counter_Ns[Stage] += perf_counter_ns() - Start
            return Result
        return _Call
    with ExitStack() as Stack:
        for Kind, Module in Modules.items():
            for Stage in Stages:
                Stack.enter_context(patch.object(Module, Stage, _Track(getattr(Module, Stage), Stage, Captured[Kind])))
            Bank = tuple((Name, _Track(Function, "Neighborhood_Filters", Captured[Kind])) for Name, Function in Module.Filter_Bank)
            Stack.enter_context(patch.object(Module, "Filter_Bank", Bank))
            Module.Process_Survey(*Make())
        Shuffle = random.Random(407)
        for Round in range(7):
            Order = list(Modules)
            Shuffle.shuffle(Order)
            for Kind in Order:
                Captured[Kind].clear()
                Args = Make()
                Start = perf_counter_ns()
                Modules[Kind].Process_Survey(*Args)
                Total = perf_counter_ns() - Start
                Parts = dict(Captured[Kind])
                Parts["Other"] = Total - sum(Parts.values())
                Parts["Total"] = Total
                Samples[Kind].append(Parts)
    Result = {}
    for Kind, Values in Samples.items():
        Medians = {Key: statistics.median(Sample[Key] for Sample in Values) / 1e6 for Key in Values[0]}
        Share = statistics.median(Sample["Neighborhood_Filters"] / Sample["Total"] for Sample in Values)
        Result[Kind] = dict(Medians_ms=Medians, Filter_Fraction=Share, Samples_ns=Values)
    return Result

def Verify_Survey(Run):
    os.environ.update(OMP_NUM_THREADS="2", OMP_DYNAMIC="FALSE")
    File = Run / "Results.json"
    Report = json.loads(File.read_text(encoding="utf-8"))
    Source = Run / Report["Source"]
    if hashlib.sha256(Source.read_bytes()).hexdigest() != Report["SHA256"]:
        raise AssertionError("Source checksum differs from the analyzed input")
    Plain = Run / Report["Plain_Binary"]
    Modules = {"Python": _Load("Reference_Survey", Source), "Plain_Cython": _Load(Plain.stem, Plain), "Compiled": _Load(Source.stem, Run / Report["Binary"])}
    Selection = json.loads((Run / Report["Binary"]).with_suffix(".selection.json").read_text(encoding="utf-8"))
    Items = {Item["Function"]: Item for Item in Selection["Items"]}
    _Check_Constant_Survey(Modules)
    Report["Verification"] = dict(Constant_Survey=True, Oracle_Filter_Cases=_Check_Filters(Modules), Edge_Cases=_Edges(Modules), Workload_Cases=0)
    Report["Timings"] = []
    for Size, Shape in (("Small", (2, 9, 11)), ("Medium", (3, 43, 67)), ("Large", (5, 127, 211))):
        for Name, Make in _Workloads(Shape):
            Row = _Measure(Modules, Name, Make, Shape, Size)
            if Name in Items:
                Row["Dispatch"] = _Dispatch(Modules["Compiled"], Items[Name], Make, Source.name)
            Report["Timings"].append(Row)
            Report["Verification"]["Workload_Cases"] += 1
            print(f"{Size:6} {Name:22} {Row['Times']['Python']['Median_ms']:9.3f} ms -> {Row['Times']['Compiled']['Median_ms']:9.3f} ms  {Row['Speedup']:.2f}x", flush=True)
    Report["Large_Stage_Profile"] = _Stage_Profile(Modules)
    File.write_text(json.dumps(Report, indent=2), encoding="utf-8")

if __name__ == "__main__":
    Verify_Survey(Path(sys.argv[1]).resolve())
