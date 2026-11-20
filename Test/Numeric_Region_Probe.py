import copy
import importlib.util
import json
import math
import sys
from pathlib import Path
# Isolated verification for nested numeric control flow, list identities and partial errors.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Benchmark_List_Grids import _Snapshot

def _Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Count(Module):
    return sum(Value()["Native_Elements"] for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_Fast_") and Name.endswith("Stats"))

def _Observe(Function, Args):
    try:
        Result = Function(*Args)
        Error = None
    except Exception as Failure:
        Result, Error = None, (type(Failure).__name__, str(Failure))
    return _Snapshot(dict(Args=Args, Result=Result)), Error

def _Arguments(Name, Size):
    Values = [0.01 + Index * 0.002 for Index in range(Size)]
    Output = [0.0] * Size
    if Name == "Escape":
        return ([[0] * (Size + 3) for Index in range(Size)], Size, Size + 3, 300)
    if Name == "Pairwise":
        return (Values, [Value * 0.3 for Value in Values], [Value + 0.5 for Value in Values], Output, Output[:], Size, 0.01, 0.9)
    if Name == "Integrate":
        return (Values, Values[:], Output, Output[:], Values[:], Values[:], Size, 0.001)
    if Name == "Prefix":
        return Values, Size
    if Name == "Nested":
        return ([[Value + Row * 0.01 for Value in Values] for Row in range(Size)], [[0.0] * Size for Row in range(Size)], Size, Size, 7)
    if Name == "Control":
        return Values, Output, Size, 7
    return Values, Output, Size

def Main():
    Original = _Load(sys.argv[1], "Reference")
    Native = _Load(sys.argv[2], "Numeric_Region_Loops")
    Names = [Name for Name in vars(Original) if Name[:1].isupper()]
    Comparisons = Positive = 0
    for Name in Names:
        Cases = [(_Arguments(Name, Size), Size >= 8) for Size in (0, 1, 2, 8, 40, 129)]
        Base = _Arguments(Name, 8)
        for Kind in ("alias", "short", "integer", "infinity", "nan", "zero", "negative", "large", "tiny", "negative_zero"):
            Args = list(copy.deepcopy(Base))
            if Name in ("Escape", "Nested"):
                if Kind == "alias":
                    Args[0][3] = Args[0][2]
                elif Kind == "short":
                    Args[0][2] = Args[0][2][:1]
                else:
                    continue
            elif Kind == "alias":
                if type(Args[1]) is list:
                    Args[1] = Args[0]
            elif Kind == "short":
                Args[0] = Args[0][:-2]
            else:
                Args[0][3] = dict(integer=1, infinity=float("inf"), nan=float("nan"), zero=0.0, negative=-0.5, large=1.7e308, tiny=5e-324, negative_zero=-0.0)[Kind]
            Cases.append((tuple(Args), False))
        for Args, Require_Native in Cases:
            Before = _Count(Native)
            Expected = _Observe(getattr(Original, Name), copy.deepcopy(Args))
            Actual = _Observe(getattr(Native, Name), copy.deepcopy(Args))
            assert Expected == Actual, (Name, Args[-3:], Expected, Actual)
            if Require_Native:
                assert _Count(Native) > Before, (Name, "retained Python")
                Positive += 1
            Comparisons += 1
    Before = _Count(Native)
    sys.setprofile(lambda *Args: None)
    try:
        assert _Observe(Original.Pairwise, _Arguments("Pairwise", 8)) == _Observe(Native.Pairwise, _Arguments("Pairwise", 8))
    finally:
        sys.setprofile(None)
    assert _Count(Native) == Before
    Saved = math.sqrt
    Calls = []
    def Rebound(Value):
        Calls.append(Value)
        return Saved(Value)
    math.sqrt = Rebound
    try:
        Expected = _Observe(Original.Pairwise, _Arguments("Pairwise", 8))
        Expected_Calls = Calls[:]
        Calls.clear()
        Actual = _Observe(Native.Pairwise, _Arguments("Pairwise", 8))
        assert Actual == Expected and Calls == Expected_Calls and _Count(Native) == Before
    finally:
        math.sqrt = Saved
    Comparisons += 2
    Before = _Count(Native)
    del Original.math
    del Native.math
    try:
        assert _Observe(Original.Binding_State, _Arguments("Binding_State", 8)) == _Observe(Native.Binding_State, _Arguments("Binding_State", 8))
        assert _Count(Native) == Before
    finally:
        Original.math = math
        Native.math = math
    Comparisons += 1
    if hasattr(Native, "Test_Rounding"):
        Native.Test_Rounding(True)
        try:
            assert _Observe(Original.Pairwise, _Arguments("Pairwise", 8)) == _Observe(Native.Pairwise, _Arguments("Pairwise", 8))
        finally:
            Native.Test_Rounding(False)
        assert _Count(Native) == Before
        Flags = []
        for Function in (Original.Pairwise, Native.Pairwise):
            Args = _Arguments("Pairwise", 8)
            Native.Test_Flags(True)
            Function(*Args)
            Flags.append(Native.Test_Flags())
        assert Flags[0] == Flags[1], Flags
        Comparisons += 2
    Report = dict(Comparisons=Comparisons, Positive_Native_Cases=Positive, Native_Elements=_Count(Native))
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(Report), flush=True)

if __name__ == "__main__":
    Main()
