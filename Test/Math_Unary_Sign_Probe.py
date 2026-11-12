import ast
import importlib.util
import json
import math
import sys
from pathlib import Path
import numpy as N

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Outcome(Function, Source, Output):
    try:
        return "value", Function(Source, Output) is Output
    except Exception as Error:
        return "error", type(Error).__name__, Error.args

Original = _Load("Reference_Unary_Signs", sys.argv[2])
Native = _Load("Math_Unary_Sign_Loops", sys.argv[1])
Parallel = sys.argv[3] == "parallel"
Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Path(sys.argv[2]).read_text()).body if isinstance(Node, ast.FunctionDef)}
Comparisons = 0
Native_Functions = set()
Parallel_Functions = set()

def _Compare(Name, Values, Expected_Native):
    global Comparisons
    Source = N.array(Values, dtype=N.float64)
    Expected, Actual = N.full(Source.shape, -12345.0), N.full(Source.shape, -12345.0)
    Stats = getattr(Native, "_Pyceler_Fast_" + str(Locations[Name]) + "_Stats")
    Before = Stats()
    Native._Test_Floating_Status(True)
    Python_Result = _Outcome(getattr(Original, Name), Source, Expected)
    Python_Flags = Native._Test_Floating_Status(True)
    Native_Result = _Outcome(getattr(Native, Name), Source, Actual)
    Native_Flags = Native._Test_Floating_Status()
    After = Stats()
    assert Python_Result == Native_Result, (Name, Python_Result, Native_Result)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64)), (Name, N.flatnonzero(Expected.view(N.uint64) != Actual.view(N.uint64))[:10])
    assert Python_Flags == Native_Flags, (Name, Python_Flags, Native_Flags)
    assert After["Native_Elements"] - Before["Native_Elements"] == Expected_Native, (Name, Before, After, Expected_Native)
    if Expected_Native:
        Native_Functions.add(Name)
        assert After["Team"] == (2 if Parallel else 1), (Name, After)
    assert After["Parallel_Elements"] - Before["Parallel_Elements"] == (Expected_Native if Parallel else 0), (Name, Before, After)
    if Expected_Native and Parallel:
        Parallel_Functions.add(Name)
    Comparisons += 1

for Down in (False, True):
    Previous = Native._Test_Rounding(Down)
    try:
        for Size in (0, 1, 9, 8195):
            Values = N.linspace(0.125, 1.125, Size)
            Values[::3] *= -1.0
            for Name in Locations:
                _Compare(Name, Values, 0 if Down else Size)
    finally:
        Native._Test_Restore_Rounding(Previous)
for Name in Locations:
    for Values in ((-0.0, 0.5), (math.inf, 0.5), (math.nan, 0.5)):
        _Compare(Name, Values, 0)
print(json.dumps(dict(Comparisons=Comparisons, Exact_Bits=True, Caller_Flags=True, Output_Identity=True, Parallel=Parallel, Native_Functions=sorted(Native_Functions), Parallel_Functions=sorted(Parallel_Functions))))
