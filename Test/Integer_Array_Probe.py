import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as N
from PyCeler.Selection_Worker import _Observe
# Isolated verification for integer indexing, promotion, precision and overflow.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Integer_Array_Loops', Binary)
    Comparisons, Positive, Parallel = 0, 0, 0
    for Name in ('Segments', 'Nested'):
        for Kind in ('float32', 'float64'):
            for Size in (0, 1, 8, 2048):
                Bounds = N.arange(Size + 1, dtype='int64') * 3
                Keys = (N.arange(Size * 3) * 7 % max(Size, 1)).astype('int32')
                Values = N.arange(Size, dtype=Kind) * 0.125
                Weights = N.full(Size * 3, 0.25, dtype=Kind)
                Output = N.zeros(Size, dtype=Kind)
                Args = (Bounds, Keys, Weights, Values, Output) if Name == 'Segments' else (Bounds, Keys, Values, Output)
                Observation = {}  # Record actual native entry separately from correctness of the returned result.
                Expected = _Observe(getattr(Reference, Name), Args)[0]
                Actual = _Observe(getattr(Native, Name), Args, Observation=Observation)[0]
                assert Actual == Expected, (Name, Kind, Size, 'mismatch')
                if Size >= 8:
                    assert Observation.get('Native_Entry'), (Name, Kind, Size, Observation)  # A correct Python fallback must not count as a successful native case.
                    Positive += 1
                    if Size == 2048:
                        assert Observation.get('Actual_Team', 0) > 1, (Name, Kind, Size, Observation)  # Require actual workers, not just an OpenMP-enabled build.
                        Parallel += 1
                Comparisons += 1
    Kinds = ('int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64', 'float32', 'float64')
    Pairs = [(Kind, Kind) for Kind in Kinds] + [('int32', 'float32'), ('int16', 'float32'), ('int64', 'float64'), ('int32', 'uint32'), ('int64', 'uint64')]
    for Left_Kind, Right_Kind in Pairs:
        Left = N.full(8, 3, dtype=Left_Kind)
        Right = N.full(8, 2, dtype=Right_Kind)
        Output = N.zeros((8, 4))
        Observation = {}
        assert _Observe(Reference.Arithmetic, (Left, Right, Output))[0] == _Observe(Native.Arithmetic, (Left, Right, Output), Observation=Observation)[0], (Left_Kind, Right_Kind)
        assert Observation.get('Native_Entry'), (Left_Kind, Right_Kind, Observation)
        Comparisons += 1
        Positive += 1
    for Kind, Value in (('int8', 127), ('int16', 32767), ('int32', 2147483647), ('int64', 2**63 - 1), ('uint8', 255), ('uint64', 2**64 - 1)):
        Left, Right, Output = N.full(8, Value, dtype=Kind), N.ones(8, dtype=Kind), N.zeros((8, 4))
        assert _Observe(Reference.Arithmetic, (Left, Right, Output))[0] == _Observe(Native.Arithmetic, (Left, Right, Output))[0], ('overflow', Kind)
        Comparisons += 1
    Left, Right, Output = N.full(8, 2**24 + 1, dtype='int32'), N.full(8, 0.25, dtype='float32'), N.zeros((8, 4))
    Observation = {}
    assert _Observe(Reference.Arithmetic, (Left, Right, Output))[0] == _Observe(Native.Arithmetic, (Left, Right, Output), Observation=Observation)[0], 'strong integer promotion'
    assert Observation.get('Native_Entry'), Observation
    Positive += 1
    Comparisons += 1
    for Kind in ('int8', 'int32', 'int64'):
        Values = N.ones(8, dtype=Kind)
        Output = N.zeros(9, dtype=Kind)
        Observation = {}
        assert _Observe(Reference.Prefix, (Values, Output))[0] == _Observe(Native.Prefix, (Values, Output), Observation=Observation)[0], ('prefix', Kind)
        assert Observation.get('Native_Entry') and Observation.get('Actual_Team') == 1, Observation
        Positive += 1
        Comparisons += 1
    for Variant in ('float_indices', 'bad_index', 'reverse_keys', 'alias'):
        Bounds = N.arange(9, dtype='int64')
        Keys = N.arange(8, dtype='int32')
        Values, Weights, Output = N.arange(8) * 0.25, N.full(8, 0.25), N.zeros(8)
        if Variant == 'float_indices':
            Keys = Keys.astype('float64')
        elif Variant == 'bad_index':
            Keys[-1] = 17
        elif Variant == 'reverse_keys':
            Keys = Keys[::-1]
        else:
            Output = Values
        Args = (Bounds, Keys, Weights, Values, Output)
        assert _Observe(Reference.Segments, Args)[0] == _Observe(Native.Segments, Args)[0], Variant
        Comparisons += 1
    Values, Output = N.full(8, 127, dtype='int8'), N.zeros(8)
    assert _Observe(Reference.Boolean_Add, (Values, Output))[0] == _Observe(Native.Boolean_Add, (Values, Output))[0], 'bool literal'
    Comparisons += 1
    for Kind, Value in (('int64', -(2**50)), ('uint64', 2**50), ('int64', 2**50 + 1), ('int64', -(2**63)), ('uint64', 2**64 - 1)):
        Values, Output = N.full(8, Value, dtype=Kind), N.zeros(9, dtype=Kind)
        Observation = {}
        assert _Observe(Reference.Copy_Integer, (Values, Output))[0] == _Observe(Native.Copy_Integer, (Values, Output), Observation=Observation)[0], ('integer copy', Kind, Value)
        assert bool(Observation.get('Native_Entry')) == (abs(Value) <= 2**50), (Kind, Value, Observation)
        Positive += abs(Value) <= 2**50
        Comparisons += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native=Positive, Parallel=Parallel)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
