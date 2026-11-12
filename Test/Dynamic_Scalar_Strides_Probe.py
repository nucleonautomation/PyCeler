import importlib.util
import json
import struct
import sys
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Value(Value):
    if type(Value) is float:
        return ("float", struct.pack("!d", Value).hex())
    if type(Value) in (tuple, list):
        return (type(Value).__name__, tuple(_Value(Item) for Item in Value))
    return Value

def _Observe(Module, Name, Args, Callback=None):
    Events = []
    try:
        Result = getattr(Module, Name)(*Args, Events, *((Callback,) if Callback is not None else ()))
    except Exception as Error:
        return type(Error).__name__, str(Error), _Value(Events)
    return "return", _Value(Result), _Value(Events)

def _Keep(Index, Total, Stride):
    return Total, Stride

def _Change(Index, Total, Stride):
    return Total * 2 + Index, -Stride

def _Zero(Index, Total, Stride):
    return Total + 1, 0

def _Bigint(Index, Total, Stride):
    return Total + 2**80, Stride

def _Fraction(Index, Total, Stride):
    return Total + 0.5, Stride

def _Fail(*Args):
    raise LookupError("dynamic stride callback")

def _Run(Binary, Source):
    Native = _Load("Dynamic_Scalar_Strides", Binary)
    Original = _Load("Original_Dynamic_Scalar_Strides", Source)
    Region_Stats = next(Value for Name, Value in vars(Native).items() if Name.startswith("_Pyceler_") and Name.endswith("Region_Stats"))
    Module_Stats = next(Value for Name, Value in vars(Native).items() if Name.startswith("_Pyceler_") and Name.endswith("Module_Stats"))
    assert Native.Module_Results == Original.Module_Results
    assert Module_Stats()["Native"] > 0 and Module_Stats()["Parallel"] == 0, Module_Stats()
    Comparisons = 0
    for Stride in (-7, -4, -3, -1, 1, 2, 3, 6, 7):
        for Begin in (-19, -1, 0, 7, 19):
            for End in (-19, -1, 0, 7, 19):
                Args = (Begin, End, Stride, 0)
                Before = Region_Stats()
                Expected = _Observe(Original, "Mixed", Args, _Keep)
                Actual = _Observe(Native, "Mixed", Args, _Keep)
                After = Region_Stats()
                assert Actual == Expected, (Args, Expected, Actual)
                if range(Begin, End, Stride):
                    assert After[0] > Before[0] and After[1] == Before[1], (Args, Before, After)
                else:
                    assert After == Before, ("empty native span", Args, Before, After)
                Comparisons += 1
        Begin, End = (-19, 40) if Stride > 0 else (19, -40)
        for Callback in (_Change, _Zero, _Bigint, _Fraction, _Fail):
            Args = (Begin, End, Stride, 0)
            Expected = _Observe(Original, "Mixed", Args, Callback)
            Actual = _Observe(Native, "Mixed", Args, Callback)
            assert Actual == Expected, (Args, Callback, Expected, Actual)
            Comparisons += 1
        for Value in (-777, -888, 13):
            def Control(Index, Total):
                return Value
            Args = (Begin, End, Stride)
            assert _Observe(Native, "Control", Args, Control) == _Observe(Original, "Control", Args, Control)
            Comparisons += 1
        for Name, Args in (("Fraction", (Begin, End, Stride)), ("Partial", (Begin, End, Stride, Begin + 2 * Stride))):
            assert _Observe(Native, Name, Args) == _Observe(Original, Name, Args), (Name, Args)
            Comparisons += 1
    for Name in ("Header", "Unbound"):
        for Args in ((0, 0, 3), (1, 20, 0), (1, 20, True), (1, 20, False), (1, 20, 1.5), (1, 20, 2**80), (1, -20, -(2**80)), (2**63 - 1, 2**63 + 2, 1), (-(2**63), -(2**63) - 3, -1)):
            Expected = _Observe(Original, Name, Args)
            Before = Region_Stats()
            Actual = _Observe(Native, Name, Args)
            assert Actual == Expected, (Name, Args, Expected, Actual)
            if type(Args[2]) is int and (abs(Args[2]) > 2**63 or abs(Args[0]) >= 2**63 - 1):
                assert Region_Stats()[1] > Before[1], ("expected guarded fallback", Name, Args)
            Comparisons += 1
    for Values in ((-7, 20, 3), (9, -20, -4), (0, 9, 0)):
        Traces = []
        for Module in (Original, Native):
            Events = []
            class Index_Value:
                def __init__(self, Label, Value):
                    self._Label, self._Value = Label, Value
                def __index__(self):
                    Events.append(self._Label)
                    return self._Value
            Args = tuple(Index_Value(Label, Value) for Label, Value in zip(("begin", "end", "stride"), Values))
            Traces.append((_Observe(Module, "Header", Args), Events))
        assert Traces[0] == Traces[1], (Values, Traces)
        assert Traces[0][1].count("stride") == 1 and all(Traces[0][1].count(Label) <= 1 for Label in ("begin", "end")), Traces
        Comparisons += 1
    for Replacement, Native_Range in ((lambda *Args: iter((9, 3, -12)), False), (lambda *Args: range(30, -21, -3), True)):
        for Module in (Original, Native):
            Module.range = Replacement
        try:
            Args = (0, 99, 2, 0)
            Before = Region_Stats()
            assert _Observe(Native, "Mixed", Args, _Change) == _Observe(Original, "Mixed", Args, _Change)
            After = Region_Stats()
            assert (After[0] > Before[0]) is Native_Range, ("shadowed range guard", Before, After)
            assert Native_Range or After[1] > Before[1], ("custom iterator fallback", Before, After)
            Comparisons += 1
        finally:
            del Original.range
            del Native.range
    return dict(Comparisons=Comparisons, Module_Statistics=Module_Stats(), Region_Statistics=Region_Stats())

if __name__ == "__main__":
    print(json.dumps(_Run(Path(sys.argv[1]), Path(sys.argv[2]))))
