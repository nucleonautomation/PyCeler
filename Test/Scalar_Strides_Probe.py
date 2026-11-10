import importlib.util
import struct
import Scalar_Strides as Native

Spec = importlib.util.spec_from_file_location("Original_Strides", Reference_Path)
Original = importlib.util.module_from_spec(Spec)
Spec.loader.exec_module(Original)

def _Observe(Module, Name, Begin, End, Callback=None):
    Events = []
    try:
        Result = getattr(Module, Name)(Begin, End, Events, *(() if Callback is None else (Callback,)))
    except Exception as Error:
        return type(Error), str(Error), Events
    return type(Result), Result, Events

def _Keep(Index, Total):
    return Total

def _Change(Index, Total):
    return Total * 2 + Index

def _Bigint(Index, Total):
    return Total + 2**80

def _Fraction(Index, Total):
    return Total + 0.5

def _Break(Index, Total):
    return -777

def _Continue(Index, Total):
    return -888

def _Fail(Index, Total):
    raise LookupError("stride callback")

def _Check(Name, Begin, End, Callback=None):
    Expected = _Observe(Original, Name, Begin, End, Callback)
    Before = Native._Pyceler_Region_Stats()
    Actual = _Observe(Native, Name, Begin, End, Callback)
    After = Native._Pyceler_Region_Stats()
    assert Actual == Expected, (Name, Begin, End, Callback, Expected, Actual)
    return Before, After

assert Native.Module_Result == Original.Module_Result
for Step in (-7, -4, -3, -2, -1, 1, 2, 3, 4, 7):
    Name = "Stride_" + ("Minus_" if Step < 0 else "Plus_") + str(abs(Step))
    for Begin in range(-19, 20, 4):
        for End in range(-19, 20, 4):
            Before, After = _Check(Name, Begin, End, _Keep)
            if range(Begin, End, Step):
                assert After[0] > Before[0] and After[1] == Before[1], (Name, Begin, End, Before, After)
            else:
                assert After == Before, ("empty range entered a native span", Name, Begin, End)
    for Callback in (_Change, _Bigint, _Fraction, _Break, _Continue, _Fail):
        Begin, End = (-19, 40) if Step > 0 else (19, -40)
        _Check(Name, Begin, End, Callback)
    for Begin in (2**63 - 1, -(2**63), 2**80, -(2**80)):
        End = Begin + 3 * Step
        Before, After = _Check(Name, Begin, End, _Keep)
        assert After[1] > Before[1], ("overflow did not use Python fallback", Name, Begin, End)
for Begin in (-19, -7, 0, 1, 7, 19):
    for End in (-19, -7, 0, 1, 7, 19):
        _Check("Fraction", Begin, End)
        Expected = _Observe(Original, "Fraction", Begin, End)[2]
        Actual = _Observe(Native, "Fraction", Begin, End)[2]
        for Reference, Result in zip(Expected, Actual):
            for Left, Right in zip(Reference, Result):
                if type(Left) is float:
                    assert struct.pack("!d", Left) == struct.pack("!d", Right), (Begin, End, Left, Right)
for Replacement in (lambda *Arguments: [9, 6, -12, 3], lambda *Arguments: range(30, -21, -3)):
    Original.range = Replacement
    Native.range = Replacement
    Before, After = _Check("Stride_Plus_2", 0, 99, _Keep)
    assert After[0] == Before[0] and After[1] > Before[1], (Before, After)
del Original.range
del Native.range
print("Scalar positive/negative stride, periodic boundary, callback, overflow and floating checks passed.")
