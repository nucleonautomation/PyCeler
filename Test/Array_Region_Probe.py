import copy
import importlib.util
import json
import sys
import warnings
from pathlib import Path
import numpy as np
from PyCeler.Selection_Inputs import _Copy, _Array_Owner
# Isolated verification for ndarray ranks, scalar promotion and ordered region execution.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Snapshot(Value):
    Memo, Storage, Nodes = {}, {}, []
    def Visit(Item):
        if id(Item) in Memo:
            return Memo[id(Item)]
        Index = len(Nodes)
        Memo[id(Item)] = Index
        Nodes.append(None)
        if isinstance(Item, np.ndarray):
            Owner = _Array_Owner(Item)
            Offset = Item.__array_interface__['data'][0] - Owner.__array_interface__['data'][0]
            Record = type(Item).__name__, Item.dtype.str, Item.shape, Item.strides, Item.flags.writeable, Storage.setdefault(id(Owner), len(Storage)), Offset, Item.tobytes()
        elif isinstance(Item, (tuple, list)):
            Record = type(Item).__name__, tuple(Visit(Part) for Part in Item)
        elif isinstance(Item, np.generic):
            Record = type(Item).__name__, Item.dtype.str, Item.tobytes()
        elif type(Item) is float:
            Record = 'float', Item.hex()
        else:
            Record = type(Item).__name__, repr(Item)
        Nodes[Index] = Record
        return Index
    Visit(Value)
    return tuple(Nodes)

def Observe(Function, Args):
    with warnings.catch_warnings(record=True) as Warnings:
        warnings.simplefilter('always')
        try:
            Value, Error = Function(*Args), None
        except Exception as Failure:
            Value, Error = None, (type(Failure).__name__, str(Failure))
    return Snapshot((Value, Args)), Error, [(type(Item.message).__name__, str(Item.message)) for Item in Warnings]

def Counters(Module):
    Values = [Value() for Name, Value in vars(Module).items() if Name.startswith('_Pyceler_Fast_') and Name.endswith('Stats')]
    return {Name: sum(Value[Name] for Value in Values) for Name in ('Native_Elements', 'Parallel_Elements')}

def Main():
    Reference, Native = Load(sys.argv[1], 'Reference'), Load(sys.argv[2], 'Array_Region_Loops')
    Positive = 0
    Cases = []
    for Dtype in (np.float32, np.float64):
        for Size in (0, 1, 8, 64):
            Source = np.arange(Size * 17, dtype=Dtype).reshape(Size, 17) * Dtype(0.001)
            Cases.append(('Stencil', (Source, Source.copy(), Size, 17), Size >= 8))
            Four = np.arange(Size * 3 * 4 * 5, dtype=Dtype).reshape(Size, 3, 4, 5) * Dtype(0.001)
            Cases.append(('Volume_Four', (Four, np.zeros_like(Four)), Size >= 8))
            Six = np.arange(Size * 32, dtype=Dtype).reshape(Size, 2, 2, 2, 2, 2) * Dtype(0.001)
            Cases.append(('Volume_Six', (Six, np.zeros_like(Six)), Size >= 8))
            Points = np.arange(Size * 3, dtype=Dtype).reshape(Size, 3) * Dtype(0.07)
            Cases.append(('Row_Sum', (Points, 0.0), Size >= 8))
            Cases.append(('Piecewise_Sum', (Points.reshape(-1), 0.0), Size >= 8))
        for Start, Stop, Step in ((0, 64, 3), (63, -1, -2), (-64, 0, 2), (0, 67, 1), (0, 64, 0)):
            Source = np.arange(64 * 9, dtype=Dtype).reshape(64, 9) * Dtype(0.01)
            Cases.append(('Strided', (Source, np.zeros_like(Source), Start, Stop, Step), Step != 0 and Stop < 65))
        Source = np.arange(64 * 9, dtype=Dtype).reshape(64, 9) * Dtype(0.01)
        Cases.append(('Neighbor_Recurrence', (Source,), True))
        for Kind in (np.uint8, np.int16, np.int32, np.int64, np.uint64, np.bool_):
            Cases.append(('Cast_Outputs', (Source, np.zeros(Source.shape, dtype=Kind), np.zeros(Source.shape, dtype=np.float32)), True))
    for Mode in ('alias', 'overlap', 'transposed', 'negative', 'readonly', 'integer', 'nan', 'overflow', 'underflow'):
        Source = np.arange(64 * 17, dtype=np.float64).reshape(64, 17) * 0.01
        Output = Source.copy()
        if Mode == 'alias':
            Output = Source
        elif Mode == 'overlap':
            Output = np.ndarray((64, 17), dtype=np.float64, buffer=np.arange(128, dtype=np.float64), strides=(8, 8))
        elif Mode == 'transposed':
            Source, Output = Source.T, Output.T
        elif Mode == 'negative':
            Source, Output = Source[::-1], Output[::-1]
        elif Mode == 'readonly':
            Output.flags.writeable = False  # Guard rejection must preserve the original read-only-output error.
        elif Mode == 'integer':
            Source = Source.astype(np.int32)
        else:
            Source[4, 4] = {'nan': np.nan, 'overflow': 1e308, 'underflow': 1e-310}[Mode]
        Cases.append(('Stencil', (Source, Output, *Source.shape), False))
    for Name, Args, Required in Cases:
        Before = Counters(Native)
        Expected = Observe(getattr(Reference, Name), _Copy(Args))
        Actual = Observe(getattr(Native, Name), _Copy(Args))
        assert Expected == Actual, (Name, Args[-1] if type(Args[-1]) is int else '', Expected[1:], Actual[1:], Snapshot(Expected[0]) == Snapshot(Actual[0]))
        if Required:
            assert Counters(Native)['Native_Elements'] > Before['Native_Elements'], (Name, 'no native execution')
            Positive += 1
    for Setting in ('warn', 'raise', 'ignore'):
        Previous = np.seterr(all=Setting)
        try:
            Input = np.full((3, 2, 2, 2), 1e-42, dtype=np.float32)
            Args = (Input, np.zeros_like(Input))
            assert Observe(Reference.Volume_Four, _Copy(Args)) == Observe(Native.Volume_Four, _Copy(Args)), ('floating error mode', Setting)
        finally:
            np.seterr(**Previous)
    for Name in ('zeros', 'empty', 'copyto', 'shares_memory', 'float64'):
        Args = (np.arange(64 * 17, dtype=np.float64).reshape(64, 17) * 0.01, np.zeros((64, 17)), 64, 17)
        Left, Right = _Copy(Args), _Copy(Args)
        Original = getattr(np, Name)
        def Rebound(*Args, **Options):
            raise AssertionError('Unexpected internal NumPy callback')
        Before = Counters(Native)
        try:
            setattr(np, Name, Rebound)
            assert Observe(Reference.Stencil, Left) == Observe(Native.Stencil, Right), ('rebound NumPy helper', Name)
            assert Counters(Native) == Before
        finally:
            setattr(np, Name, Original)
    Values = np.arange(64 * 3, dtype=np.float64).reshape(64, 3) * 0.01
    Original_Math = Reference.math
    del Reference.math
    del Native.math
    try:
        assert Observe(Reference.Row_Sum, (Values, 0.0)) == Observe(Native.Row_Sum, (Values, 0.0))
    finally:
        Reference.math = Original_Math
        Native.math = Original_Math
    Core = np._core.multiarray
    Original_Zeros = np.zeros
    def Exhausted(*Args, **Options):
        raise MemoryError('Injected scratch allocation failure')
    Left, Right = _Copy((Values, Values.copy(), *Values.shape)), _Copy((Values, Values.copy(), *Values.shape))
    try:
        np.zeros = Core.zeros = Exhausted
        assert Observe(Reference.Stencil, Left) == Observe(Native.Stencil, Right)
    finally:
        np.zeros = Core.zeros = Original_Zeros
    Report = dict(Comparisons=len(Cases) + 10, Positive=Positive, Counters=Counters(Native))
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2))
    print(json.dumps(Report))

if __name__ == '__main__':
    Main()
