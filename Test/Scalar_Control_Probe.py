import importlib.util
import json
import random
import sys
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

Native = _Load("Scalar_Control", Path(sys.argv[1]))
Original = _Load("Scalar_Control_Reference", Path(sys.argv[2]))
Statistics = Native._Pyceler_Dispatch_Stats
Comparisons = 0
Native_Entries = set()
Fallbacks = set()

def _Outcome(Function, Arguments):
    try:
        Value = Function(*Arguments)
    except Exception as Error:
        return "error", type(Error), Error.args
    return "value", type(Value), Value

def _Compare(Name, Arguments, Mode=None):
    global Comparisons
    Statistics(True, Reset=True)
    Expected = _Outcome(getattr(Original, Name), Arguments)
    Actual = _Outcome(getattr(Native, Name), Arguments)
    assert Actual == Expected, (Name, Arguments, Actual, Expected)
    Execution = Statistics().get("Execution", {})
    if Mode is not None:
        assert Execution.get("Reason") == Mode, (Name, Arguments, Execution)
    if Execution.get("Reason") == "native_serial":
        Native_Entries.add(Name)
    if Execution.get("Reason") == "python_fallback":
        Fallbacks.add(Name)
    Comparisons += 1

for Name, Arguments in (
    ("Dynamic_Stride", (-5, 100, 3)), ("Dynamic_Stride", (100, -9, -7)),
    ("Dynamic_Division", (-5, 100, 3, 7)), ("Dynamic_Division", (100, -9, -7, 13)),
    ("Stride_Snapshot", (1, 100, 3)), ("For_Else", (100, -1)),
    ("For_Else", (100, 4)), ("For_Else", (0, -1)),
    ("While_Else", (100, -1)), ("While_Else", (100, 4)),
    ("Nested_Else", (7, 9, 4)), ("Nested_Else", (7, 9, -1)),
    ("Early_Return", (100, 70)), ("Early_Constant", (100, 3)),
    ("Tuple_Fibonacci", (50,)), ("Chained_And_Conditional", (100, 3, 27)),
    ("Integer_Operators", (100, 3, 13)), ("Integer_Powers", (100, 3)),
    ("Nested_Early_Return", (10, 20, 200)), ("Conditional_Zero", (1, 0)),
):
    _Compare(Name, Arguments, "native_serial")

for Name, Arguments in (
    ("Dynamic_Stride", (0, 1, 0)), ("Dynamic_Stride", (2**63 - 1, 2**63, 1)),
    ("Dynamic_Division", (0, 1, 0, 7)), ("Dynamic_Division", (0, 0, 3, 0)),
    ("Dynamic_Stride", (0, 5, True)), ("Dynamic_Stride", (0, 5, 1.5)),
    ("Stride_Snapshot", (0, 2**100, 2**99)), ("Integer_Operators", (2, -1, 13)),
    ("Integer_Operators", (3, 100, 13)), ("Integer_Powers", (3, -1)),
    ("Integer_Powers", (20, 30)), ("Tuple_Fibonacci", (100,)),
):
    _Compare(Name, Arguments, "python_fallback")

Generator = random.Random(20261111)
for Case in range(200):
    Begin, End = Generator.randrange(-100, 100), Generator.randrange(-100, 100)
    Step = Generator.choice((-13, -3, -1, 0, 1, 3, 13))
    _Compare("Dynamic_Stride", (Begin, End, Step))
    _Compare("Stride_Snapshot", (Begin, End, Step))
    _Compare("Dynamic_Division", (Begin, End, Step, Generator.randrange(-5, 6)))
    Count, Break_At = Generator.randrange(0, 30), Generator.randrange(-1, 31)
    _Compare("For_Else", (Count, Break_At))
    _Compare("While_Else", (Count, Break_At))
    _Compare("Early_Return", (Count, Break_At))
    _Compare("Early_Constant", (Count, Break_At))
    _Compare("Chained_And_Conditional", (Count, Begin, End))
    _Compare("Integer_Operators", (Count, Generator.randrange(0, 7), Generator.randrange(-1000, 1000)))
    _Compare("Integer_Powers", (Count, Generator.randrange(0, 7)))

for Name, Arguments in (("Unbound_After_Empty", (0,)), ("Else_Unbound", (3,)), ("Conditional_Zero", (2, 0))):
    _Compare(Name, Arguments)
Value = int("9876543210")
assert Native.Identity_Early(3, Value) is Value
assert Native.Identity_Tuple(3, Value) is Value
Original.range = lambda *Arguments: [7, 11]
Native.range = Original.range
_Compare("Dynamic_Stride", (0, 20, 3), "python_fallback")
_Compare("For_Else", (100, -1), "python_fallback")
Statistics(False)
print(json.dumps(dict(Comparisons=Comparisons, Native_Families=sorted(Native_Entries), Fallback_Families=sorted(Fallbacks))))
