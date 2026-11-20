import importlib.util
import json
import math
import struct
import sys
from pathlib import Path
# Isolated verification for scalar math call boundaries and observer behavior.
def _Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Value(Value):
    if type(Value) is float:
        return "float", struct.pack("!d", Value).hex()
    if type(Value) in (tuple, list):
        return type(Value).__name__, tuple(_Value(Part) for Part in Value)
    return type(Value).__name__, repr(Value)

def _Observe(Function, Arguments):
    try:
        return "value", _Value(Function(*Arguments))
    except Exception as Error:
        return "error", type(Error).__name__, str(Error)

def _Native(Module):
    return sum(Function()["Native_Elements"] for Name, Function in vars(Module).items() if Name.startswith("_Pyceler_Fast_") and Name.endswith("_Stats"))

def Main():
    Source, Binary, Destination = map(Path, sys.argv[1:4])
    Original, Native = _Load(Source, "Reference"), _Load(Binary, Binary.stem)
    assert _Value(Original.Module_Result) == _Value(Native.Module_Result)
    assert _Native(Native) == 80
    assert Native._Pyceler_Module_Stats()["Fallbacks"] == 0
    Cases = [(80, 0.2, 0.4, 0.0), (9000, 0.2, 0.4, 0.0), (0, 0.2, 0.4, 0.0), (-1, 0.2, 0.4, 0.0), (1, -0.0, 0.0, -0.0), (8, -0.25, -0.5, 1.0), (5, 2, 3, 0), (3, float("nan"), 0.2, 0.0), (3, float("inf"), 0.2, 0.0), (3, 0.2, 1e308, 0.0), (8, 0.5, 0.25, 1e308)]
    Names = ("Recurrence", "Aliases", "Branches", "Descending", "Domain", "Nested")
    Cases.extend(((80, 7.5, 5.0, 0.0), (80, 1000.0, -1000.0, 0.0), (80, 1e-300, -1e-300, 0.0)))
    Comparisons, Positive = 0, 0
    for Name in Names:
        for Position, Args in enumerate(Cases):
            Before = _Native(Native)
            Expected = _Observe(getattr(Original, Name), Args)
            Actual = _Observe(getattr(Native, Name), Args)
            assert Actual == Expected, (Name, Args, Actual, Expected)
            if Position < 2 and Name != "Domain":
                assert _Native(Native) > Before, (Name, Args, Before, _Native(Native))
                Positive += 1
            Comparisons += 1
    for Count, First in ((0, 1.0), (5, 2.0), (10, 0.5), (66000, 9000.0), (66000, 8193.0)):
        Expected, Actual = _Observe(Original.Global_Domain, (Count, First)), _Observe(Native.Global_Domain, (Count, First))
        assert Actual == Expected, (Actual, Expected)
        for Name in ("State", "Total", "Last", "Part"):
            assert _Value(getattr(Original, Name)) == _Value(getattr(Native, Name)), Name
        Comparisons += 1
    Saved = math.sin
    Calls = []
    def Rebound(Value):
        Calls.append(Value)
        return Saved(Value)
    try:
        math.sin = Rebound
        Expected = _Observe(Original.Recurrence, (80, 0.2, 0.4, 0.0))
        Expected_Calls = Calls[:]
        Calls.clear()
        Before = _Native(Native)
        Actual = _Observe(Native.Recurrence, (80, 0.2, 0.4, 0.0))
        assert Actual == Expected and Calls == Expected_Calls and _Native(Native) == Before
        Comparisons += 1
    finally:
        math.sin = Saved
    Before = _Native(Native)
    sys.setprofile(lambda *Args: None)
    try:
        assert _Observe(Original.Recurrence, (80, 0.2, 0.4, 0.0)) == _Observe(Native.Recurrence, (80, 0.2, 0.4, 0.0))
    finally:
        sys.setprofile(None)
    assert _Native(Native) == Before
    for Name in ("Destruction", "Local_Destruction"):
        Before = _Native(Native)
        Expected = _Observe(getattr(Original, Name), (8, 0.2))
        Actual = _Observe(getattr(Native, Name), (8, 0.2))
        assert Actual == Expected and _Native(Native) == Before, (Name, Actual, Expected)
        Comparisons += 1
    if hasattr(Native, "Test_Rounding"):
        Before = _Native(Native)
        Native.Test_Rounding(True)
        try:
            assert _Observe(Original.Recurrence, (80, 0.2, 0.4, 0.0)) == _Observe(Native.Recurrence, (80, 0.2, 0.4, 0.0))
        finally:
            Native.Test_Rounding(False)
        assert _Native(Native) == Before
        Flags = []
        for Function in (Original.Recurrence, Native.Recurrence):
            Native.Test_Flags(True)
            Function(80, 0.2, 0.4, 0.0)
            Flags.append(Native.Test_Flags())
        assert Flags[0] == Flags[1], Flags
        Comparisons += 2
    Report = dict(Comparisons=Comparisons + 1, Positive_Native_Cases=Positive, Native_Elements=_Native(Native), Module_Stats=Native._Pyceler_Module_Stats())
    Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(Report), flush=True)

if __name__ == "__main__":
    Main()
