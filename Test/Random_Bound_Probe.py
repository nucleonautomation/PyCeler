import importlib.util
import json
import random
import sys
from pathlib import Path
import numpy as Numpy
# Isolated verification for random bound.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], Path(sys.argv[2]).name.split('.')[0])
    Mode = sys.argv[3]
    Comparisons, Positive, Teams = 0, 0, 0
    Cases = [(Name, 8, Dtype, Seed) for Name in ('Pure_Body', 'Random_Body') for Dtype in ('float32', 'float64') for Seed in (0, 817, 1931)]
    Cases.extend(('Heavy', Width, Dtype, 817) for Width in (32, 8192) for Dtype in ('float32', 'float64'))
    Cases.extend((Name, 1024, Dtype, 817) for Name in ('Ordered_Math', 'List_Math') for Dtype in ('float32', 'float64'))
    for Name, Width, Dtype, Seed in Cases:
        Native._Pyceler_Dispatch_Stats(True, True)
        Results = []
        for Module in (Reference, Native):
            random.seed(Seed)
            Output = Numpy.zeros((8, Width), dtype=Dtype)
            if Name == 'List_Math':
                Output = Output.tolist()
            Args = (Output,) if Name in ('Pure_Body', 'Random_Body') else (Output, Width)
            Result = getattr(Module, Name)(*Args)
            Values = Numpy.asarray(Output)
            Results.append((Result is Output, Values.dtype.str, Values.tobytes(), random.getstate()))
        assert Results[0] == Results[1], (Name, Width, Dtype, Seed)
        Totals = Native._Pyceler_Dispatch_Stats().get('Totals', {})
        Required = Mode != 'selected' or Name == 'Heavy' and Width == 8192 and Dtype == 'float64'
        if Required:
            assert Totals.get('Native_Entries', 0) > 0, (Name, Width, Dtype, Totals)
            Positive += 1
        if Mode == 'parallel' and (Name == 'Heavy' and Width == 8192 or Name in ('Ordered_Math', 'List_Math')):
            assert Totals.get('Maximum_Team', 0) > 1, (Name, Totals)
            Teams += 1
        if Mode == 'serial':
            assert Totals.get('Parallel_Entries', 0) == 0, (Name, Totals)
        Comparisons += 1
    Original = random.random
    Observations = []
    try:
        for Module in (Reference, Native):
            Calls = []
            def Changed():
                Calls.append(len(Calls))
                return 0.25
            random.random = Changed
            Output = Numpy.zeros((8, 8))
            Module.Pure_Body(Output)
            Observations.append((Output.tobytes(), Calls))
        assert Observations[0] == Observations[1] and len(Observations[0][1]) == 8, Observations
    finally:
        random.random = Original
    print(json.dumps(dict(Comparisons=Comparisons + 1, Native=Positive, Parallel=Teams, Bound_Callbacks=8)))

if __name__ == '__main__':
    Main()
