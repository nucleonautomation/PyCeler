import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as N
from PyCeler.Selection_Worker import _Observe
# Isolated verification for conditional tails and bounded prefix recovery.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Region_Tail_Loops', Binary)
    Comparisons, Entries, Teams = 0, 0, 0
    for Name in ('Ordered_Pairs', 'Unobserved_Pairs', 'Unobserved_Tail', 'Conditional_Tail', 'Reverse_Triangle', 'Numeric_Tail'):
        for Kind in ('list',) if Name == 'Numeric_Tail' else ('list', 'float32', 'float64'):
            for Size in (0, 1, 8, 65):
                Values = N.arange(Size, dtype='float64' if Kind == 'list' else Kind) * 0.125
                Output = N.zeros_like(Values)
                if Kind == 'list':
                    Values, Output = Values.tolist(), Output.tolist()
                Args = (Values,) if Name.endswith('Pairs') else (Values, Output, Size // 2) if Name.endswith('Tail') else (Values, Output)
                Expected = _Observe(getattr(Reference, Name), Args)[0]
                Observation = {}  # Record actual native entry separately from correctness of the returned result.
                Actual = _Observe(getattr(Native, Name), Args, Observation=Observation)[0]
                assert Actual == Expected, (Name, Kind, Size, Expected, Actual)
                if Size >= 8:
                    assert Observation.get('Native_Entry'), (Name, Kind, Size, Observation)  # A correct Python fallback must not count as a successful native case.
                    if Name.startswith('Unobserved'):
                        assert not Observation.get('Python_Fallback'), (Name, Kind, Size, Observation)
                    Entries += 1
                Comparisons += 1
    for Name in ('Conditional_Tail', 'Numeric_Tail'):
        for Limit in (0, 1, 2048, 4095):
            Args = ([0.25] * 4096, [0.0] * 4096, Limit)
            Expected = _Observe(getattr(Reference, Name), Args)[0]
            Observation = {}
            Actual = _Observe(getattr(Native, Name), Args, Observation=Observation)[0]
            assert Actual == Expected, (Name, Limit)
            if Limit >= 2048:
                assert Observation.get('Native_Entry'), (Name, Limit, Observation)
                assert Observation.get('Actual_Team', 0) > 1, (Name, Limit, Observation)  # Require actual workers, not just an OpenMP-enabled build.
                Entries += 1
                Teams += 1
            Comparisons += 1
    for Kind in ('list', 'float32', 'float64'):
        Values = N.full(32, 0.25, dtype='float64' if Kind == 'list' else Kind)
        Output = N.zeros(12, dtype=Values.dtype)
        if Kind == 'list':
            Values, Output = Values.tolist(), Output.tolist()
        Args = (Values, Output, 20)
        assert _Observe(Reference.Conditional_Tail, Args)[0] == _Observe(Native.Conditional_Tail, Args)[0], Kind
        Comparisons += 1
    for Size in (8, 65):
        Args = (N.full(Size, 0.25), N.zeros(Size), Size - 1)
        Expected = _Observe(Reference.Random_Tail, Args, Random_State=True)[0]
        Observation = {}
        Actual = _Observe(Native.Random_Tail, Args, Observation=Observation, Random_State=True)[0]
        assert Actual == Expected, ('Random_Tail', Size, Expected, Actual)
        assert Observation.get('Native_Entry'), ('Random_Tail', Size, Observation)
        Comparisons += 1
        Entries += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native=Entries, Parallel=Teams)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
