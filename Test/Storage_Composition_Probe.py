import importlib.util
import json
import sys
from pathlib import Path
import numpy as Numpy
# Isolated verification for competing list/array backends and runtime storage kinds.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Array_Region_Probe import Observe, _Copy

def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], 'Storage_Loops')
    Require_Native = sys.argv[3] == 'native'
    Report = dict(Comparisons=0, Native=0, Parallel=0, Cases=[])
    def Check(Name, Args, Positive=False):
        Native._Pyceler_Dispatch_Stats(True, True)
        Values = Args[:2] if Name == 'Whole' else Args
        Expected = Observe(getattr(Reference, Name), _Copy(Values))
        Actual = Observe(getattr(Native, Name), _Copy(Values))
        assert Expected == Actual, (Name, type(Args[0]), Args[2], Expected, Actual)
        Execution = Native._Pyceler_Dispatch_Stats().get('Execution', {})
        Entered = Execution.get('Native_Entry', False)
        Parallel = Entered and Execution.get('Actual_Team', 0) > 1
        if Positive and Require_Native:
            assert Entered, (Name, type(Args[0]), getattr(Args[0], 'dtype', None), Args[2], Execution, Native._Pyceler_Guard_Stats())
        Report['Comparisons'] += 1
        Report['Native'] += Entered
        Report['Parallel'] += Parallel
        Report['Cases'].append(dict(Function=Name, Storage=type(Args[0]).__name__, Size=Args[2], Execution=Execution))
    for Name in ('Transform', 'Extracted', 'Whole'):
        for Kind in (float, int, Numpy.float32, Numpy.float64, Numpy.int32, Numpy.int64):
            for Size in (0, 1, 31, 4096):
                Source = [Kind(Index % 9 + 1) for Index in range(Size)]
                Output = [0.0] * Size
                if Kind not in (float, int):
                    Source, Output = Numpy.array(Source, dtype=Kind), Numpy.zeros(Size, dtype=Kind)
                Check(Name, (Source, Output, Size), Size == 4096 and (Name == 'Whole' or Kind not in (Numpy.int32, Numpy.int64)))
        for Mode in ('shared', 'short', 'overflow', 'mixed', 'nonfinite', 'strided', 'readonly'):
            Source, Output = [float(Index + 1) for Index in range(31)], [0.0] * 31
            if Mode == 'shared':
                Output = Source
            elif Mode == 'short':
                Output = Output[:4]
            elif Mode == 'overflow':
                Source = [2**70 + Index for Index in range(31)]
            elif Mode == 'mixed':
                Source[7] = 7
            elif Mode == 'nonfinite':
                Source[7] = float('inf')
            else:
                Source = Numpy.arange(62, dtype=Numpy.float64)[::2]
                Output = Numpy.zeros_like(Source)
                if Mode == 'readonly':
                    Output.flags.writeable = False  # Guard rejection must preserve the original read-only-output error.
            Check(Name, (Source, Output, 31))
    print(json.dumps(Report), flush=True)

if __name__ == '__main__':
    Main()
