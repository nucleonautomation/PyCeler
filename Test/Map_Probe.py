import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
import numpy as Numpy
import Map_Loops as Native

Spec = importlib.util.spec_from_file_location("Reference_Maps", Reference_Path)
Reference = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Reference)

def _Call(Function, Args, Index, Fallback):
    Calls = []
    def _Observe(Frame, Event, Value):
        if Event == "call" and Frame.f_code.co_filename == "Map_Loops.py" and Frame.f_code.co_name == Function.__name__:
            Calls.append(Event)
    sys.setprofile(_Observe)
    try:
        Result = Function(*Args)
    finally:
        sys.setprofile(None)
    assert Result is Args[Index]
    assert bool(Calls) == Fallback, (Function.__name__, Calls)
    return Result

for Dtype in (Numpy.int32, Numpy.int64, Numpy.float32, Numpy.float64):
    Source = (Numpy.arange(65536, dtype=Dtype) % 19 - 9).reshape(256, 256)
    Source.flags.writeable = False
    for Name, Extra in (("Copy_Grid", ()), ("Threshold_Grid", (4,))):
        Actual = Numpy.empty_like(Source)
        Expected = Numpy.empty_like(Source)
        getattr(Reference, Name)(Source, Expected, *Extra)
        _Call(getattr(Native, Name), (Source, Actual, *Extra), 1, False)
        Numpy.testing.assert_array_equal(Actual, Expected)
    for Shape in ((0, 3), (3, 0), (1, 1), (51, 73)):
        Actual = Numpy.empty(Shape, dtype=Dtype)
        _Call(Native.Fill_Grid, (Actual, -7), 0, False)
        Numpy.testing.assert_array_equal(Actual, Numpy.full(Shape, -7, dtype=Dtype))
    Values = Source.ravel().copy()
    Expected = Reference.Clip_Negative(Values.copy())
    _Call(Native.Clip_Negative, (Values,), 0, False)
    Numpy.testing.assert_array_equal(Values, Expected)
    Left, Right, Actual = Source.ravel(), Values, Values.copy()
    _Call(Native.Select, (Left, Right, Actual), 2, False)
    Numpy.testing.assert_array_equal(Actual, Reference.Select(Left, Right, Numpy.empty_like(Actual)))
    _Call(Native.Difference, (Left, Right, Actual), 2, False)
    Numpy.testing.assert_array_equal(Actual, Reference.Difference(Left, Right, Numpy.empty_like(Actual)))
    _Call(Native.Blend, (Left, Right, Actual, 2), 2, Dtype in (Numpy.float32, Numpy.float64))
    Numpy.testing.assert_array_equal(Actual, Reference.Blend(Left, Right, Numpy.empty_like(Actual), 2))

Base = Numpy.arange(9, dtype=Numpy.int64)
for Dtype in (Numpy.int8, Numpy.uint8, Numpy.int16, Numpy.uint16):
    Pixels = (Numpy.arange(256 * 256) % 19).astype(Dtype).reshape(256, 256)
    Target = Numpy.empty_like(Pixels)
    _Call(Native.Threshold_Grid, (Pixels, Target, 7), 1, False)
    Numpy.testing.assert_array_equal(Target, Pixels >= 7)
    _Call(Native.Add_In_Place, (Pixels.ravel(), 2), 0, False)
    assert Pixels[0, 0] == 2
    Maximum = int(Numpy.iinfo(Dtype).max)
    _Call(Native.Threshold_Grid, (Pixels, Target, Maximum + 1), 1, True)
    assert not Target.any()
    for Module in (Reference, Native):
        Data = Numpy.array([0, Maximum], dtype=Dtype)
        with Numpy.errstate(over="raise"):
            try:
                Module.Add_In_Place(Data, 1)
            except FloatingPointError:
                assert Data.tolist() == [1, Maximum]
            else:
                raise AssertionError("narrow pixel overflow")
Expected = Base.copy()
Reference.Copy_Grid(Expected[:-1].reshape(2, 4), Expected[1:].reshape(2, 4))
_Call(Native.Copy_Grid, (Base[:-1].reshape(2, 4), Base[1:].reshape(2, 4)), 1, True)
Numpy.testing.assert_array_equal(Base, Expected)
Grid = Numpy.arange(9, dtype=Numpy.int32).reshape(3, 3)
_Call(Native.Copy_Grid, (Grid, Grid), 1, False)
_Call(Native.Copy_Grid, (Grid.T, Numpy.empty_like(Grid)), 1, True)
_Call(Native.Copy_Grid, (Grid, Numpy.empty(Grid.shape, dtype=Numpy.int64)), 1, True)
for Module in (Native, Reference):
    Small = Numpy.full((1, 3), -1, dtype=Numpy.int32)
    try:
        Module.Copy_Grid(Grid, Small)
    except IndexError:
        pass
    else:
        raise AssertionError("Expected a short destination error after the first row")
    assert Small.tolist() == [Grid[0].tolist()]
    Read_Only = Grid.copy()
    Read_Only.flags.writeable = False
    try:
        Module.Fill_Grid(Read_Only, 3)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected a read-only destination error")

class Shape_Tracker:
    def __init__(self):
        self.Queries = 0
        self.Grid = Numpy.ones((1, 2), dtype=Numpy.int32)

    @property
    def shape(self):
        self.Queries += 1
        return self.Grid.shape

    def __getitem__(self, Key):
        return self.Grid[Key]

Tracker = Shape_Tracker()
Tracked_Output = Numpy.empty((1, 2), dtype=Numpy.int32)
_Call(Native.Copy_Grid, (Tracker, Tracked_Output), 1, True)
assert Tracker.Queries == 1 and Tracked_Output.tolist() == [[1, 1]]
for Dtype in (Numpy.int32, Numpy.int64):
    Maximum = Numpy.iinfo(Dtype).max
    for Module in (Reference, Native):
        Values = Numpy.array([1, Maximum], dtype=Dtype)
        with Numpy.errstate(over="raise"):
            try:
                Module.Add_In_Place(Values, 1)
            except FloatingPointError:
                pass
            else:
                raise AssertionError("Expected scalar integer overflow")
        assert Values.tolist() == [2, Maximum]
    with Numpy.errstate(over="ignore"):
        Left = Numpy.array([Maximum], dtype=Dtype)
        Right = Numpy.array([-Maximum], dtype=Dtype)
        Actual = Numpy.empty_like(Left)
        _Call(Native.Blend, (Left, Right, Actual, 2), 2, True)
        Numpy.testing.assert_array_equal(Actual, Reference.Blend(Left, Right, Numpy.empty_like(Left), 2))
Floats = Numpy.array([[-0.0, Numpy.nan, Numpy.inf]], dtype=Numpy.float64)
Copy = Numpy.empty_like(Floats)
_Call(Native.Copy_Grid, (Floats, Copy), 1, False)
Numpy.testing.assert_array_equal(Copy.view(Numpy.uint64), Floats.view(Numpy.uint64))
_Call(Native.Threshold_Grid, (Floats, Copy, 1), 1, True)
Numpy.testing.assert_array_equal(Copy, Reference.Threshold_Grid(Floats, Numpy.empty_like(Copy), 1))
for Dtype in (Numpy.float32, Numpy.float64):
    Source = Numpy.array([-0.0, 0.5, 4.5], dtype=Dtype)
    Result = Numpy.empty_like(Source)
    _Call(Native.Scale, (Source, Result), 1, Dtype is Numpy.float32)
    Expected = Reference.Scale(Source, Numpy.empty_like(Source))
    assert Result.tobytes() == Expected.tobytes()
    _Call(Native.Threshold_Grid, (Source.reshape(1, 3), Result.reshape(1, 3), 0.5), 1, False)
    assert Result.tolist() == [0, 1, 1]
    Maximum = Numpy.finfo(Dtype).max
    for Module in (Native, Reference):
        Left = Numpy.array([1., Maximum], dtype=Dtype)
        Right = Numpy.array([0.5, -Maximum], dtype=Dtype)
        Result = Numpy.zeros_like(Left)
        with Numpy.errstate(over="raise"):
            try:
                Module.Difference(Left, Right, Result)
            except FloatingPointError:
                pass
            else:
                raise AssertionError("Expected floating-point overflow")
        assert Result.tolist() == [0.5, 0.0]
with ThreadPoolExecutor(max_workers=1) as Pool:
    Grid = Numpy.zeros((256, 256), dtype=Numpy.int32)
    assert Pool.submit(Native.Fill_Grid, Grid, 7).result() is Grid
    assert (Grid == 7).all()
Native.range = lambda Count: [0]
Grid = Numpy.zeros((2, 2), dtype=Numpy.int32)
_Call(Native.Fill_Grid, (Grid, 3), 0, True)
assert Grid.tolist() == [[3, 0], [0, 0]]
