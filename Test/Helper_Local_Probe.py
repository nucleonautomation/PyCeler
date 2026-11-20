import importlib.util
import json
import sys
import numpy as N
# Isolated verification for pure-helper local computations and unused arguments.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Call(Function, Args):
    try:
        Result = Function(*Args)
        assert Result is Args[1]
        return 'ok', N.asarray(Result).tobytes()
    except Exception as Error:
        return type(Error).__name__, str(Error), N.asarray(Args[1]).tobytes()

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Helper_Local_Loops', Binary)
    Comparisons, Entries, Teams = 0, 0, 0
    for Name in ('Apply', 'With_Error', 'Heavy'):
        for Kind in ('list', 'float32', 'float64'):
            for Size in (0, 8, 4096):
                Values = N.full(Size, 0.125, dtype='float64' if Kind == 'list' else Kind)
                Expected, Actual = N.zeros_like(Values), N.zeros_like(Values)
                if Kind == 'list':
                    Values, Expected, Actual = Values.tolist(), Expected.tolist(), Actual.tolist()
                Tail = (1.0,) if Name == 'With_Error' else ()
                Native._Pyceler_Dispatch_Stats(True, True)
                assert _Call(getattr(Reference, Name), (Values, Expected, *Tail)) == _Call(getattr(Native, Name), (Values, Actual, *Tail)), (Name, Kind, Size)
                Stats = Native._Pyceler_Dispatch_Stats().get('Totals', {})
                if Size:
                    assert Stats.get('Native_Entries', 0) > 0, (Name, Kind, Size, Stats)
                    Entries += 1
                if Size == 4096:
                    assert Stats.get('Maximum_Team', 0) > 1, (Name, Kind, Stats)
                    Teams += 1
                Comparisons += 1
    for Position in (0, 4, 7):
        Values = [0.125] * 8
        Values[Position] = 1.0
        Expected, Actual = [0.0] * 8, [0.0] * 8
        assert _Call(Reference.With_Error, (Values, Expected, 1.0)) == _Call(Native.With_Error, (Values, Actual, 1.0))
        Comparisons += 1
    Runs = []
    for Module in (Reference, Native):
        Events = []
        Original = Module.Polynomial
        def Replacement(Value, Weight):
            Events.append((Value, Weight))
            return Original(Value, Weight)
        Module.Polynomial = Replacement
        Values, Output = [0.125] * 8, [0.0] * 8
        Runs.append((_Call(Module.Apply, (Values, Output)), Events))
        Module.Polynomial = Original
    assert Runs[0] == Runs[1] and len(Runs[0][1]) == 16
    Comparisons += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native=Entries, Parallel=Teams)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
