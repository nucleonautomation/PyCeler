import ast
import importlib.util
import json
import math
import signal
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as N

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

Original = _Load("Reference_Binary_Math", sys.argv[2])
Native = _Load("Fast_Binary_Loops", sys.argv[1])
Parallel = sys.argv[3] == "parallel"
Locations = {Node.name: Node.body[0].lineno for Node in ast.parse(Path(sys.argv[2]).read_text()).body if isinstance(Node, ast.FunctionDef) and not Node.name.startswith("Deferred_")}
Comparisons = 0
Native_Functions = set()
Parallel_Functions = set()

def _Stats(Name):
    Suffix = "Fast_" + str(Locations[Name]) + "_Stats"
    Helper = next(Value for Key, Value in vars(Native).items() if Key.startswith("_Pyceler_") and Key.endswith(Suffix))
    return Helper()

def _Outcome(Function, Left, Right, Output):
    try:
        return "value", (Function(Left, Output) if Function.__name__ == "Same_Input" else Function(Left, Right, Output)) is Output
    except Exception as Error:
        return "error", type(Error).__name__, Error.args

def _Compare(Name, Left, Right, Expected_Native, Preserve=False):
    global Comparisons
    Left = Left if Preserve else N.array(Left, dtype=N.float64)
    Right = Right if Preserve else N.array(Right, dtype=N.float64)
    Expected, Actual = N.full(Left.shape, -12345.0), N.full(Left.shape, -12345.0)
    Left_Before, Right_Before = Left.tobytes(), Right.tobytes()
    Before = _Stats(Name)
    Native._Test_Floating_Status(True)
    Python_Result = _Outcome(getattr(Original, Name), Left, Right, Expected)
    Python_Flags = Native._Test_Floating_Status(True)
    Native_Result = _Outcome(getattr(Native, Name), Left, Right, Actual)
    Native_Flags = Native._Test_Floating_Status()
    After = _Stats(Name)
    assert Python_Result == Native_Result, (Name, Python_Result, Native_Result)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64)), (Name, N.flatnonzero(Expected.view(N.uint64) != Actual.view(N.uint64))[:10])
    assert Python_Flags == Native_Flags, (Name, Python_Flags, Native_Flags)
    assert Left.tobytes() == Left_Before and Right.tobytes() == Right_Before
    assert After["Native_Elements"] - Before["Native_Elements"] == Expected_Native, (Name, Before, After, Expected_Native)
    assert After["Parallel_Elements"] - Before["Parallel_Elements"] == (Expected_Native if Parallel else 0)
    if Expected_Native:
        Native_Functions.add(Name)
        assert After["Team"] == (2 if Parallel else 1), (Name, After)
        if Parallel:
            Parallel_Functions.add(Name)
    Comparisons += 1

for Name in Locations:
    for Size in (0, 1, 9, 8195):
        _Compare(Name, N.full(Size, 2.5), N.full(Size, 1.7), 0 if Name == "Float_Negative_Zero_Sign" else Size)
Smallest = N.nextafter(N.float64(0.0), N.float64(1.0))
Largest = N.finfo(N.float64).max
Boundary = N.array([-Largest, -1.0, -Smallest, 0.0, Smallest, N.finfo(N.float64).tiny, 1.0, Largest])
for Sign in (-1.0, 1.0):
    _Compare("Map_Copysign", Boundary, N.full(len(Boundary), Sign), len(Boundary))
for Left, Right, Expected in (([5.5, -5.5, 5.5, -5.5], [2.0, 2.0, -2.0, -2.0], 4), ([Smallest * 3, -Smallest * 3], [Smallest * 2, Smallest * 2], 2), ([4.0, -4.0], [2.0, 2.0], 0), ([0.0], [2.0], 0), ([1.0], [0.0], 0), ([1.0], [-0.0], 0), ([1.0], [Smallest], 0)):
    _Compare("Map_Fmod", Left, Right, Expected)
Random = N.random.default_rng(427119)
Left = Random.integers(0, N.iinfo(N.uint64).max, 20000, dtype=N.uint64).view(N.float64)
Right = Random.integers(0, N.iinfo(N.uint64).max, 20000, dtype=N.uint64).view(N.float64)
Valid = N.isfinite(Left) & N.isfinite(Right) & (Left != 0.0) & (Right != 0.0)
Left, Right = Left[Valid], Right[Valid]
_Compare("Map_Copysign", Left, Right, len(Left))
Zero = next((Index for Index, Pair in enumerate(zip(Left, Right)) if math.fmod(*Pair) == 0.0), len(Left))
_Compare("Map_Fmod", Left, Right, len(Left) if Zero == len(Left) else Zero // 4096 * 4096)
for Name in ("Map_Copysign", "Map_Fmod"):
    for Position in (0, 4095, 4096, 5000, 8192):
        for Operand, Bad in ((0, math.nan), (1, math.inf), (0, -0.0), (1, -0.0)):
            Left, Right = N.full(8195, 2.5), N.full(8195, 1.7)
            (Left if Operand == 0 else Right)[Position] = Bad
            _Compare(Name, Left, Right, Position // 4096 * 4096)
    for Left, Right in ((N.full(9, 2.5, dtype=N.float32), N.full(9, 1.7)), (N.full(18, 2.5)[::2], N.full(9, 1.7)), (N.full(9, 2.5)[::-1], N.full(9, 1.7)), (N.full(9, 2.5), N.full(18, 1.7)[::2]), (N.full(9, 2.5), N.full(8, 1.7))):
        _Compare(Name, Left, Right, 0, True)
    Misaligned = N.ndarray((9,), dtype=N.float64, buffer=bytearray(9 * 8 + 1), offset=1)
    Misaligned.fill(2.5)
    Metadata = N.full(9, 2.5, dtype=N.dtype("float64", metadata={"contract": "custom"}))
    class Array_Subclass(N.ndarray):
        pass
    for Left in (Misaligned, Metadata, N.full(9, 2.5).view(Array_Subclass), N.full(9, 2, dtype=N.int64)):
        _Compare(Name, Left, N.full(9, 1.7), 0, True)
    Left, Right = N.full(9, 2.5), N.full(9, 1.7)
    Left.flags.writeable = Right.flags.writeable = False
    _Compare(Name, Left, Right, 9, True)
    for Position in (0, 4095, 4096, 5000, 8192):
        if Name == "Map_Fmod":
            for Bad in (0.0, 2.5):
                Left, Right = N.full(8195, 2.5), N.full(8195, 1.7)
                Right[Position] = Bad
                _Compare(Name, Left, Right, Position // 4096 * 4096)
for Left, Right in (([-1.0, 2.5], [-1.0, 1.7]), ([2.5, 2.5], [-1.0, 1.7]), ([2.5, 2.5], [1.0, 1.7])):
    _Compare("Ordered_Arguments", Left, Right, 0)
_Compare("Nested_Zero", [2.5], [0.0], 0)
Native._Test_Allocation(True)
try:
    _Compare("Map_Copysign", N.full(8195, 2.5), N.full(8195, 1.7), 0)
    _Compare("Map_Fmod", N.full(8195, 2.5), N.full(8195, 1.7), 0)
finally:
    Native._Test_Allocation(False)

def _Callbacks(Module):
    Events = []
    Sentinel = ValueError("binary callback identity")
    Namespace = types.SimpleNamespace()
    def Last(Left, Right):
        Events.append(("last", float(Left).hex(), float(Right).hex()))
        raise Sentinel
    def First(Left, Right):
        Events.append(("first", float(Left).hex(), float(Right).hex()))
        Namespace.copysign = Last
        return math.copysign(Left, Right)
    Namespace.copysign = First
    Saved = Module.math
    try:
        Module.math = Namespace
        Output = N.full(4, -12345.0)
        try:
            Module.Map_Copysign(N.full(4, 2.5), N.full(4, -1.7), Output)
        except Exception as Error:
            assert Error is Sentinel
        else:
            raise AssertionError("callback did not raise")
        return Events, Output.view(N.uint64).tolist()
    finally:
        Module.math = Saved

Before = _Stats("Map_Copysign")
assert _Callbacks(Original) == _Callbacks(Native)
assert _Stats("Map_Copysign") == Before
Comparisons += 1

def _Conversion_Order(Module):
    Events = []
    class Real:
        def __init__(self, Name, Value):
            self.Name, self.Value = Name, Value
        def __float__(self):
            Events.append(self.Name)
            if self.Name == "right2":
                raise ValueError("right conversion")
            return self.Value
    Left = N.array([Real("left" + str(Index), 2.5) for Index in range(4)], dtype=object)
    Right = N.array([Real("right" + str(Index), 1.7) for Index in range(4)], dtype=object)
    Output = N.full(4, -12345.0)
    Result = _Outcome(Module.Map_Fmod, Left, Right, Output)
    return Events, Result, Output.view(N.uint64).tolist()

Before = _Stats("Map_Fmod")
assert _Conversion_Order(Original) == _Conversion_Order(Native)
assert _Stats("Map_Fmod") == Before
Comparisons += 1
Saved_Original, Saved_Native = Original.Float_Remainder, Native.Float_Remainder
try:
    Original.Float_Remainder = Native.Float_Remainder = math.copysign
    _Compare("Aliased", N.full(9, 2.5), N.full(9, 1.7), 0)
finally:
    Original.Float_Remainder, Native.Float_Remainder = Saved_Original, Saved_Native
for Name in ("Map_Copysign", "Map_Fmod"):
    for Slot in (0, 1):
        Expected_Inputs = [N.full(9, 2.5), N.full(9, 1.7)]
        Actual_Inputs = [Value.copy() for Value in Expected_Inputs]
        Before = _Stats(Name)
        assert _Outcome(getattr(Original, Name), *Expected_Inputs, Expected_Inputs[Slot]) == _Outcome(getattr(Native, Name), *Actual_Inputs, Actual_Inputs[Slot])
        assert N.array_equal(Expected_Inputs[Slot].view(N.uint64), Actual_Inputs[Slot].view(N.uint64))
        assert _Stats(Name) == Before
        Comparisons += 1
    for Slot in (0, 1):
        Expected_Buffer, Actual_Buffer = N.full(10, 2.5 if Slot == 0 else 1.7), N.full(10, 2.5 if Slot == 0 else 1.7)
        Expected_Inputs = [N.full(9, 2.5), N.full(9, 1.7)]
        Actual_Inputs = [Value.copy() for Value in Expected_Inputs]
        Expected_Inputs[Slot], Actual_Inputs[Slot] = Expected_Buffer[:-1], Actual_Buffer[:-1]
        Before = _Stats(Name)
        assert _Outcome(getattr(Original, Name), *Expected_Inputs, Expected_Buffer[1:]) == _Outcome(getattr(Native, Name), *Actual_Inputs, Actual_Buffer[1:])
        assert N.array_equal(Expected_Buffer.view(N.uint64), Actual_Buffer.view(N.uint64))
        assert _Stats(Name) == Before
        Comparisons += 1
    Expected, Actual = N.zeros(9), N.zeros(9)
    Expected.flags.writeable = Actual.flags.writeable = False
    Before = _Stats(Name)
    assert _Outcome(getattr(Original, Name), N.full(9, 2.5), N.full(9, 1.7), Expected) == _Outcome(getattr(Native, Name), N.full(9, 2.5), N.full(9, 1.7), Actual)
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
    assert _Stats(Name) == Before
    Comparisons += 1
    Left, Right = N.full(8195, 2.5), N.full(8195, 1.7)
    Before = _Stats(Name)
    with ThreadPoolExecutor(max_workers=1) as Pool:
        Actual = Pool.submit(getattr(Native, Name), Left, Right, N.empty_like(Left)).result()
    Expected = getattr(Original, Name)(Left, Right, N.empty_like(Left))
    assert N.array_equal(Expected.view(N.uint64), Actual.view(N.uint64))
    assert _Stats(Name) == Before
    Comparisons += 1
Saved_Handler = signal.getsignal(signal.SIGINT)
try:
    signal.signal(signal.SIGINT, lambda Number, Frame: None)
    _Compare("Map_Copysign", [2.5], [1.7], 0)
    _Compare("Map_Fmod", [2.5], [1.7], 0)
finally:
    signal.signal(signal.SIGINT, Saved_Handler)
Previous = Native._Test_Rounding(True)
try:
    for Name in Locations:
        _Compare(Name, [2.5], [1.7], 0)
finally:
    Native._Test_Restore_Rounding(Previous)
if Parallel:
    Previous = Native._Test_Rounding(False)
    try:
        Native._Test_Worker_Rounding(True)
        Native._Test_Rounding(False)
        Modes = Native._Test_Worker_Modes()
        assert Modes[0] != Modes[1]
        _Compare("Map_Copysign", N.full(8195, Smallest), N.full(8195, 1.0), 8195)
        _Compare("Map_Fmod", N.full(8195, Smallest * 3), N.full(8195, Smallest * 2), 8195)
        assert Native._Test_Worker_Modes() == Modes
    finally:
        Native._Test_Worker_Rounding(False)
        Native._Test_Restore_Rounding(Previous)
    Controls = Native._Test_Worker_Controls()
    if Controls is not None:
        try:
            Native._Test_Worker_Flush()
            Changed = Native._Test_Worker_Controls()
            assert Changed[1] & 0x8040 == 0x8040
            _Compare("Map_Copysign", N.full(8195, Smallest), N.full(8195, 1.0), 8195)
            _Compare("Map_Fmod", N.full(8195, Smallest * 3), N.full(8195, Smallest * 2), 8195)
            assert Native._Test_Worker_Controls()[1] == Changed[1]
        finally:
            Native._Test_Worker_Restore_Controls(*Controls)
Expected_Names = set(Locations) - {"Float_Negative_Zero_Sign"}
assert Native_Functions == Expected_Names, (Native_Functions, Expected_Names)
assert Parallel_Functions == (Expected_Names if Parallel else set())
if hasattr(Original, "_Pyceler_Marker"):
    assert Native._Pyceler_Marker == Original._Pyceler_Marker == "_Pyceler_literal"
    assert Native.Copy_Sign is Original.Copy_Sign and Native.Float_Remainder is Original.Float_Remainder
print(json.dumps(dict(Comparisons=Comparisons, Exact_Bits=True, Caller_Flags=True, Output_Identity=True, Error_Identity=True, Parallel=Parallel, Native_Functions=sorted(Native_Functions), Parallel_Functions=sorted(Parallel_Functions))))
