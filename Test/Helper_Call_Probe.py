import copy
import importlib.util
import json
import struct
import sys
import numpy as Numpy
# Isolated verification for helper argument order, identity and guarded inlining.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def State(Value, Seen=None):
    Seen = {} if Seen is None else Seen
    if isinstance(Value, (list, tuple, Numpy.ndarray)):
        if id(Value) in Seen:
            return 'reference', Seen[id(Value)]
        Seen[id(Value)] = len(Seen)
    if isinstance(Value, Numpy.ndarray):
        return 'array', Value.dtype.str, Value.shape, Value.strides, Value.tobytes()
    if isinstance(Value, Numpy.generic):
        return 'scalar', Value.dtype.str, Value.tobytes()
    if isinstance(Value, (list, tuple)):
        return type(Value).__name__, tuple(State(Item, Seen) for Item in Value)
    return type(Value).__name__, struct.pack('>d', Value) if type(Value) is float else Value

def Observe(Function, Arguments):
    try:
        Result, Error = Function(*Arguments), None
    except Exception as Failure:
        Result, Error = None, (type(Failure).__name__, Failure.args)
    return State((Arguments, Result)), Error

def Main():
    Reference, Native = Load(sys.argv[1], 'Reference'), Load(sys.argv[2], 'Helper_Call_Cases')
    Parallel = sys.argv[3] == 'parallel'
    Comparisons, Positive, Teams = 0, 0, 0
    def Check(Name, Arguments, Required=False, Workers=False, Fallback=False, Callables=None):
        nonlocal Comparisons, Positive, Teams
        Left, Right = copy.deepcopy(Arguments), copy.deepcopy(Arguments)
        Functions = Callables or (getattr(Reference, Name), getattr(Native, Name))
        Expected = Observe(Functions[0], Left)
        Before = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
        Native._Pyceler_Dispatch_Stats(True, True)
        Actual = Observe(Functions[1], Right)
        assert Actual == Expected, (Name, Actual[1], Expected[1], Left, Right)
        After = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
        Totals = Native._Pyceler_Dispatch_Stats().get('Totals', {})
        if Required:
            assert After > Before and Totals.get('Native_Entries', 0) > 0, (Name, Totals, Native._Pyceler_Guard_Stats())
            Positive += 1
        if Fallback:
            assert After == Before, (Name, Totals)
        if Parallel and Workers:
            assert Totals.get('Maximum_Team', 0) > 1, (Name, Totals)
            Teams += 1
        if not Parallel:
            assert Totals.get('Parallel_Entries', 0) == 0, (Name, Totals)
        Comparisons += 1
        return Right
    for Size in (0, 1, 3, 257, 4096):
        for Kind in (float, int, bool):
            Data = [Kind(Index % 7 - 3) for Index in range(Size)]
            for Name in ('Apply', 'Inline', 'Local_Alias', 'Integer_Intermediate', 'Shadowed_Math'):
                Check(Name, (Data, [0.0] * Size, Size), Size > 1, Size == 4096)
        for Dtype in ('float32', 'float64'):
            Data = Numpy.linspace(-0.25, 0.25, Size, dtype=Dtype)
            for Name in ('Array_Apply', 'Array_Arithmetic', 'Array_Conditional', 'Array_Inline_Choice'):
                Check(Name, (Data, Numpy.zeros_like(Data), Size), Size > 1, Size == 4096)
        Data = [0.25] * Size
        for Name in ('Keywords', 'Unused_Argument', 'Keyword_Order'):
            Check(Name, (Data, [0.0] * Size, Size), Size > 1)
        if Size:
            Result = Check('Shared_Result', (Data, [0.0] * Size, [0.0] * Size, Size), Size > 1, Size == 4096)
            assert all(Left is Right for Left, Right in zip(Result[1], Result[2]))
    Check('Heavy', ([0.25] * 256, [0.0] * 256, 256), True, True)
    for First_Kind in ('float32', 'float64'):
        for Second_Kind in ('float32', 'float64'):
            for Output_Kind in ('float32', 'float64'):
                First = Numpy.linspace(-10.0, 10.0, 4096, dtype=First_Kind)
                First[1] = 0.1
                Second = Numpy.linspace(-0.25, 0.25, 4096, dtype=Second_Kind)
                Check('Array_Mixed_Choice', (First, Second, Numpy.zeros(4096, dtype=Output_Kind), 4096), True, True)
    Data = [0.25] * 257
    Args = (Data, [0.0] * 257, 257)
    Check('Captured', Args, True, Callables=(Reference.Captured_Callable(Reference.Nested), Native.Captured_Callable(Native.Nested)))
    Check('Captured_Alias', Args, True, Callables=(Reference.Captured_Alias(), Native.Captured_Alias()))
    def Replacement(Value):
        return Value + 100.0
    Check('Captured_Changed', Args, Fallback=True, Callables=(Reference.Captured_Callable(Replacement), Native.Captured_Callable(Replacement)))
    def Local_Reference(Source, Output, Count):
        return Reference.Local_Callable(Source, Output, Count, Reference.Nested)
    def Local_Native(Source, Output, Count):
        return Native.Local_Callable(Source, Output, Count, Native.Nested)
    Check('Local_Callable', Args, True, Callables=(Local_Reference, Local_Native))
    for Name in ('Nested', 'Square', 'Cosine'):
        Saved = getattr(Reference, Name), getattr(Native, Name)
        try:
            setattr(Reference, Name, Replacement)
            setattr(Native, Name, Replacement)
            Check('Apply', Args, Fallback=True)
            if Name == 'Cosine':
                Check('Inline', Args, Fallback=True)
        finally:
            setattr(Reference, Name, Saved[0])
            setattr(Native, Name, Saved[1])
    for Attribute, Value in (('__defaults__', (0.5,)), ('__kwdefaults__', {})):
        Saved = getattr(Reference.Nested, Attribute), getattr(Native.Nested, Attribute)
        try:
            setattr(Reference.Nested, Attribute, Value)
            setattr(Native.Nested, Attribute, Value)
            Check('Apply', Args, Fallback=True)
        finally:
            setattr(Reference.Nested, Attribute, Saved[0])
            setattr(Native.Nested, Attribute, Saved[1])
    Saved = Reference.Square.__code__, Native.Square.__code__
    try:
        Reference.Square.__code__ = Replacement.__code__
        Native.Square.__code__ = Replacement.__code__
        Check('Apply', Args, Fallback=True)
    finally:
        Reference.Square.__code__, Native.Square.__code__ = Saved
    Nested_Constant = None
    for Depth in range(1000):
        Nested_Constant = (Nested_Constant,)
    try:
        Reference.Square.__code__ = Saved[0].replace(co_consts=(*Saved[0].co_consts, Nested_Constant))
        Native.Square.__code__ = Saved[1].replace(co_consts=(*Saved[1].co_consts, Nested_Constant))
        Check('Apply', Args, Fallback=True)
    finally:
        Reference.Square.__code__, Native.Square.__code__ = Saved
    for Value in (2**51, 2**80):
        Check('Integer_Intermediate', ([Value] * 8, [0.0] * 8, 8), Fallback=True)
    Check('Unused_Argument', ([0.25] * 65540, [0.0] * 65540, 65540), True)
    Data = [0.25] * 257
    Check('Apply', (Data, Data, 257))
    class Number(float):
        pass
    Check('Apply', ([Number(0.25)] * 8, [0.0] * 8, 8), Fallback=True)
    print(json.dumps(dict(Comparisons=Comparisons, Native=Positive, Parallel=Teams)))

if __name__ == '__main__':
    Main()
