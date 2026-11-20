import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as N
from PyCeler.Selection_Worker import _Observe
from Test.Array_Region_Probe import Counters
# Isolated verification for complete output transactions and late errors.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Complete_Array_Loops', Binary)
    Comparisons, Complete, Parallel = 0, 0, 0
    for Name in ('Interior', 'Reverse', 'Domain'):
        for Kind in ('float32', 'float64'):
            for Size in (0, 1, 8, 65):
                Values = N.full((Size, 17, 19), 0.25, dtype=Kind)
                Output = N.zeros_like(Values)
                Before = Counters(Native)['Native_Elements']
                Observation = {}  # Record actual native entry separately from correctness of the returned result.
                assert _Observe(getattr(Reference, Name), (Values, Output))[0] == _Observe(getattr(Native, Name), (Values, Output), Observation=Observation)[0], (Name, Kind, Size)
                if Size >= 8:
                    Count = max(0, Size - 2) if Name == 'Interior' else (Size + 1) // 2 if Name == 'Reverse' else Size
                    assert Counters(Native)['Native_Elements'] - Before == Count, (Name, Kind, Size, Observation)
                    assert Observation.get('Native_Entry') and not Observation.get('Python_Fallback'), (Name, Kind, Size, Observation)  # A correct Python fallback must not count as a successful native case.
                    Complete += 1
                    if Size == 65:
                        assert Observation.get('Actual_Team', 0) > 1, (Name, Kind, Size, Observation)  # Require actual workers, not just an OpenMP-enabled build.
                        Parallel += 1
                Comparisons += 1
    for Variant in ('strided', 'alias', 'short', 'readonly', 'last_error', 'first_error', 'nonfinite', 'integer_output'):
        Values = N.full((8, 7, 9), 0.25)
        Output = N.zeros_like(Values)
        if Variant == 'strided':
            Values, Output = Values[::-1, :, ::-1], Output[:, ::-1, :]
        elif Variant == 'alias':
            Output = Values
        elif Variant == 'short':
            Output = Output[:6]
        elif Variant == 'readonly':
            Output.flags.writeable = False  # Guard rejection must preserve the original read-only-output error.
        elif Variant == 'last_error':
            Values[-1, -1, -1] = -1.0
        elif Variant == 'first_error':
            Values[0, 0, 0] = -1.0
        elif Variant == 'nonfinite':
            Values[-1, -1, -1] = N.inf
        elif Variant == 'integer_output':
            Output = Output.astype(N.int16)
        assert _Observe(Reference.Domain, (Values, Output))[0] == _Observe(Native.Domain, (Values, Output))[0], Variant
        Comparisons += 1
    print(json.dumps(dict(Comparisons=Comparisons, Complete_Native=Complete, Parallel=Parallel)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
