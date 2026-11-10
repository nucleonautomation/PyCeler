import importlib.util
import sys
import warnings
from pathlib import Path
import numpy as np
import Structural_Loops as Native

def _Reference():
    Spec = importlib.util.spec_from_file_location("Structural_Reference", Path(Reference_Path))
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Observe(Function, Factory):
    Args = Factory()
    with warnings.catch_warnings(record=True) as Captured:
        warnings.simplefilter("always")
        try:
            Result = Function(*Args)
            Returned = (Result.dtype.str, Result.shape, Result.tobytes()) if isinstance(Result, np.ndarray) else Result
            Outcome = ("return", tuple(Index for Index, Value in enumerate(Args) if Result is Value), Returned)
        except Exception as Error:
            Outcome = ("raise", type(Error).__name__, str(Error))
    State = tuple((Value.dtype.str, Value.shape, Value.tobytes()) if isinstance(Value, np.ndarray) else Value for Value in Args)
    return Outcome, State, tuple((Item.category.__name__, str(Item.message)) for Item in Captured)

def _Check(Reference, Name, Factory):
    Expected = _Observe(getattr(Reference, Name), Factory)
    Actual = _Observe(getattr(Native, Name), Factory)
    assert Actual == Expected, (Name, Expected, Actual)

def _Native_Call(Name, Args):
    Calls = []
    def _Profile(Frame, Event, Value):
        if Event == "call" and Frame.f_code.co_filename == "Structural_Loops.py" and Frame.f_code.co_name == Name:
            Calls.append(Event)
    sys.setprofile(_Profile)
    try:
        getattr(Native, Name)(*Args)
    finally:
        sys.setprofile(None)
    assert not Calls, (Name, "Eligible input unexpectedly used Python fallback")

def _Alias():
    Values = np.array([3, 4, 5], dtype=np.int32)
    return Values, Values, np.zeros(3, dtype=np.int32), 1

def _Overlap():
    Values = np.arange(12, dtype=np.int32)
    return Values[:-1], Values[1:], np.zeros(11, dtype=np.int32)

def _Augmented_Alias():
    Values = np.arange(12, dtype=np.int32)
    return Values, Values, Values

def _Run():
    Reference = _Reference()
    Source = np.arange(32, dtype=np.int32) % 7
    for Name, Extra, Outputs in (("Fused_Maps", (), 2), ("Repeated_Scores", (1,), 2), ("Local_Values", (), 2),
                                  ("Versioned_Reads", (), 2), ("Invariant_Scale", (2, 3), 1), ("Temporary_Pipeline", (2, 3), 1),
                                  ("Implicit_Fusion", (), 2), ("Explicit_None", (2, 3), 1), ("Augmented_Outputs", (), 2),
                                  ("Augmented_Locals", (), 1), ("Sequential_Updates", (), 1)):
        _Native_Call(Name, (Source, *(np.zeros_like(Source) for Index in range(Outputs)), *Extra))
    _Native_Call("Column_First", (np.ones((3, 7), dtype=np.int32), np.zeros((3, 7), dtype=np.int32)))
    for Name, Args in (("Augmented_Outputs", (Source, np.zeros_like(Source), np.ones_like(Source))),
                       ("Augmented_Locals", (Source, np.zeros_like(Source))),
                       ("Sequential_Updates", (Source, np.zeros_like(Source))),
                       ("Independent_Updates", (np.zeros_like(Source), np.ones_like(Source)))):
        Large = tuple(np.tile(Value, 2048) for Value in Args)
        Expected = tuple(Value.copy() for Value in Large)
        getattr(Reference, Name)(*Expected)
        _Native_Call(Name, Large)
        assert all(Left.tobytes() == Right.tobytes() for Left, Right in zip(Large, Expected)), Name
    for Dtype in (np.float32, np.float64):
        Input = np.arange(32, dtype=Dtype) % 7
        _Native_Call("Fused_Maps", (Input, np.zeros_like(Input), np.zeros_like(Input)))
        _Native_Call("Local_Values", (Input, np.zeros_like(Input), np.zeros_like(Input)))
        for Name in ("Invariant_Scale", "Explicit_None"):
            _Check(Reference, Name, lambda: (np.array([-3, 0, 3], dtype=Dtype), np.zeros(3, dtype=Dtype), 0, -3))
    for Dtype in (np.int8, np.uint8, np.int16, np.uint16, np.int32, np.int64, np.float32, np.float64):
        for Size in (0, 1, 17, 4096):
            Base = lambda: (np.arange(Size, dtype=np.int64) % 7).astype(Dtype)
            Output = lambda: np.zeros(Size, dtype=Dtype)
            _Check(Reference, "Fused_Maps", lambda: (Base(), Output(), Output()))
            _Check(Reference, "Repeated_Scores", lambda: (Base(), Output(), Output(), 1))
            _Check(Reference, "Local_Values", lambda: (Base(), Output(), Output()))
            _Check(Reference, "Versioned_Reads", lambda: (Base(), Output(), Output()))
            _Check(Reference, "Invariant_Scale", lambda: (Base(), Output(), 2, 3))
            _Check(Reference, "Temporary_Pipeline", lambda: (Base(), Output(), 2, 3))
            _Check(Reference, "Implicit_Fusion", lambda: (Base(), Output(), Output()))
            _Check(Reference, "Explicit_None", lambda: (Base(), Output(), 2, 3))
            _Check(Reference, "Augmented_Outputs", lambda: (Base(), Base(), Base()))
            _Check(Reference, "Augmented_Locals", lambda: (Base(), Output()))
            _Check(Reference, "Sequential_Updates", lambda: (Base(), Output()))
            _Check(Reference, "Independent_Updates", lambda: (Base(), Base()))
    for Shape in ((0, 5), (4, 0), (1, 1), (3, 17), (64, 32)):
        _Check(Reference, "Column_First", lambda: (np.ones(Shape, dtype=np.int32), np.zeros(Shape, dtype=np.int32)))
    _Check(Reference, "Repeated_Scores", _Alias)
    _Check(Reference, "Fused_Maps", _Overlap)
    _Check(Reference, "Augmented_Outputs", _Overlap)
    _Check(Reference, "Augmented_Outputs", _Augmented_Alias)
    _Check(Reference, "Augmented_Outputs", lambda: (np.arange(4, dtype=np.int32), np.zeros(4, dtype=np.int32), np.zeros(1, dtype=np.int32)))
    _Check(Reference, "Sequential_Updates", lambda: (np.array([1, 2147483647], dtype=np.int32), np.zeros(2, dtype=np.int32)))
    _Check(Reference, "Augmented_Locals", lambda: (np.array([0.25, -0.0, np.nan, np.inf]), np.zeros(4)))
    for Name in ("Unsafe_Local_Reduction", "Unsafe_Index_Update"):
        _Check(Reference, Name, lambda: (np.arange(4, dtype=np.int32), np.zeros(4, dtype=np.int32)))
    Outcomes = [_Observe(Module.Uninitialized_Local, lambda: (np.arange(4, dtype=np.int32), np.zeros(4, dtype=np.int32))) for Module in (Reference, Native)]
    assert Outcomes[0] == Outcomes[1], Outcomes
    Original = ((np.dtype(np.int32).str, (4,), np.arange(4, dtype=np.int32).tobytes()),
                (np.dtype(np.int32).str, (4,), np.zeros(4, dtype=np.int32).tobytes()))
    for Outcome, State, Warnings in Outcomes:
        assert Outcome[:2] == ("raise", "UnboundLocalError") and "Value" in Outcome[2], Outcome
        assert State == Original and not Warnings, (State, Warnings)
    _Check(Reference, "Fused_Maps", lambda: (np.arange(4, dtype=np.int32), np.zeros(4, dtype=np.int32), np.zeros(1, dtype=np.int32)))
    _Check(Reference, "Implicit_Fusion", lambda: (np.arange(4, dtype=np.int32), np.zeros(4, dtype=np.int32), np.zeros(1, dtype=np.int32)))
    _Check(Reference, "Fused_Maps", lambda: (np.array([1, 2, 2147483647], dtype=np.int32), np.zeros(3, dtype=np.int32), np.zeros(3, dtype=np.int32)))
    Left, Right = object(), object()
    _Check(Reference, "Invariant_Scale", lambda: (np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), Left, Right))
    _Check(Reference, "Explicit_None", lambda: (np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), Left, Right))
    _Check(Reference, "Repeated_Scores", lambda: (np.array([-2147483648], dtype=np.int32), np.zeros(1, dtype=np.int32), np.zeros(1, dtype=np.int32), 0))
    _Check(Reference, "Fused_Maps", lambda: (np.arange(16, dtype=np.int32)[::2], np.zeros(8, dtype=np.int32), np.zeros(8, dtype=np.int32)))
    Core = sys.modules.get("numpy._core.multiarray") or sys.modules["numpy.core.multiarray"]
    Original = np.empty_like
    Calls = []
    def _Allocation(Value):
        Calls.append(1)
        return Original(Value)
    np.empty_like = Core.empty_like = _Allocation
    try:
        _Check(Reference, "Temporary_Pipeline", lambda: (np.arange(3, dtype=np.int32), np.zeros(3, dtype=np.int32), 2, 1))
        assert len(Calls) == 2, Calls
    finally:
        np.empty_like = Core.empty_like = Original

_Run()
