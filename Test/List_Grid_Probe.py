import copy
import importlib.util
import json
import struct
import sys
from pathlib import Path
# Isolated verification for nested list updates and object identity.
def _Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Value(Value):
    if type(Value) is float:
        return struct.pack("!d", Value).hex()
    if type(Value) in (tuple, list):
        return type(Value).__name__, tuple(_Value(Item) for Item in Value)
    return type(Value).__name__, repr(Value)

def _Observe(Function, Args):
    Before = [list(Item) for Item in Args if type(Item) is list]
    try:
        Result = Function(*Args)
        Outcome = "value", _Value(Result)
        if Function.__name__ == "Aliases" and Args[2] > 2 and Args[3] > 2:
            assert Result[1] is Result[2] is Result[0][Args[2] - 2][Args[3] - 2]
    except Exception as Error:
        Outcome = "error", type(Error).__name__, str(Error)
    for Matrix, Rows in zip((Item for Item in Args if type(Item) is list), Before):
        assert all(Left is Right for Left, Right in zip(Matrix, Rows)), "row identity changed"
    return Outcome, _Value(Args)

def _Count(Module):
    return sum(Value()["Native_Elements"] for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_Fast_") and Name.endswith("Stats"))

def _Arguments(Height=8, Width=9):
    return ([[0.01 + (Row * Width + Column) * 0.001 for Column in range(Width)] for Row in range(Height)], [[0.0] * Width for Row in range(Height)], Height, Width)

def Main():
    Original = _Load(sys.argv[1], "Reference")
    Native = _Load(sys.argv[2], "List_Grid_Loops")
    Names = [Name for Name in vars(Original) if Name[:1].isupper() and Name != "Two_Inputs"]
    Comparisons = Positive = 0
    for Name in Names:
        Cases = [(_Arguments(), True), (_Arguments(32, 39), True), (_Arguments(130, 137), True), (_Arguments(0, 0), False), (_Arguments(2, 2), False), (_Arguments(3, 3), False)]
        for Kind in ("alias", "shared", "overlap", "ragged", "integer", "nonfinite", "zero", "bounds", "tuple", "negative_zero", "nan", "large", "tiny"):
            A, B, H, W = _Arguments()
            if Kind == "alias":
                B = A
            elif Kind == "shared":
                B = [B[0]] * H
            elif Kind == "overlap":
                B[3] = A[4]
            elif Kind == "ragged":
                A[3] = A[3][:2]
            elif Kind == "integer":
                A[3][4] = 1
            elif Kind == "nonfinite":
                A[3][4] = float("inf")
            elif Kind == "zero":
                A[3][4] = 0.0
            elif Kind == "bounds":
                H += 2
            elif Kind == "tuple":
                A = tuple(tuple(Row) for Row in A)
            elif Kind == "negative_zero":
                A[3][4] = -0.0
            elif Kind == "nan":
                A[3][4] = float("nan")
            elif Kind == "large":
                A[3][4] = 1.7e308
            elif Kind == "tiny":
                A[3][4] = 5e-324
            Cases.append(((A, B, H, W), False))
        for Args, Expect_Native in Cases:
            Before = _Count(Native)
            Expected = _Observe(getattr(Original, Name), copy.deepcopy(Args))
            Actual = _Observe(getattr(Native, Name), copy.deepcopy(Args))
            assert Actual == Expected, (Name, Actual, Expected)
            if Expect_Native:
                assert _Count(Native) > Before, Name
                Positive += 1
            Comparisons += 1
    for Height, Width in ((8, 9), (32, 39), (130, 137)):
        A, B, H, W = _Arguments(Height, Width)
        Args = (A, copy.deepcopy(A), B, H, W)
        Before = _Count(Native)
        assert _Observe(Original.Two_Inputs, copy.deepcopy(Args)) == _Observe(Native.Two_Inputs, copy.deepcopy(Args))
        assert _Count(Native) > Before
        Comparisons += 1
        Positive += 1
    Before = _Count(Native)
    sys.setprofile(lambda *Args: None)
    try:
        assert _Observe(Original.Weighted, _Arguments()) == _Observe(Native.Weighted, _Arguments())
    finally:
        sys.setprofile(None)
    assert _Count(Native) == Before
    for Name in ("range", "len"):
        import builtins
        Calls = []
        Saved = getattr(builtins, Name)
        def Rebound(*Args):
            Calls.append(Args)
            return Saved(*Args)
        setattr(Original, Name, Rebound)
        setattr(Native, Name, Rebound)
        try:
            Calls.clear()
            Expected = _Observe(Original.Dimensions, _Arguments())
            Expected_Count = len(Calls)
            Calls.clear()
            Actual = _Observe(Native.Dimensions, _Arguments())
            assert Expected == Actual and len(Calls) == Expected_Count
            assert _Count(Native) == Before
        finally:
            delattr(Original, Name)
            delattr(Native, Name)
        Comparisons += 1
    if hasattr(Native, "Test_Rounding"):
        Native.Test_Rounding(True)
        try:
            assert _Observe(Original.Weighted, _Arguments()) == _Observe(Native.Weighted, _Arguments())
        finally:
            Native.Test_Rounding(False)
        assert _Count(Native) == Before
        Flags = []
        Args = _Arguments()
        for Function in (Original.Weighted, Native.Weighted):
            Arguments = copy.deepcopy(Args)
            Native.Test_Flags(True)
            Function(*Arguments)
            Flags.append(Native.Test_Flags())
        assert Flags[0] == Flags[1], Flags
        Comparisons += 2
    import builtins
    Calls, Length = [], builtins.len
    def Length_Observer(Value):
        Result = Length(Value)
        Calls.append(Result)
        return Result
    Before = _Count(Native)
    Outcomes = []
    for Function in (Original.Dimensions, Native.Dimensions):
        Args = _Arguments()
        Calls.clear()
        builtins.len = Length_Observer
        try:
            Result = Function(*Args)
        finally:
            builtins.len = Length
        Outcomes.append((_Value(Result), Calls[:]))
    assert Outcomes[0] == Outcomes[1] and _Count(Native) == Before, Outcomes
    Comparisons += 1
    Report = dict(Comparisons=Comparisons + 1, Positive_Native_Cases=Positive, Native_Elements=_Count(Native))
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(Report))

if __name__ == "__main__":
    Main()
