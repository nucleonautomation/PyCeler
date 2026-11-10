import importlib.util
import socket
import sys
from pathlib import Path
import numpy as Numpy

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

class _Stream:
    def __init__(self, Chunks):
        self._Chunks = iter(Chunks)
        self._Events = []

    def recv(self, Size):
        self._Events.append(("read", Size))
        Value = next(self._Chunks)
        if isinstance(Value, BaseException):
            raise Value
        return Value

    def sendall(self, Buffer):
        self._Events.append(("write", bytes(Buffer)))

def _Read_Cases(Module):
    assert Module.Read_Frame(_Stream([b"a", SystemExit()]), 3) is None
    try:
        Module.Read_Exact(_Stream([b"a", SystemExit()]), 3)
    except SystemExit:
        pass
    else:
        raise AssertionError("the narrower handler must propagate SystemExit")
    for Need, Chunks, Expected, Requests in (
            (0, [], b"", []), (6, [b"a", b"bc", b"def"], b"abcdef", [6, 5, 3]),
            (5, [b"a", b"b", b""], None, [5, 4, 3]), (5, [b"x", OSError()], None, [5, 4]),
            (4, [b"a", bytearray(b"b"), b"c", b"d"], b"abcd", [4, 3, 2, 1])):
        Stream = _Stream(Chunks)
        assert Module.Read_Exact(Stream, Need) == Expected
        assert Stream._Events == [("read", Size) for Size in Requests]
    Stream = _Stream([b"a", socket.timeout("late")])
    try:
        Module.Read_Exact(Stream, 3)
    except socket.timeout as Error:
        assert Error.args == ("late",)
    else:
        raise AssertionError("timeout was swallowed")
    assert Stream._Events == [("read", 3), ("read", 2)]
    Read, Write = socket.socketpair()
    with Read, Write:
        Read.settimeout(0.02)
        try:
            Module.Read_Exact(Read, 1)
        except socket.timeout:
            pass
        else:
            raise AssertionError("socket timeout must propagate")
        Read.settimeout(2)
        Write.sendall(b"abcde")
        Write.shutdown(socket.SHUT_WR)
        assert Module.Read_Exact(Read, 4) == b"abcd"
        assert Module.Read_Exact(Read, 2) is None

def _Buffers(Module):
    Target = bytearray(b"xxxxxxx")
    Stream = _Stream([b".abcd"])
    assert Module.Load_Fragment(Stream, Target, 1, 4) is Target and Target == b"abcd\x00\x00\x00"
    assert Stream._Events == [("read", 5)]
    Source = memoryview(b"..abcde")[1:]
    assert Module.Load_Fragment(_Stream([Source]), Target, 1, 4) == b"abcd\x00\x00\x00"
    Source.release()
    assert Module.Load_Fragment(_Stream([Source]), Target, 0, 0) == bytes(7)
    Stream = _Stream([b".ab"])
    try:
        Module.Load_Fragment(Stream, Target, 1, 4)
    except IndexError:
        assert Target[:2] == b"ab" and Stream._Events == [("read", 5)]
    else:
        raise AssertionError("short input must preserve the partial write and exception")
    Target = bytearray(2048)
    Data = b"k" * len(Target)
    Stream = _Stream([Data, BlockingIOError()])
    def _Notify(Values):
        Stream._Events.append(("callback", bytes(Values)))
    assert Module.Pump(Stream, Target, _Notify) is Target and Target == Data
    assert Stream._Events == [("read", 2048), ("callback", Data), ("write", Data), ("read", 2048)]

def _Scoring(Module):
    for Width in (0, 1, 9, 256):
        Values = ((Numpy.arange(512 * Width) % 7) - 3).astype(Numpy.float32).reshape(512, Width)[:, ::-1]
        Values.flags.writeable = False
        Labels = Numpy.full(512, 255, dtype=Numpy.uint8)
        assert Module.Choose_Labels(Values, Labels, 512, Width) is Labels
        Numpy.testing.assert_array_equal(Labels, Values.argmin(axis=1) if Width else Numpy.zeros(512))
    Data = Numpy.array([[2.0, 0.0, 0.0], [1.0, Numpy.nan, 0.0]], dtype=Numpy.float32)
    for Rows, Width in ((2, 3), (1, 2)):
        Expected = Reference.Choose_Labels(Data, Numpy.full(2, 255, dtype=Numpy.uint8), Rows, Width)
        Numpy.testing.assert_array_equal(Module.Choose_Labels(Data, Numpy.full(2, 255, dtype=Numpy.uint8), Rows, Width), Expected)
    Values = Numpy.zeros((2, 257), dtype=Numpy.int32)
    Values[1, -1] = -1
    Labels = Numpy.full(2, 255, dtype=Numpy.uint8)
    try:
        Expected = Reference.Choose_Labels(Values, Labels.copy(), 2, 257)
    except OverflowError:
        try:
            Module.Choose_Labels(Values, Labels, 2, 257)
        except OverflowError:
            assert Labels.tolist() == [0, 255]
        else:
            raise AssertionError("unrepresentable index")
    else:
        Numpy.testing.assert_array_equal(Module.Choose_Labels(Values, Labels, 2, 257), Expected)
    for Dtype in (Numpy.float32, Numpy.float64):
        Points = (Numpy.arange(14400).reshape(7200, 2) % 97).astype(Dtype)[::2]
        Indices = Numpy.arange(len(Points) - 1, -1, -2, dtype=Numpy.int64)
        Labels = Numpy.arange(len(Points), dtype=Numpy.int32) % 3
        Model = (1.0, 2.0, -0.5, 0.75, 3.0, 1)
        for Flag, Supplied in ((False, None), (True, Labels)):
            Direct = Module.Score_Stripes(Points, 1.0, 2.0, -0.5, 0.75, 3.0, Labels, 1, Flag, Supplied, 1)
            assert Direct == sum(abs((float(X) - 1) * -0.5 + (float(Y) - 2) * 0.75) <= 3 for (X, Y), L in zip(Points, Labels) if L == 1)
            Expected = sum(abs((float(Points[I, 0]) - 1) * -0.5 + (float(Points[I, 1]) - 2) * 0.75) <= 3
                           for I in Indices if not Flag or Labels[I] == 1)
            assert Module.Evaluate_Models(Points, Indices, [Model, Model], Supplied, Flag) == (Expected, 0)
        assert Module.Evaluate_Models(Points, Numpy.array([-1, 0]), [Model], Labels, True) == Reference.Evaluate_Models(Points, Numpy.array([-1, 0]), [Model], Labels, True)
        try:
            Module.Evaluate_Models(Points, Numpy.array([0, len(Points)]), [Model], None, False)
        except IndexError:
            pass
        else:
            raise AssertionError("invalid gather index")
    Calls = []
    Errors = Numpy.arange(5000, dtype=Numpy.int64)[::2]
    assert Module.Count_Residuals(Errors, 100, Calls.append) == 51 and Calls == [51]
    assert Module.Partial_Count([1, 2, "x"], 2) == 2
    assert Module.Visible_Counter([7, 8], [0, 0]) == 1
    A = Numpy.arange(96 * 33, dtype=Numpy.int32).reshape(96, 33)
    Out = Numpy.zeros_like(A)
    Seen = []
    def _Convert(Frame):
        Seen.append(Frame)
        return A, Out
    assert Module.Frame_Processor().Process(_Convert, "frame", 8) is Out
    assert Seen == ["frame"]
    Numpy.testing.assert_array_equal(Out, A + 8)
    for Rows in (0, 3, 96, 97):
        Target = Numpy.full(A.shape, -1, dtype=Numpy.int32)
        try:
            Module.Copy_Rows(A, Target, Rows)
        except IndexError:
            assert Rows == 97
        else:
            assert Rows <= 96
        Numpy.testing.assert_array_equal(Target[:Rows], A[:Rows])
        assert (Target[Rows:] == -1).all()

def _Filter(Module):
    for Dtype in (Numpy.int32, Numpy.int16, Numpy.uint8, Numpy.uint16, Numpy.float64):
        Frame = (Numpy.arange(73 * 91).reshape(73, 91) % 97).astype(Dtype)[::-1, ::2]
        Frame.flags.writeable = False
        Valid = Numpy.full(Frame.shape, True)
        Valid[::8, 3::5] = False
        Expected = Reference.Sobel_East(Frame, Valid, -999)
        Actual = Module.Sobel_East(Frame, Valid, -999)
        Numpy.testing.assert_array_equal(Actual, Expected)
        assert Actual.dtype == Numpy.int64
    Tiny = Numpy.ones((1, 1), dtype=Numpy.int32)
    assert Module.Sobel_East(Tiny, Tiny.astype(bool), -7)[0, 0] == -7

Source, Binary = (Path(Value) for Value in sys.argv[1:3])
Reference = _Load("Classic_Reference", Source)
Native = _Load(Binary.stem, Binary)
for Module in (Reference, Native):
    _Read_Cases(Module)
    _Buffers(Module)
    _Scoring(Module)
    _Filter(Module)
