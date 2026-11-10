import importlib.util
import math
import random
import sys
import Scalar_Arithmetic as Native

Spec = importlib.util.spec_from_file_location("Original_Scalar_Arithmetic", Reference_Path)
Original = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Original)

def _Outcome(Function, Arguments):
    try:
        Value = Function(*Arguments)
    except Exception as Error:
        return "error", type(Error), str(Error)
    return "value", type(Value), Value.hex() if type(Value) is float else Value

def _Compare(Name, Arguments, Fallback=None):
    Calls = []
    def _Observe(Frame, Event, Value):
        if Event == "call" and Frame.f_code.co_filename == "Scalar_Arithmetic.py" and Frame.f_code.co_name == Name:
            Calls.append(Event)
    Expected = _Outcome(getattr(Original, Name), Arguments)
    sys.setprofile(_Observe)
    try:
        Actual = _Outcome(getattr(Native, Name), Arguments)
    finally:
        sys.setprofile(None)
    assert Actual == Expected, (Name, Arguments, Actual, Expected)
    if Fallback is not None:
        assert len(Calls) == int(Fallback), (Name, Arguments, Calls)

for Name, Arguments, Fallback in (
    ("Modulo_Total", (50000, 999983), False), ("Modulo_Total", (50000, -999983), False),
    ("Modulo_Total", (0, 0), True), ("Modulo_Total", (1, 0), True),
    ("Floor_Total", (1, -(2**63), -1), True), ("Floor_Total", (1, -(2**63), 1), False),
    ("Remainder_Total", (1, -(2**63), -1), False), ("Remainder_Total", (1, -(2**63), 3), False),
    ("Minimum_Remainder", (5,), False), ("Division_Total", (50000, 999983), False),
    ("Division_Total", (0, 0), True), ("Division_Total", (-5, 0), True),
    ("Division_Total", (1, 0), False), ("Division_Total", (4, 0.5), True),
    ("Wide_Division", (1, 2**53 + 1, 3), False), ("Wide_Division", (1, 2**63 - 1, 37), False),
    ("Wide_Division", (1, -(2**63), -1), False), ("Wide_Division", (1, 2**100, 3), True),
    ("Mixed_Division", (100, -(2**61), 13), False), ("Negative_Zero", (1,), False),
    ("Negative_Zero", (0,), True), ("Fractional_Divisor", (50,), False),
    ("Division_Overflow", (5, 2**62, 3), True), ("Division_Overflow", (3, 2**2000, 1), True),
):
    _Compare(Name, Arguments, Fallback)

Generator = random.Random(20261110)
for Index in range(400):
    Left = Generator.choice((-(2**63), 2**63 - 1, -(2**53) - 1, 2**53 + 1, Generator.randrange(-10**12, 10**12)))
    Right = Generator.choice((0, -1, 1, -(2**63), 2**63 - 1, Generator.randrange(-10**12, 10**12)))
    for Name in ("Floor_Total", "Remainder_Total", "Wide_Division", "Mixed_Division"):
        _Compare(Name, (1, Left, Right))

assert math.copysign(1, Native.Negative_Zero(7)) == -1
Native.range = lambda Count: [3, 5]
Original.range = Native.range
_Compare("Modulo_Total", (5, 7), True)
_Compare("Division_Total", (5, 7), True)
print("Scalar arithmetic: 1626 exact comparisons and native/fallback checks passed")
