import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as N
from PyCeler.Selection_Worker import _Observe
# Isolated verification for exact scalar-power precision and exceptional arithmetic.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Array_Power_Loops', Binary)
    Comparisons, Positive, Parallel = 0, 0, 0
    for Name in ('Square', 'Inverse', 'Helper', 'Ordered', 'Random_Power'):
        for Kind in ('float32', 'float64'):
            for Size in (0, 1, 8, 128):
                Values = N.random.default_rng(91).uniform(0.125, 1.875, (Size, 19)).astype(Kind)
                Output = N.zeros_like(Values)
                Args = (Values,) if Name == 'Ordered' else (Values, Output)
                Expected = _Observe(getattr(Reference, Name), Args, Random_State=True)[0]
                Observation = {}  # Record actual native entry separately from correctness of the returned result.
                Actual = _Observe(getattr(Native, Name), Args, Observation=Observation, Random_State=True)[0]
                assert Actual == Expected, (Name, Kind, Size, Expected, Actual)
                if Size >= 8:
                    assert Observation.get('Native_Entry'), (Name, Kind, Size, Observation)  # A correct Python fallback must not count as a successful native case.
                    Positive += 1
                    if Size == 128 and Name not in ('Ordered', 'Random_Power'):
                        assert Observation.get('Actual_Team', 0) > 1, (Name, Kind, Size, Observation)  # Require actual workers, not just an OpenMP-enabled build.
                        Parallel += 1
                Comparisons += 1
    for Name in ('Square', 'Inverse', 'Helper', 'Ordered'):
        for Kind in ('float32', 'float64'):
            Small, Large = (1e-30, 1e30) if Kind == 'float32' else (1e-300, 1e300)
            for Boundary in (-0.0, -0.25, Small, Large, N.inf, N.nan):
                Values = N.full((8, 7), 0.25, dtype=Kind)
                Values[-1, -1] = Boundary
                Output = N.zeros_like(Values)
                Args = (Values,) if Name == 'Ordered' else (Values, Output)
                assert _Observe(getattr(Reference, Name), Args)[0] == _Observe(getattr(Native, Name), Args)[0], (Name, Kind, Boundary)
                Comparisons += 1
    for Kind in ('float32', 'float64'):
        Values = N.random.default_rng(72).uniform(-3.0, 3.0, (128, 97)).astype(Kind)
        Output = N.zeros_like(Values)
        Observation = {}
        assert _Observe(Reference.Square, (Values, Output))[0] == _Observe(Native.Square, (Values, Output), Observation=Observation)[0], Kind
        assert Observation.get('Native_Entry'), Observation
        Comparisons += 1
        Positive += 1
    for Name in ('Square', 'Inverse', 'Helper', 'Ordered'):
        Values = [[0.125 + Column * 0.025 for Column in range(19)] for Row in range(8)]
        Output = [[0.0] * 19 for Row in range(8)]
        Args = (Values,) if Name == 'Ordered' else (Values, Output)
        Observation = {}
        assert _Observe(getattr(Reference, Name), Args)[0] == _Observe(getattr(Native, Name), Args, Observation=Observation)[0], (Name, 'list')
        assert Observation.get('Native_Entry'), (Name, 'list', Observation)
        Comparisons += 1
        Positive += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native=Positive, Parallel=Parallel)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
