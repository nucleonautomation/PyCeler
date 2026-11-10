import contextlib
import importlib.util
import io
import sys
from types import SimpleNamespace
import Scalar_Regions as Native

Spec = importlib.util.spec_from_file_location("Original_Scalar_Regions", Reference_Path)
Original = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Original)

def _Observe(Function, Count, *Arguments):
    Events = []
    try:
        Result = Function(Count, Events, *Arguments)
    except Exception as Error:
        return type(Error), str(Error), Events, tuple(tuple(type(Value) for Value in Event) for Event in Events)
    return type(Result), Result, Events, tuple(tuple(type(Value) for Value in Event) for Event in Events)

def _Check(Name, Count, *Arguments):
    Expected = _Observe(getattr(Original, Name), Count, *Arguments)
    Before = Native._Pyceler_Region_Stats()
    Actual = _Observe(getattr(Native, Name), Count, *Arguments)
    After = Native._Pyceler_Region_Stats()
    assert Actual == Expected, (Name, Count, Arguments, Expected, Actual)
    return Before, After, Actual

def _Prints(Module, Name, Count):
    Ticks = []
    def _Clock():
        Ticks.append(1)
        return len(Ticks) / 8
    Saved = Module.time
    Module.time = SimpleNamespace(perf_counter=_Clock)
    Output = io.StringIO()
    try:
        with contextlib.redirect_stdout(Output):
            Result = getattr(Module, Name)(Count)
    finally:
        Module.time = Saved
    return Result, Output.getvalue(), len(Ticks)

def _Mutate(Index, Total):
    return Total * 2 + Index

def _Bigint(Index, Total):
    return Total + 2**80

def _Float(Index, Total):
    return Total + 0.5

def _Fail(Index, Total):
    if Index >= 10:
        raise LookupError("callback boundary")
    return Total

for Name in ("Module_Events", "Module_Result", "Module_Division_Events", "Module_Division_Result"):
    assert getattr(Native, Name) == getattr(Original, Name), Name
assert Native._Pyceler_Region_Stats()[0] == 0, "module-level state must remain in Python"
for Name in ("Remainder", "Division", "Plain_Region"):
    for Count in (0, -2, 1, 7, 8, 14, 15, 31, 1000):
        Before, After, Actual = _Check(Name, Count)
        if Count > 0:
            assert After[0] > Before[0], ("native span not attempted", Name, Count, Before, After)
            assert After[1] == Before[1], ("unexpected fallback", Name, Count, Before, After)
        else:
            assert Actual[2][-1][-1] == -23, ("empty loop changed Index", Name, Actual)
for Callback in (_Mutate, _Bigint, _Float, _Fail):
    Before, After, Actual = _Check("Mutating_Progress", 31, Callback)
    assert After[0] > Before[0], (Callback.__name__, Before, After)
    if Callback in (_Bigint, _Float):
        assert After[1] > Before[1], ("callback type change did not trigger fallback", Callback.__name__)
Before, After, Actual = _Check("Overflow", 100, 10**16)
assert After[0] > Before[0] and After[1] > Before[1], (Before, After)
assert Actual[2][0][0] == 4 and Actual[2][1][0] == 8, Actual
assert Actual[2][-1][1] > 2**63, Actual
for Count in (0, 1, 5, 6, 11, 31):
    Before, After, Actual = _Check("Range_Snapshot", Count)
    if Count > 0:
        assert Actual[2][0] == (0, Count, Count), Actual
        assert Actual[2][-1][2] == Count - 1, ("range stop was reevaluated", Count, Actual)
for Count in (-15, -9, -8, -4, 0, 1, 9):
    _Check("Negative_Start", Count)
for Module in (Original, Native):
    Value = int("1234567890123456789")
    Events = []
    Module.Conditional_Identity(10, Value, Events)
    assert Events[0] is Value, ("unchanged scalar argument lost identity", Module.__name__)
    for Name in ("Literal_Identity", "Constant_Identity"):
        Events = []
        getattr(Module, Name)(10, Events)
        getattr(Module, Name)(10, Events)
        assert Events[0] is Events[1], ("literal result lost identity", Module.__name__, Name)
for Name in ("Remainder_Benchmark", "Division_Benchmark"):
    for Count in (0, 1, 10, 11, 21, 35):
        Expected = _Prints(Original, Name, Count)
        Actual = _Prints(Native, Name, Count)
        assert Actual == Expected, (Name, Count, Expected, Actual)
Native.range = lambda Count: [9, 3, 14]
Original.range = Native.range
for Name in ("Remainder", "Division", "Plain_Region"):
    Before, After, Actual = _Check(Name, 100)
    assert After[1] > Before[1], ("custom range did not use inline fallback", Name)
del Native.range
del Original.range
for Count in (0, 1, 5, 6, 11, 30):
    _Check("Progress_Control", Count)
import builtins as Builtins
Saved_Range = Builtins.range
del Builtins.range
try:
    Expected = _Observe(Original.Remainder, 5)
    Actual = _Observe(Native.Remainder, 5)
finally:
    Builtins.range = Saved_Range
assert Actual == Expected and Actual[0] is NameError, (Actual, Expected)
print("Scalar region native, callback, overflow, empty-loop and progress checks passed.")
