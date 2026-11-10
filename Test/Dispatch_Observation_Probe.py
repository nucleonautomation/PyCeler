import importlib.util
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as N

File = Path(sys.argv[1])
Spec = importlib.util.spec_from_file_location("Dispatch_Kernels", File)
Native = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Native)
Statistics = next(Value for Name, Value in vars(Native).items() if Name.startswith("_Pyceler_") and Name.endswith("Dispatch_Stats") and callable(Value))
assert Statistics.__name__.startswith("_Pyceler_X"), Statistics.__name__
Parallel_Families = set()
Serial_Families = set()
Fallbacks = set()

class _Stream:
    def __init__(self, Data):
        self._Data = Data

    def recv(self, Count):
        Part, self._Data = self._Data[:Count], self._Data[Count:]
        return Part

def _Call(Name, Args, Reason, Team, Worker=False):
    Statistics(True, Reset=True)
    Function = getattr(Native, Name)
    if Worker:
        with ThreadPoolExecutor(max_workers=1) as Pool:
            Result = Pool.submit(Function, *Args).result()
    else:
        Result = Function(*Args)
    State = Statistics()
    Execution = State.get("Execution", {})
    assert Execution.get("Reason") == Reason, (Name, Reason, State)
    assert Execution.get("Actual_Team") == Team, (Name, Team, State)
    assert Execution.get("Native_Entry") is (Reason != "python_fallback"), (Name, State)
    if Reason == "native_parallel":
        Parallel_Families.add(Name)
    elif Reason == "native_serial":
        Serial_Families.add(Name)
    else:
        Fallbacks.add(Name)
    State["Execution"]["Reason"] = "mutated snapshot"
    assert Statistics()["Execution"]["Reason"] == Reason
    return Result

Values = N.ones(65536, dtype=N.float64)
Native.Clear_Elements(Values)
assert Statistics() == {}
assert _Call("Clear_Elements", (Values,), "native_parallel", 2) is Values
Values = N.full(32768, -3, dtype=N.int32)
assert _Call("Clip_Negative", (Values,), "native_parallel", 2) is Values and not Values.any()
Source = N.arange(32768, dtype=N.int32) % 11
First, Second = N.zeros_like(Source), N.zeros_like(Source)
assert _Call("Fused_Maps", (Source, First, Second), "native_parallel", 2) is Second
assert N.array_equal(First, Source * 2) and N.array_equal(Second, Source + 5)
Input = N.full((129, 131), 7, dtype=N.int32)
Output = N.zeros_like(Input)
assert _Call("Clipped_Median", (Input, Output), "native_parallel", 2) is Output and N.array_equal(Input, Output)
Distances = N.tile(N.array([3, 1, 4, 2], dtype=N.int32), (4096, 1))
Labels = N.zeros(4096, dtype=N.uint8)
assert _Call("Choose_Labels", (Distances, Labels, 4096, 4), "native_parallel", 2) is Labels
assert N.all(Labels == 1)
Reports = []
assert _Call("Count_Residuals", (N.arange(4096, dtype=N.int32), 17, Reports.append), "native_parallel", 2) == 18
assert Reports == [18]
Points = N.zeros((4096, 2), dtype=N.float64)
Labels = N.full(4096, 3, dtype=N.int32)
Stripes = N.zeros(4096, dtype=N.int32)
assert _Call("Score_Stripes", (Points, 0.0, 0.0, 1.0, 0.0, 0.5, Labels, 3, False, Stripes, 0), "native_parallel", 2) == 4096
Mask = N.ones(Input.shape, dtype=bool)
Expected = N.full(Input.shape, -99, dtype=N.int64)
Expected[1:-1, 1:-1] = 7
assert N.array_equal(_Call("Dispatch_Filter", (Input, Mask, -99), "native_parallel", 2), Expected)
Expected_Total = sum((Index * Index + Index * 7) % 999983 for Index in range(10000))
assert _Call("Modulo_Total", (10000, 999983), "native_parallel", 2) == Expected_Total
assert _Call("Modulo_Total", (10000, 999983), "native_serial", 1, Worker=True) == Expected_Total
assert _Call("Clip_Negative", (N.full(32768, -3, dtype=N.int32),), "native_serial", 1, Worker=True).sum() == 0
Native._Test_Set_Threads(3)
assert _Call("Clip_Negative", (N.full(32768, -3, dtype=N.int32),), "native_parallel", 3).sum() == 0
Native._Test_Set_Threads(2)
Output = bytearray(12)
assert _Call("Load_Fragment", (_Stream(b"abcde"), Output, 1, 4), "native_serial", 1) == bytearray(b"bcde" + b"\x00" * 8)
assert _Call("Read_Exact", (_Stream(b"abcdef"), 6), "native_serial", 1) == b"abcdef"
Values = [4, 7, 9]
assert _Call("Clear_Elements", (Values,), "python_fallback", 0) is Values and Values == [0, 0, 0]
Values = [-4, 7, -9]
assert _Call("Clip_Negative", (Values,), "python_fallback", 0) is Values and Values == [0, 7, 0]
Values = N.arange(8, dtype=N.int32)
Output = N.zeros_like(Values)
assert _Call("Fused_Maps", (Values, Values, Output), "python_fallback", 0) is Output
assert N.array_equal(Output, N.arange(8, dtype=N.int32) * 2 + 5)
Statistics(False, Reset=True)
Native.Clear_Elements(N.ones(65536))
assert Statistics() == {}
Native.type = Native.bool = Native.dict = Native.TypeError = object()
Statistics(True, Reset=True)
assert Statistics() == {}
print(json.dumps(dict(Parallel_Families=len(Parallel_Families), Serial_Families=len(Serial_Families), Fallbacks=len(Fallbacks))))
