import importlib.util
import sys
import numpy as Numpy
import Loop_Workloads as Native

Spec = importlib.util.spec_from_file_location("Original_Loops", Reference_Path)
Original = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Original)

def _Invoke(Function, Args, Fallback):
    Calls = []
    def _Observe(Frame, Event, Value):
        if Event == "call" and Frame.f_code.co_filename == "Loop_Workloads.py" and Frame.f_code.co_name == Function.__name__:
            Calls.append(Event)
    sys.setprofile(_Observe)
    try:
        Result = Function(*Args)
    finally:
        sys.setprofile(None)
    assert len(Calls) == int(Fallback), (Function.__name__, Calls)
    return Result

for Name, Args, Fallback in (
    ("Count_Pairs", (18, 23), False), ("Count_Pairs", (0, 5), False), ("Count_Pairs", (-1, 4), False),
    ("Count_Pairs", (True, 5), True), ("Count_Pairs", (0, 2**100), True),
    ("Count_Triangle", (53,), False), ("Count_Triangle", (0,), False),
    ("First_Fibonacci_At_Least", (4321,), False), ("First_Fibonacci_At_Least", (2**62,), False),
    ("First_Fibonacci_At_Least", (2**63 - 1,), True),
    ("Range_Snapshot", (0,), False), ("Range_Snapshot", (7,), False),
    ("Checked_Product", (1, 2**62, 2), True), ("Checked_Product", (1, -(2**63), -1), True),
    ("Checked_Product", (1, -(2**63), 1), False), ("Checked_Product", (1, 2**63 - 1, -1), True),
    ("Checked_Product", (4, -56, -19), False), ("Checked_Product", (2, 3.5, 2), True),
):
    Expected = getattr(Original, Name)(*Args)
    Actual = _Invoke(getattr(Native, Name), Args, Fallback)
    assert Actual == Expected and type(Actual) is type(Expected), (Name, Args)
for Shape in ((0, 4, 2), (3, 0, 4), (2, 3, 0), (5, 7, 13), (12, 48, 64)):
    Values = Numpy.arange(Numpy.prod(Shape), dtype=Numpy.int32).reshape(Shape)
    Expected = Original.Threshold_Volume(Values, Numpy.empty_like(Values), 19)
    Output = Numpy.empty_like(Values)
    assert _Invoke(Native.Threshold_Volume, (Values, Output, 19), False) is Output
    Numpy.testing.assert_array_equal(Output, Expected)
Batch = Numpy.zeros((2, 3, 4, 5), dtype=Numpy.float32)
assert _Invoke(Native.Fill_Batch, (Batch,), False) is Batch
assert (Batch == 5).all()
Storage = Numpy.arange(25, dtype=Numpy.int64)
Expected = Storage.copy()
Original.Threshold_Volume(Expected[:-1].reshape(2, 3, 4), Expected[1:].reshape(2, 3, 4), 4)
_Invoke(Native.Threshold_Volume, (Storage[:-1].reshape(2, 3, 4), Storage[1:].reshape(2, 3, 4), 4), True)
Numpy.testing.assert_array_equal(Storage, Expected)
Native.range = lambda Count: [4]
assert _Invoke(Native.Count_Pairs, (2, 3), True) == 15
