import copy
import importlib.util
import json
import sys
from pathlib import Path
# Isolated verification for expanded numeric.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Benchmark_List_Grids import _Snapshot

def Load(Pathname, Name):
    Spec = importlib.util.spec_from_file_location(Name, Pathname)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Count(Module):
    return sum(Value()["Native_Elements"] for Name, Value in vars(Module).items() if Name.startswith("_Pyceler_Fast_") and Name.endswith("Stats"))

def Observe(Function, Args):
    try:
        Value, Error = Function(*Args), None
    except Exception as Failure:
        Value, Error = None, (type(Failure).__name__, str(Failure))
    return _Snapshot(dict(Args=Args, Result=Value)), Error

def Arguments(Name, Size):
    if Name == 'Hypercube':
        Source = [[[[0.01 + (A * 24 + B * 8 + C * 2 + D) * 0.001 for D in range(2)] for C in range(4)] for B in range(3)] for A in range(Size)]
        return Source, copy.deepcopy(Source), Size
    if Name in ("Volume", "Initialize"):
        Values = [[[0.01 + (A * 9 + B * 3 + C) * 0.001 for C in range(7)] for B in range(9)] for A in range(Size)]
        Target = [[[0.0] * 7 for B in range(9)] for A in range(Size)]
        return (Values, Target, Size, 9, 7) if Name == "Volume" else (Target, Size, 9, 7)
    if Name == "Neighbors":
        return ([[((A * 3 + B * 7) % 5) < 2 for B in range(9)] for A in range(Size)], [[0] * 9 for A in range(Size)], Size, 9)
    if Name == "Mark":
        return [True] * Size, 0, Size, 2
    if Name == "Count_Flags":
        return [Index % 4 == 1 for Index in range(Size)], Size
    if Name == "Scatter":
        return [Index // 2 for Index in range(Size)], [7.5] * Size, Size
    return ([[A % 7 - B % 5 for B in range(Size)] for A in range(Size)], [[A % 3 + B % 4 for B in range(Size)] for A in range(Size)], [[0] * Size for A in range(Size)], Size)

def Main():
    Reference = Load(sys.argv[1], "Reference")
    Native = Load(sys.argv[2], "Expanded_Numeric_Loops")
    Cases = []
    for Name in ("Volume", "Initialize", "Neighbors", "Mark", "Count_Flags", "Product", "Scatter", "Hypercube"):
        for Size in (0, 1, 2, 9, 40):
            Cases.append((Name, Arguments(Name, Size), Size >= 9))
    for Size in (9, 40, 65540):
        Cases.append(("Mark", ([True] * Size, Size - 1, -1, -3), True))
        Cases.append(("Count_Flags", ([False] * Size, Size), True))
    for Begin, End, Step in ((-9, 0, 2), (4, -5, -2)):
        Cases.append(("Mark", ([True] * 9, Begin, End, Step), True))
    for Value in (2**50 + 1, -(2**50 + 1), 1.0, None):
        Args = list(Arguments("Product", 9))
        Args[0][3][4] = Value
        Cases.append(("Product", tuple(Args), False))
    Args = list(Arguments("Product", 9))
    Args[0][1][1] = 2**49
    Args[1][1][1] = 2**49
    Cases.append(("Product", tuple(Args), False))
    for Mode in ("short", "row_alias", "plane_alias", "source_alias", "mixed", "nonfinite"):
        Args = list(Arguments("Volume", 9))
        if Mode == "short":
            Args[0][3][2].pop()
        elif Mode == "row_alias":
            Args[1][2][3] = Args[1][2][2]
        elif Mode == "plane_alias":
            Args[1][3] = Args[1][2]
        elif Mode == "source_alias":
            Args[1] = Args[0]
        else:
            Args[0][2][3][4] = 1 if Mode == "mixed" else float("inf")
        Cases.append(("Volume", tuple(Args), False))
    for Args in (([True] * 9, 0, 9, 0), ([True] * 9, 0, 12, 1), ([True] * 9, 10, -1, -1), ([True] * 9, -10, 0, 1), ([True] * 65540, 0, 65542, 1)):
        Cases.append(("Mark", Args, False))
    for Value in (-1, 20, 2**80):
        Args = list(Arguments("Scatter", 9))
        Args[0][5] = Value
        Cases.append(("Scatter", tuple(Args), False))
    Positive = 0
    for Name, Args, Require in Cases:
        Before = Count(Native)
        Expected = Observe(getattr(Reference, Name), copy.deepcopy(Args))
        Actual = Observe(getattr(Native, Name), copy.deepcopy(Args))
        assert Expected == Actual, (Name, Args[-1], Expected, Actual)
        if Require:
            assert Count(Native) > Before, (Name, "No native execution", Args[-1])
            Positive += 1
    Before = Count(Native)
    sys.setprofile(lambda *Args: None)
    try:
        Args = Arguments("Count_Flags", 40)
        assert Observe(Reference.Count_Flags, copy.deepcopy(Args)) == Observe(Native.Count_Flags, copy.deepcopy(Args))
    finally:
        sys.setprofile(None)
    assert Count(Native) == Before
    Report = dict(Comparisons=len(Cases) + 1, Positive_Native_Cases=Positive, Native_Elements=Count(Native))
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2))
    print(json.dumps(Report))

if __name__ == "__main__":
    Main()
