import copy
import importlib.util
import json
import struct
import sys
import numpy as Numpy
# Isolated verification for negative/wrapped indices, aliasing and scalar identity.
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
    Reference, Native = Load(sys.argv[1], 'Reference'), Load(sys.argv[2], 'Wrapped_Index_Cases')
    Parallel = sys.argv[3] == 'parallel'
    Comparisons, Positive, Teams = 0, 0, 0
    def Check(Name, Arguments, Required=False, Workers=False, Serial=False):
        nonlocal Comparisons, Positive, Teams
        Left, Right = copy.deepcopy(Arguments), copy.deepcopy(Arguments)
        Expected = Observe(getattr(Reference, Name), Left)
        Before = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
        Native._Pyceler_Dispatch_Stats(True, True)
        Actual = Observe(getattr(Native, Name), Right)
        assert Actual == Expected, (Name, Actual[1], Expected[1])
        After = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
        Totals = Native._Pyceler_Dispatch_Stats().get('Totals', {})
        if Required:
            assert After > Before and Totals.get('Native_Entries', 0) > 0, (Name, Native._Pyceler_Dispatch_Stats())
            Positive += 1
        if Parallel and Workers:
            assert Totals.get('Maximum_Team', 0) > 1, (Name, Totals)
            Teams += 1
        if Serial or not Parallel:
            assert Totals.get('Parallel_Entries', 0) == 0, (Name, Totals)
        Comparisons += 1
        return Right
    for Size in (0, 1, 3, 257, 4096):
        for Kind in (float, int, bool):
            Source = [Kind(Index % 7 - 3) for Index in range(Size)]
            Check('Reverse', (Source, [0.0] * Size, Size), Size > 1, Size == 4096)
            Check('Negate', (Source, [0.0] * Size, Size), Size > 1, Size == 4096)
            for Begin, End, Step in ((-Size, 0, 1), (-1, -Size - 1, -2), (-Size, 0, 3)):
                Count = len(range(Begin, End, Step))
                Check('Stepped', (Source, [0.0] * Size, Begin, End, Step), Count > 1, Size == 4096)
        Source = [Index * 0.001 for Index in range(Size)]
        Check('In_Place', (Source, -Size, Size), Size > 1, Serial=True)
        Check('Reverse', (Source, [0.0] * Size, Size + 1), Size > 1)
        for Dtype in ('float32', 'float64'):
            Data = Numpy.array(Source, dtype=Dtype)
            Check('Array_Reverse', (Data, Numpy.zeros_like(Data), Size), Size > 1, Size == 4096)
    Check('Stepped', ([1.0] * 8, [0.0] * 8, -8, 0, 0))
    for Name in ('Rows', 'Array_Rows'):
        Data = [[Row * 0.01 + Column * 0.001 for Column in range(64)] for Row in range(64)]
        Output = [[0.0] * 64 for Row in range(64)]
        if Name.startswith('Array'):
            Data, Output = Numpy.array(Data, dtype='float32'), Numpy.array(Output, dtype='float32')
        Check(Name, (Data, Output, 64, 64), True, True)
        Check(Name, (Data, Output, 65, 64), Name == 'Rows')
    for Name in ('Wrapped_Alias', 'Array_Alias'):
        Values, Source = [0.125] * 8, [0.25] * 8192
        if Name.startswith('Array'):
            Values, Source = Numpy.array(Values), Numpy.array(Source)
        Check(Name, (Values, Source, -8, 8), True, Serial=True)
    for Size in (8, 4096, 131080):
        for Name in ('Shared_Indices', 'Carried_Index', 'Index_And_Copy'):
            Arguments = ([None] * Size, [None] * Size, 260, 260 + Size) if Name == 'Shared_Indices' else ([None] * Size, [None] * Size, Size)
            Result = Check(Name, Arguments, True, Size >= 4096 and Name != 'Shared_Indices')
            for Index, (Left, Right) in enumerate(zip(*Result[:2])):
                assert (Left is Right) is (Name != 'Index_And_Copy' or Index <= 256), (Name, Index)
    Left, Right = Check('Repeated_Indices', ([[None] * 64 for Row in range(64)], [[None] * 64 for Row in range(64)], 64, 64), True, True)[:2]
    assert all(Left[Row][Column] is Right[Row][Column] for Row in range(64) for Column in range(64))
    assert len({id(Value) for Row in Left for Value in Row}) == 4096
    Source = [0.25] * 4096
    Check('Reverse', (Source, Source, len(Source)))
    Rows = [[0.25] * 8] * 8
    Check('Rows', (Rows, [[0.0] * 8] * 8, 8, 8))
    print(json.dumps(dict(Comparisons=Comparisons, Native=Positive, Parallel=Teams)))

if __name__ == '__main__':
    Main()
