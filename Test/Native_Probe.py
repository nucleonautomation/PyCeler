import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
import numpy
import Numeric_Loops as Native

Spec = importlib.util.spec_from_file_location("Reference_Loops", Reference_Path)
Reference = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Reference)
Calls = []
def _Record(Frame, Event, Value):
    if Event == "call" and Frame.f_code.co_filename == "Numeric_Loops.py" and Frame.f_code.co_name == "Clear_Elements":
        Calls.append(Event)

sys.setprofile(_Record)
try:
    Native.Clear_Elements(numpy.ones(100003))
    assert Calls == []
    Native.Clear_Elements([1])
    assert Calls == ["call"]
finally:
    sys.setprofile(None)
for Dtype in (numpy.int32, numpy.int64, numpy.float32, numpy.float64):
    for Count in (0, 1, 100003):
        Expected = numpy.full(Count, 17, dtype=Dtype)
        Actual = Expected.copy()
        assert Reference.Clear_Elements(Expected) is Expected
        assert Native.Clear_Elements(Actual) is Actual
        numpy.testing.assert_array_equal(Actual, Expected)
        assert Actual.dtype == Expected.dtype
for Make in (lambda: numpy.arange(10)[::2], lambda: numpy.arange(6).reshape(2, 3),
             lambda: numpy.arange(4, dtype=">i8"), lambda: numpy.arange(7, dtype=numpy.uint16)):
    Expected, Actual = Make(), Make()
    Reference.Clear_Elements(Expected)
    assert Native.Clear_Elements(Actual) is Actual
    numpy.testing.assert_array_equal(Actual, Expected)
for Module in (Reference, Native):
    Read_Only = numpy.ones(4)
    Read_Only.flags.writeable = False
    try:
        Module.Clear_Elements(Read_Only)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected a read-only error")
Values = [2 ** 140, 1, 7]
assert Native.Prefix_Sum(Values.copy()) == Reference.Prefix_Sum(Values.copy())
with ThreadPoolExecutor(max_workers=1) as Pool:
    Array = numpy.ones(120000)
    assert Pool.submit(Native.Clear_Elements, Array).result() is Array
    assert not Array.any()
class Tracked(list):
    def __setitem__(self, Index, Value):
        super().__setitem__(Index, Value + 1)
Array = Tracked([9, 9])
assert Native.Clear_Elements(Array) is Array and Array == [1, 1]
Native.range = lambda Count: [1]
Array = numpy.full(3, 4)
Native.Clear_Elements(Array)
assert Array.tolist() == [4, 0, 4]
