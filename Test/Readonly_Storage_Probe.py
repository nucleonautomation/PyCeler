import copy
import importlib.util
import json
import struct
import sys
from pathlib import Path
import numpy as Numpy
# Isolated verification for shared read-only storage and selection holdouts.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Fingerprint(Value):
    if type(Value) is Numpy.ndarray:
        return Value.dtype.str, Value.shape, Value.tobytes()
    if type(Value) in (list, tuple):
        return type(Value).__name__, tuple(Fingerprint(Item) for Item in Value)
    if type(Value) is float:
        return 'float', struct.pack('d', Value)
    return type(Value).__name__, Value

def Flat_Arguments(Storage, Alias, Size):
    if Storage == 'list':
        First = [Index * 0.001 for Index in range(Size)]
        Second = First if Alias == 'shared' else First[:]
        Output = First if Alias == 'write' else [0.0] * Size
    else:
        Base = Numpy.arange(Size + 1, dtype=Storage) * 0.001
        First = Base[:-1]
        Second = First if Alias == 'shared' else Base[1:] if Alias == 'overlap' else First.copy()
        Output = First if Alias == 'write' else Numpy.zeros_like(First)
    return First, Second, Output

def Rows_Arguments(Storage, Alias, Width):
    Row = [Index * 0.001 for Index in range(Width)]
    Source = [Row if Alias == 'shared' else Row[:] for Index in range(16)]
    Output = [[0.0] * Width for Index in range(16)]
    if Alias == 'write':
        Output = Source
    elif Alias == 'output':
        Output = [Output[0]] * 16
    if Storage != 'list':
        Source = Numpy.array(Source, dtype=Storage)
        Output = Source if Alias == 'write' else Numpy.zeros_like(Source)
    return Source, Output

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], Path(sys.argv[2]).name.split('.')[0])
    Parallel = sys.argv[3] == 'parallel'
    Counts = dict(Comparisons=0, Native=0, Parallel=0, Guarded=0)
    def Check(Name, Factory, Required=False, Guarded=False, Team=False, Identity=False):
        Native._Pyceler_Dispatch_Stats(True, True)
        Results = []
        for Module in (Reference, Native):
            Args = Factory()
            Error = None
            Result = None
            try:
                Result = getattr(Module, Name)(*Args)
            except Exception as Failure:
                Error = type(Failure).__name__, str(Failure)
            Extra = None
            if Identity:
                Extra = all(Args[1][Row][Column] is Args[2][Row][Column] and Args[1][Row][Column] is Args[1][Row][0] for Row in range(len(Args[0])) for Column in range(len(Args[0][Row])))
                assert Extra, Name
            Results.append((Fingerprint(Args), Error, None if Result is None else any(Result is Value for Value in Args), Extra))
        assert Results[0] == Results[1], (Name, Required, Results[0][1], Results[1][1])
        Stats = Native._Pyceler_Dispatch_Stats().get('Totals', {})
        if Required:
            assert Stats.get('Native_Entries', 0) > 0, (Name, Stats)
            Counts['Native'] += 1
        if Guarded:
            assert Stats.get('Native_Entries', 0) == 0, (Name, Stats)
            Counts['Guarded'] += 1
        if Parallel and Team:
            assert Stats.get('Maximum_Team', 0) > 1, (Name, Stats)
            Counts['Parallel'] += 1
        if not Parallel:
            assert Stats.get('Parallel_Entries', 0) == 0, (Name, Stats)
        Counts['Comparisons'] += 1
    for Storage in ('list', 'float32', 'float64'):
        Names = ('Flat', 'Flat_Region') if Storage == 'list' else ('Flat', 'Array_Region')
        for Name in Names:
            for Alias in ('distinct', 'shared', 'write') + (() if Storage == 'list' else ('overlap',)):
                for Size in (0, 1, 8, 4096):
                    Check(Name, lambda: Flat_Arguments(Storage, Alias, Size), Required=Size > 1 and Alias != 'write', Team=Size == 4096 and Alias != 'write')
        Name = 'Rows' if Storage == 'list' else 'Array_Rows'
        for Alias in ('distinct', 'shared', 'write') + (('output',) if Storage == 'list' else ()):
            Check(Name, lambda: Rows_Arguments(Storage, Alias, 512), Required=Alias in ('distinct', 'shared'), Guarded=Alias in ('write', 'output'), Team=Alias in ('distinct', 'shared'))
    for Shift in (-16, -1, 0, 1, 16):
        Check('Shifted_Rows', lambda: (*Rows_Arguments('list', 'shared', 512), Shift), Required=Shift <= 0, Team=Shift <= 0)
    for Source in ([], [[]], [[0.25], []], [[0.25], [0.5, 1.0]]):
        Check('Rows', lambda: (copy.deepcopy(Source), [[0.0] * len(Row) for Row in Source]), Guarded=True)
    Source = [[[0.25] * 32 for Row in range(8)] for Layer in range(16)]
    Check('Volume', lambda: (copy.deepcopy(Source), [[[0.0] * 32 for Row in range(8)] for Layer in range(16)]), Required=True, Team=True)
    for Width in (8, 512):
        Check('Length_Identity', lambda: (*Rows_Arguments('list', 'shared', Width), [[0] * Width for Row in range(16)]), Required=True, Identity=True)
    for Row, Column in ((0, 0), (-16, -8), (16, 0), (0, 8), (16, 2**60)):
        Check('Checked_Length', lambda: (copy.deepcopy(Source), [0] * 64, Row, Column), Required=-16 <= Row < 16 and -8 <= Column < 8, Guarded=not (-16 <= Row < 16 and -8 <= Column < 8))
    print(json.dumps(Counts))

if __name__ == '__main__':
    Main()
