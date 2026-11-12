import ast
import importlib.util
import json
import math
import signal
import sys
import sysconfig
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as N

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

Original = _Load("Fast_Erf_Reference", Path(sys.argv[2]))
Parallel = sys.argv[3] == "parallel"
Disabled = sys.argv[4] == "disabled"
Poisoned = sys.argv[4] == "poisoned"
Actual_Version = sys.version_info
Saved_Config = sysconfig.get_config_var
try:
    if Poisoned:
        sys.version_info = (3, 14, 8, "final", 0) if Actual_Version[:2] == (3, 11) else (3, 11, 9, "final", 0)
        sysconfig.get_config_var = lambda Name: 1 if Name in {"HAVE_ERF", "HAVE_ERFC"} else Saved_Config(Name)
    Native = _Load("Fast_Erf_Loops", Path(sys.argv[1]))
finally:
    sys.version_info = Actual_Version
    sysconfig.get_config_var = Saved_Config
Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Path(sys.argv[2]).read_text()).body if isinstance(Node, ast.FunctionDef)}
Backend = Native._Test_Erf_Backend()
assert Backend == (Actual_Version[:2] in ((3, 12), (3, 13), (3, 14)) and not Disabled), (Actual_Version, Backend, Poisoned)
Comparisons = 0
Native_Functions = set()
Parallel_Functions = set()

def _Stats(Name):
    return getattr(Native, "_Pyceler_Fast_" + str(Locations[Name]) + "_Stats")()

def _Outcome(Function, Source, Output):
    try:
        Result = Function(Source, Output)
        return "value", Result is Output
    except Exception as Error:
        return "error", type(Error).__name__, Error.args

def _Compare(Name, Values, Expected_Native, Status=False, Preserve_Array=False):
    global Comparisons
    Source = Values if Preserve_Array else N.array(Values, dtype=N.float64)
    Expected = N.full(Source.shape, -12345.0, dtype=N.float64)
    Actual = Expected.copy()
    Before = _Stats(Name)
    Native._Test_Floating_Status(True)
    Python_Result = _Outcome(getattr(Original, Name), Source, Expected)
    Python_Status = Native._Test_Floating_Status(True)
    Native_Result = _Outcome(getattr(Native, Name), Source, Actual)
    Native_Status = Native._Test_Floating_Status()
    After = _Stats(Name)
    assert Python_Result == Native_Result, (Name, Python_Result, Native_Result)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64)), (Name, N.flatnonzero(Expected.view(N.uint64) != Actual.view(N.uint64))[:10])
    if Status:
        assert Python_Status == Native_Status, (Name, Python_Status, Native_Status)
    Entered = After["Native_Elements"] - Before["Native_Elements"]
    assert Entered == (Expected_Native if Backend else 0), (Name, Entered, Expected_Native, Backend)
    if Entered:
        Native_Functions.add(Name)
    if After["Parallel_Elements"] > Before["Parallel_Elements"]:
        assert Parallel and After["Team"] == 2, (Name, After)
        Parallel_Functions.add(Name)
    Comparisons += 1

Names = ("Map_erf", "Map_erfc", "Aliased_erf", "Aliased_erfc", "Composed", "Nested")
Ordinary = N.linspace(-9.0, 9.0, 10001)
for Name in Names:
    _Compare(Name, Ordinary, len(Ordinary))
    _Compare(Name, (), 0)
    _Compare(Name, (0.0,), 1, True)
    _Compare(Name, (-0.0,), 0, True)
    _Compare(Name, (math.inf, -math.inf, math.nan), 0)
Smallest = N.nextafter(N.float64(0.0), N.float64(1.0))
Largest = N.finfo(N.float64).max
Boundaries = [-Largest, -1e300, -28.0, -6.0, -2.0, -1.0, -Smallest, 0.0, Smallest, N.finfo(N.float64).tiny, 1.0, 2.0, 6.0, 26.0, 26.5, 27.0, 27.25, 28.0, 1e300, Largest]
for Center in (0.46875, 0.84375, 1.0, 1.25, 2.0, 4.0, 6.0, 26.5, 27.0, 27.25):
    Boundaries.extend((math.nextafter(Center, -math.inf), Center, math.nextafter(Center, math.inf)))
Random = N.random.default_rng(294371).integers(0, N.iinfo(N.uint64).max, 20000, dtype=N.uint64).view(N.float64)
Random = Random[N.isfinite(Random) & ~((Random == 0.0) & N.signbit(Random))]
Payloads = N.array([0x7ff8000000000001, 0x7ff812345678abcd, 0xfff8000000000001], dtype=N.uint64).view(N.float64)
for Name in ("Map_erf", "Map_erfc"):
    _Compare(Name, Boundaries, len(Boundaries), True)
    _Compare(Name, Random, len(Random))
    _Compare(Name, Payloads, 0)
    _Compare(Name, N.full(8195, Smallest), 8195, True)
    _Compare(Name, N.full(8195, 27.0), 8195, True)
    _Compare(Name, N.linspace(26.0, 28.0, 10001), 10001)
    for Position in (0, 4095, 4096, 5000, 8192):
        Values = N.ones(8195)
        Values[Position] = math.nan
        _Compare(Name, Values, Position // 4096 * 4096)
    for Values in (N.linspace(0.1, 1.0, 101).astype(N.float32), N.linspace(0.1, 1.0, 202)[::2], N.linspace(0.1, 1.0, 101)[::-1]):
        _Compare(Name, Values, 0, Preserve_Array=True)
for Name, Initial, Bad in (("Domain_erf", 0.5, -1.0), ("Domain_erfc", 0.5, 30.0), ("Overflow_erfc", 2.0, -1.0)):
    Values = N.full(8195, Initial)
    _Compare(Name, Values, len(Values))
    Values[5000] = Bad
    _Compare(Name, Values, 4096, True)
Native._Test_Allocation(True)
try:
    _Compare("Map_erf", Ordinary, 0)
    _Compare("Map_erfc", Ordinary, 0)
finally:
    Native._Test_Allocation(False)

def _Callbacks(Module):
    Events = []
    Namespace = types.SimpleNamespace()
    def Second(Value):
        Events.append(("second", type(Value).__name__, float(Value).hex()))
        return math.erfc(Value)
    def First(Value):
        Events.append(("first", type(Value).__name__, float(Value).hex()))
        Namespace.erf = Second
        return math.erf(Value)
    Namespace.erf = First
    Saved = Module.math
    try:
        Module.math = Namespace
        Values = N.linspace(0.1, 1.0, 9)
        Output = N.zeros_like(Values)
        Result = Module.Map_erf(Values, Output)
        return Events, Result is Output, Output.view(N.uint64).tolist()
    finally:
        Module.math = Saved

Before = _Stats("Map_erf")["Native_Elements"]
assert _Callbacks(Original) == _Callbacks(Native)
assert _Stats("Map_erf")["Native_Elements"] == Before
Comparisons += 1

def _Protocol(Module):
    Events = []
    class Real:
        def __init__(self, Value):
            self.Value = Value
        def __float__(self):
            Events.append(self.Value)
            if self.Value == 5:
                raise ValueError("conversion stopped")
            return self.Value / 10.0
    Values = N.array([Real(Value) for Value in range(9)], dtype=object)
    Output = N.full(Values.shape, -12345.0)
    Result = _Outcome(Module.Map_erf, Values, Output)
    return Events, Result, Output.view(N.uint64).tolist()

Before = _Stats("Map_erf")["Native_Elements"]
assert _Protocol(Original) == _Protocol(Native)
assert _Stats("Map_erf")["Native_Elements"] == Before
Comparisons += 1
Saved_Original, Saved_Native = Original.Error_Function, Native.Error_Function
try:
    Original.Error_Function = math.erfc
    Native.Error_Function = math.erfc
    _Compare("Aliased_erf", Ordinary, 0)
finally:
    Original.Error_Function, Native.Error_Function = Saved_Original, Saved_Native
for Name in ("Map_erf", "Map_erfc"):
    Expected, Actual = Ordinary.copy(), Ordinary.copy()
    Before = _Stats(Name)["Native_Elements"]
    assert _Outcome(getattr(Original, Name), Expected, Expected) == _Outcome(getattr(Native, Name), Actual, Actual)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
    assert _Stats(Name)["Native_Elements"] == Before
    Comparisons += 1
    Expected, Actual = N.zeros_like(Ordinary), N.zeros_like(Ordinary)
    Expected.flags.writeable = Actual.flags.writeable = False
    Before = _Stats(Name)["Native_Elements"]
    assert _Outcome(getattr(Original, Name), Ordinary, Expected) == _Outcome(getattr(Native, Name), Ordinary, Actual)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
    assert _Stats(Name)["Native_Elements"] == Before
    Comparisons += 1
    Before = _Stats(Name)["Native_Elements"]
    with ThreadPoolExecutor(max_workers=1) as Pool:
        Actual = Pool.submit(getattr(Native, Name), Ordinary, N.zeros_like(Ordinary)).result()
    Expected = getattr(Original, Name)(Ordinary, N.zeros_like(Ordinary))
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
    assert _Stats(Name)["Native_Elements"] == Before
    Comparisons += 1
Saved_Handler = signal.getsignal(signal.SIGINT)
try:
    signal.signal(signal.SIGINT, lambda Number, Frame: None)
    _Compare("Map_erf", Ordinary, 0)
    _Compare("Map_erfc", Ordinary, 0)
finally:
    signal.signal(signal.SIGINT, Saved_Handler)
Previous = Native._Test_Rounding(True)
try:
    _Compare("Map_erf", Ordinary, 0)
    _Compare("Map_erfc", Ordinary, 0)
finally:
    Native._Test_Restore_Rounding(Previous)
if Parallel:
    Previous = Native._Test_Rounding(False)
    try:
        Native._Test_Worker_Rounding(True)
        Native._Test_Rounding(False)
        Modes = Native._Test_Worker_Modes()
        assert Modes[0] != Modes[1], Modes
        _Compare("Map_erf", Ordinary, len(Ordinary))
        _Compare("Map_erfc", Ordinary, len(Ordinary))
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
            _Compare("Map_erf", N.full(8195, Smallest), 8195, True)
            _Compare("Map_erfc", N.full(8195, 27.0), 8195, True)
            assert Native._Test_Worker_Controls()[1] == Changed[1]
        finally:
            Native._Test_Worker_Restore_Controls(*Controls)
print(json.dumps(dict(Comparisons=Comparisons, Backend_Eligible=Backend, Forced_Disabled=Disabled, Metadata_Poisoned=Poisoned, Parallel=Parallel, Native_Functions=sorted(Native_Functions), Parallel_Functions=sorted(Parallel_Functions))))
