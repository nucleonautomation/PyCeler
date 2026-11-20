import importlib.util
import json
import sys
from pathlib import Path
import numpy as Numpy
# Isolated verification for shared read-only storage and selection holdouts.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], Path(sys.argv[2]).name.split('.')[0])
    Results = {}
    for Storage in ('list', 'float32', 'float64'):
        Native._Pyceler_Dispatch_Stats(True, True)
        Values = []
        for Module in (Reference, Native):
            First = [0.25] * 16384 if Storage == 'list' else Numpy.full(16384, 0.25, dtype=Storage)
            Output = [0.0] * 16384 if Storage == 'list' else Numpy.zeros_like(First)
            Result = Module.Transform(First, First, Output)
            Values.append((Result is Output, Numpy.asarray(Result).tobytes(), Numpy.asarray(First).tobytes()))
        assert Values[0] == Values[1], Storage
        Stats = Native._Pyceler_Dispatch_Stats().get('Totals', {})
        assert Stats.get('Native_Entries', 0) > 0, (Storage, Stats)
        assert Stats.get('Maximum_Team', 0) > 1, (Storage, Stats)
        Results[Storage] = Stats
    print(json.dumps(Results))

if __name__ == '__main__':
    Main()
