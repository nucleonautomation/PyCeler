import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as N
from PyCeler.Selection_Worker import _Observe
# Isolated verification for dtype-preserving extrema, clamped indices and repeated reductions.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Array_Extrema_Loops', Binary)
    Counts = dict(Comparisons=0, Native=0, Parallel=0)
    def Check(Name, Args, Positive=False, Parallel=False):
        Observation = {}  # Record actual native entry separately from correctness of the returned result.
        Expected = _Observe(getattr(Reference, Name), Args)[0]
        Actual = _Observe(getattr(Native, Name), Args, Observation=Observation)[0]
        assert Actual == Expected, (Name, [getattr(Value, 'dtype', Value) for Value in Args], Expected, Actual)
        if Positive:
            assert Observation.get('Native_Entry'), (Name, Observation)  # A correct Python fallback must not count as a successful native case.
            Counts['Native'] += 1
        if Parallel:
            assert Observation.get('Actual_Team', 0) > 1, (Name, Observation)  # Require actual workers, not just an OpenMP-enabled build.
            Counts['Parallel'] += 1
        Counts['Comparisons'] += 1
    for Kind in ('float32', 'float64', 'int16', 'uint8'):
        Values = N.arange(128, dtype=Kind).reshape(16, 8)
        Check('Clamp', (Values, N.zeros((16, 8)), 2.0, 80.0), True)
        Check('Extrema', (Values[:, 0].copy(), Values[:, 1].copy(), N.zeros((16, 3)), 32.0), True)
        Check('Binned', (Values, N.zeros(16, dtype='int64')), True)
    for Left, Right in (('float32', 'float64'), ('float32', 'int32'), ('int64', 'uint64')):
        Check('Extrema', (N.full(16, 1, dtype=Left), N.full(16, 2, dtype=Right), N.zeros((16, 3)), 1.00000001), True)
    for Values in (N.array([-0.0, 0.0] * 8), N.array([N.nan, 1.0] * 8), N.array([N.inf, -N.inf] * 8), N.full(16, 2**63 - 1, dtype='int64')):
        Check('Extrema', (Values, N.zeros(16), N.zeros((16, 3)), 0.0))
    for Kind in ('float32', 'float64'):
        for Shape in ((1, 3, 2), (8, 9, 3), (256, 8, 2)):
            Values = (N.arange(N.prod(Shape)) % 32).astype(Kind).reshape(Shape) * 0.125
            Check('Convolution', (Values, N.full((3, 3), 0.125, dtype=Kind), N.zeros_like(Values)), Shape[0] > 1, Shape[0] == 256)
    for Divisor in (1, 2, 3, -2, 0):
        Check('Signed_Division', (N.arange(-16, 16, dtype='float64'), N.zeros(32), Divisor), Divisor != 0)
    for Divisor in (2, 3):
        Check('Scaled_Window', (N.arange(360.0).reshape(20, 18), N.zeros((20 // Divisor, 18 // Divisor)), Divisor), True)
    for Shape in ((0, 0), (1, 1), (8, 12), (20, 18)):
        Check('Repeated_Scales', (N.arange(N.prod(Shape), dtype='float64').reshape(Shape),), Shape[0] >= 8)
    for Bound in (2.0, N.float32(2.0), N.float64(2.0)):
        Check('Borrowed', (N.full(16, 5.0), Bound))
    Values = N.arange(128.0).reshape(16, 8)
    Check('Clamp', (Values[::-1], N.zeros((16, 8)), 2.0, 90.0))
    Check('Clamp', (Values, Values, 2.0, 90.0))
    Check('Clamp', (Values, N.zeros((16, 3)), 2.0, 90.0))
    Output = N.zeros((16, 8))
    Output.flags.writeable = False  # Guard rejection must preserve the original read-only-output error.
    Check('Clamp', (Values, Output, 2.0, 90.0))
    print(json.dumps(Counts), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
