import importlib.util
import random
import sys
from concurrent.futures import ThreadPoolExecutor
import Parallel_Reductions as Native

Spec = importlib.util.spec_from_file_location("Original_Parallel_Reductions", Reference_Path)
Original = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Original)
Comparisons = 0

def _Outcome(Function, Args):
    try:
        Value = Function(*Args)
        return "value", type(Value), Value.hex() if type(Value) is float else Value
    except Exception as Error:
        return "error", type(Error), Error.args

def _Compare(Name, Args, Parallel=None):
    global Comparisons
    Before = Native._Pyceler_Parallel_Stats()[0]
    Serial_Before = Native._Pyceler_Reduction_Stats()["Serial_Calls"]
    Expected = _Outcome(getattr(Original, Name), Args)
    Actual = _Outcome(getattr(Native, Name), Args)
    assert Actual == Expected, (Name, Args, Expected, Actual)
    Comparisons += 1
    Calls, Team = Native._Pyceler_Parallel_Stats()
    if Parallel is not None:
        assert (Calls > Before) is (Parallel and Parallel_Enabled), (Name, Args, Calls, Before)
        if Parallel and Parallel_Enabled:
            assert Team == 2, (Name, Team)
        if Parallel and not Parallel_Enabled:
            Statistics = Native._Pyceler_Reduction_Stats()
            assert Statistics["Serial_Calls"] == Serial_Before + 1, (Name, Args, Statistics)
            assert Statistics["Last_Mode"] == "serial" and Statistics["Last_Team"] == 1, (Name, Args, Statistics)

for Name, Args, Parallel in (
    ("Modulo_Total", (1100000, 999983), True), ("Modulo_Total", (100000, -999983), True),
    ("Signed_Total", (-100000, 100000, 17), True), ("Reverse_Total", (100000, -100000, -7), True),
    ("Constant_Total", (1, -(2**63)), True), ("Constant_Total", (1, 2**63 - 1), True),
    ("Constant_Total", (2, -(2**63)), False), ("Constant_Total", (2, 2**63 - 1), False),
    ("Modulo_Constant", (4, -(2**63), -1), True), ("Floor_Constant", (1, -(2**63), -1), False),
    ("Floor_Constant", (1, -(2**63), 1), True), ("Floor_Constant", (2, 7, 0), False),
    ("Modulo_Total", (0, 0), False), ("Modulo_Total", (-1, 0), False),
    ("Modulo_Total", (10, 0), False), ("Modulo_Total", (10, 1.5), False),
    ("Intermediate_Overflow", (20, 2**40), False), ("Constant_Total", (4, 2**100), False),
    ("Bounds_Division", (100, 0), False), ("Bounds_Division", (100, 3), True),
    ("Constant_Total", (True, 7), False),
    ("Ordered_Float", (1000,), False), ("Dependent_Total", (20,), False), ("Rebound_Index", (1000,), False),
    ("Signed_Total", (2**63 - 7, 2**63 - 1, 2**63 - 7), True),
    ("Reverse_Total", (-(2**63) + 6, -(2**63), 2**62), True),
):
    _Compare(Name, Args, Parallel)

Generator = random.Random(20261110)
for Case in range(300):
    Begin, Stop = Generator.randrange(-60, 61), Generator.randrange(-60, 61)
    Divisor = Generator.choice((0, -1, 1, -7, 13, -(2**63), 2**63 - 1))
    _Compare("Signed_Total", (Begin, Stop, Generator.randrange(-100, 101)))
    _Compare("Reverse_Total", (Begin, Stop, Divisor))
    _Compare("Modulo_Total", (Generator.randrange(-3, 60), Divisor))

Before = Native._Pyceler_Parallel_Stats()[0]
Serial_Before = Native._Pyceler_Reduction_Stats()["Serial_Calls"]
with ThreadPoolExecutor(max_workers=1) as Pool:
    assert Pool.submit(Native.Modulo_Total, 10000, 999983).result() == Original.Modulo_Total(10000, 999983)
assert Native._Pyceler_Parallel_Stats()[0] == Before
assert Native._Pyceler_Reduction_Stats()["Serial_Calls"] == Serial_Before + 1
Native.range = lambda *Args: [2, 7, -3]
Original.range = Native.range
_Compare("Modulo_Total", (100, 13), False)
del Native.range
del Original.range
print(f"Exact integer reductions: {Comparisons} comparisons; OpenMP enabled={Parallel_Enabled}, proof-based serial worker-thread execution and guarded Python fallback verified")
