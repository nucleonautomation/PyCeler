import ast
import importlib.util
import signal
from concurrent.futures import ThreadPoolExecutor
import json
import math
import sys
from pathlib import Path
import numpy as N

def _Load(Name, Path):
    Spec = importlib.util.spec_from_file_location(Name, Path)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

Native = _Load("Fast_Math_Loops", Path(sys.argv[1]))
Original = _Load("Fast_Math_Reference", Path(sys.argv[2]))
Parallel = sys.argv[3] == "parallel"
Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Path(sys.argv[2]).read_text()).body if isinstance(Node, ast.FunctionDef)}

def _Stats(Name):
    return getattr(Native, "_Pyceler_Fast_" + str(Locations[Name]) + "_Stats")()
Names = sorted(Name for Name in vars(Original) if Name.startswith("Map_") and not Name.endswith("_Continue")) + ["Composed", "Aliased"]
Comparisons = 0
Native_Functions = set()
Parallel_Functions = set()

def _Outcome(Function, Source, Output, Threads=None):
    try:
        Result = Function(Source, Output) if Threads is None else Function(Source, Output)
        return "value", Result is Output
    except Exception as Error:
        return "error", type(Error).__name__, Error.args

def _Compare(Name, Values, Threads=False, Expected_Native=None):
    global Comparisons
    Source = N.array(Values, dtype=N.float64)
    Expected = N.full(Source.shape, -12345.0, dtype=N.float64)
    Actual = Expected.copy()
    Before = _Stats(Name)
    Python_Result = _Outcome(getattr(Original, Name), Source, Expected)
    Native_Result = _Outcome(getattr(Native, Name), Source, Actual, Threads)
    After = _Stats(Name)
    assert Python_Result == Native_Result, (Name, Python_Result, Native_Result)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64)), (Name, Source[N.flatnonzero(Expected.view(N.uint64) != Actual.view(N.uint64))[:5]], Expected[N.flatnonzero(Expected.view(N.uint64) != Actual.view(N.uint64))[:5]], Actual[N.flatnonzero(Expected.view(N.uint64) != Actual.view(N.uint64))[:5]])
    Entered = After["Native_Elements"] - Before["Native_Elements"]
    if Expected_Native is not None:
        assert Entered == Expected_Native, (Name, Entered, Expected_Native, After)
    if Entered:
        Native_Functions.add(Name)
    if After["Parallel_Elements"] > Before["Parallel_Elements"]:
        Parallel_Functions.add(Name)
        assert After["Team"] == 2, (Name, After)
    Comparisons += 1

def _Status_Compare(Name, Values, Expected_Native):
    global Comparisons
    Source = N.array(Values, dtype=N.float64)
    Expected = N.full(Source.shape, -12345.0)
    Actual = Expected.copy()
    Before = _Stats(Name)["Native_Elements"]
    Native._Test_Floating_Status(True)
    Python_Result = _Outcome(getattr(Original, Name), Source, Expected)
    Expected_Status = Native._Test_Floating_Status(True)
    Native_Result = _Outcome(getattr(Native, Name), Source, Actual)
    Actual_Status = Native._Test_Floating_Status()
    assert Python_Result == Native_Result, (Name, Python_Result, Native_Result)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64)), Name
    assert Expected_Status == Actual_Status, (Name, Expected_Status, Actual_Status)
    assert _Stats(Name)["Native_Elements"] - Before == Expected_Native
    Comparisons += 1

for Name in Names:
    Function = Name.removeprefix("Map_")
    if Function in ("acos", "asin", "atanh"):
        Values = N.linspace(-0.9, 0.9, 10001)
    elif Function == "acosh":
        Values = N.linspace(1.0, 9.0, 10001)
    elif Function in ("log", "log10", "sqrt", "Composed"):
        Values = N.linspace(0.01, 9.0, 10001)
    elif Function == "log1p":
        Values = N.linspace(-0.9, 9.0, 10001)
    else:
        Values = N.linspace(-9.0, 9.0, 10001)
    _Compare(Name, Values, False, len(Values))
    _Compare(Name, Values, Parallel, len(Values))

for Name, Value in (("Map_sqrt", -1.0), ("Map_log", 0.0), ("Map_log1p", -1.0), ("Map_acos", 2.0), ("Map_exp", 1000.0), ("Map_sin", math.inf)):
    Values = N.ones(10000)
    Values[5000] = Value
    _Compare(Name, Values, False, 4096)
    _Compare(Name, Values, True, 4096)

for Name in Names:
    _Compare(Name, (0.0, -0.0, math.nan, math.inf, -math.inf), False, 0)
    _Compare(Name, (), True, 0)

Native._Test_Allocation(True)
try:
    _Compare("Composed", N.linspace(0.01, 9.0, 8195), Parallel, 0)
finally:
    Native._Test_Allocation(False)
_Status_Compare("Map_sin", [0.1, 0.2, 0.3], 3)
_Status_Compare("Map_exp2", N.full(8195, -1074.0), 8195)
for Name, Bad in (("Map_sqrt", -1.0), ("Map_exp", 1000.0), ("Map_log", 0.0)):
    Values = N.ones(8195)
    Values[5000] = Bad
    _Status_Compare(Name, Values, 4096)

for Source in (N.linspace(0.1, 9.0, 100).astype(N.float32), N.linspace(0.1, 9.0, 200)[::2]):
    Expected, Actual = N.zeros(len(Source)), N.zeros(len(Source))
    Before = _Stats("Map_sin")["Native_Elements"]
    Original.Map_sin(Source, Expected)
    Native.Map_sin(Source, Actual)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
    assert _Stats("Map_sin")["Native_Elements"] == Before
    Comparisons += 1

Expected = N.linspace(0.1, 9.0, 200)
Actual = Expected.copy()
Before = _Stats("Map_sin")["Native_Elements"]
Original.Map_sin(Expected[:-1], Expected[1:])
Native.Map_sin(Actual[:-1], Actual[1:])
assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
assert _Stats("Map_sin")["Native_Elements"] == Before
Comparisons += 1

class _Replacement:
    def __init__(self):
        self._Calls = []
    def sin(self, Value):
        self._Calls.append(float(Value))
        return float(Value) + 1.0

Replacement = _Replacement()
Native.M = Replacement
Expected = N.arange(30, dtype=N.float64) + 1.0
Actual = N.zeros(30)
Before = _Stats("Map_sin")["Native_Elements"]
Native.Map_sin(N.arange(30, dtype=N.float64), Actual)
assert N.array_equal(Expected, Actual)
assert Replacement._Calls == list(N.arange(30, dtype=N.float64))
assert _Stats("Map_sin")["Native_Elements"] == Before
Native.M = math
Comparisons += 1
assert len(Native_Functions) == 26, Native_Functions
assert len(Parallel_Functions) == (26 if Parallel else 0), Parallel_Functions

Smallest = float.fromhex("0x0.0000000000001p-1022")
Largest = sys.float_info.max
Near_One = (math.nextafter(1.0, 0.0), 1.0, math.nextafter(1.0, math.inf))
Boundaries = {
    "sqrt": [0.0, Smallest, sys.float_info.min, *Near_One, Largest],
    "cbrt": [-Largest, -sys.float_info.min, -Smallest, 0.0, Smallest, sys.float_info.min, Largest],
    "log": [Smallest, sys.float_info.min, *Near_One, Largest],
    "log10": [Smallest, sys.float_info.min, *Near_One, Largest],
    "log1p": [math.nextafter(-1.0, 0.0), -Smallest, 0.0, Smallest, *Near_One, Largest],
    "acos": [-1.0, math.nextafter(-1.0, 0.0), -Smallest, 0.0, Smallest, math.nextafter(1.0, 0.0), 1.0],
    "asin": [-1.0, math.nextafter(-1.0, 0.0), -Smallest, 0.0, Smallest, math.nextafter(1.0, 0.0), 1.0],
    "atanh": [math.nextafter(-1.0, 0.0), -Smallest, 0.0, Smallest, math.nextafter(1.0, 0.0)],
    "acosh": [1.0, math.nextafter(1.0, math.inf), 2.0, Largest],
    "exp": [-1000.0, -745.0, -Smallest, 0.0, Smallest, 709.0],
    "exp2": [-1100.0, -1074.0, -Smallest, 0.0, Smallest, 1023.0],
    "expm1": [-1000.0, -745.0, -Smallest, 0.0, Smallest, 709.0],
    "sinh": [-709.0, -Smallest, 0.0, Smallest, 709.0],
    "cosh": [-709.0, -Smallest, 0.0, Smallest, 709.0],
}
for Name in Names:
    if not Name.startswith("Map_"):
        continue
    Function = Name.removeprefix("Map_")
    Values = Boundaries.get(Function, [-Largest, -1.0, -Smallest, 0.0, Smallest, 1.0, Largest])
    _Compare(Name, Values, Parallel, len(Values))

Values = N.linspace(0.1, 9.0, 10001)
Before = _Stats("Map_sin")["Native_Elements"]
with ThreadPoolExecutor(max_workers=1) as Pool:
    Actual = Pool.submit(Native.Map_sin, Values, N.zeros_like(Values)).result()
assert N.array_equal(Actual.view(N.uint64), N.array([math.sin(Value) for Value in Values]).view(N.uint64))
assert _Stats("Map_sin")["Native_Elements"] == Before
Comparisons += 1
Old_Handler = signal.getsignal(signal.SIGINT)
def _Observer(Number, Frame):
    return None
try:
    signal.signal(signal.SIGINT, _Observer)
    _Compare("Map_sin", Values, Parallel, 0)
finally:
    signal.signal(signal.SIGINT, Old_Handler)

Native.Wave = math.cos
Actual = N.zeros_like(Values)
Before = _Stats("Aliased")["Native_Elements"]
Native.Aliased(Values, Actual)
assert N.array_equal(Actual.view(N.uint64), N.array([math.cos(Value) for Value in Values]).view(N.uint64))
assert _Stats("Aliased")["Native_Elements"] == Before
Native.Wave = math.sin
Comparisons += 1
Previous = Native._Test_Rounding(True)
try:
    _Compare("Map_sin", Values, Parallel, 0)
finally:
    Native._Test_Restore_Rounding(Previous)
if Parallel:
    Previous = Native._Test_Rounding(False)
    try:
        Native._Test_Worker_Rounding(True)
        Native._Test_Rounding(False)
        Modes = Native._Test_Worker_Modes()
        assert Modes[0] != Modes[1], Modes
        _Compare("Map_sin", Values, True, len(Values))
        assert Native._Test_Worker_Modes() == Modes
    finally:
        Native._Test_Worker_Rounding(False)
        Native._Test_Restore_Rounding(Previous)
    Controls = Native._Test_Worker_Controls()
    if Controls is not None:
        try:
            Native._Test_Worker_Flush()
            Changed = Native._Test_Worker_Controls()
            assert Changed[1] & 0x8040 == 0x8040, Changed
            _Compare("Map_exp2", N.full(8192, -1074.0), True, 8192)
            After = Native._Test_Worker_Controls()
            assert After[1] == Changed[1], (Changed, After)
        finally:
            Native._Test_Worker_Restore_Controls(*Controls)
sys.path.insert(0, sys.argv[4])
from PyCeler.Selection_Worker import _Observe
Observation = {}
Before = _Stats("Map_sin")["Native_Elements"]
Outcome, Fallback = _Observe(Native.Map_sin, (Values, N.zeros_like(Values)), "Map_sin", Observation)
assert not Fallback and Observation["Native_Entry"] and Observation["Actual_Team"] == (2 if Parallel else 1), Observation
assert _Stats("Map_sin")["Native_Elements"] - Before == len(Values)
Before = _Stats("Map_sin")["Native_Elements"]
Fallback_Observation = {}
Outcome, Fallback = _Observe(Native.Map_sin, ([0.1, 0.2], [0.0, 0.0]), "Map_sin", Fallback_Observation)
assert Fallback and not Fallback_Observation["Native_Entry"] and Fallback_Observation["Actual_Mode"] == "python_fallback", Fallback_Observation
assert _Stats("Map_sin")["Native_Elements"] == Before
Comparisons += 2
Slice_Teams = []
if Parallel:
    Previous_Settings = Native._Test_Thread_Settings(3, 0)
    try:
        for Requested, Dynamic in ((3, 0), (32, 1)):
            Native._Test_Thread_Settings(Requested, Dynamic)
            for Size in (1, 3, 63, 4095, 4097, 8195):
                Source = N.linspace(0.01, 9.0, Size)
                Expected, Actual = N.empty_like(Source), N.empty_like(Source)
                Before = _Stats("Map_sin")
                Original.Map_sin(Source, Expected)
                Native.Map_sin(Source, Actual)
                After = _Stats("Map_sin")
                assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64)), (Requested, Dynamic, Size)
                assert After["Native_Elements"] - Before["Native_Elements"] == Size, After
                assert After["Parallel_Elements"] - Before["Parallel_Elements"] == Size, After
                assert 1 <= After["Team"] <= Requested, After
                Slice_Teams.append(dict(Requested=Requested, Dynamic=Dynamic, Elements=Size, Actual=After["Team"]))
                Comparisons += 1
    finally:
        Native._Test_Thread_Settings(*Previous_Settings)
print(json.dumps(dict(Comparisons=Comparisons, Native_Functions=sorted(Native_Functions), Parallel_Functions=sorted(Parallel_Functions), Slice_Teams=Slice_Teams)))
