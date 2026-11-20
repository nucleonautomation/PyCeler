import importlib.util
import json
import sys
import numpy as N
# Isolated verification for iterator construction, target bindings and strict mismatch.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _State(Value):
    if isinstance(Value, N.ndarray):
        return Value.dtype.str, Value.shape, Value.tobytes()
    if isinstance(Value, (tuple, list)):
        return type(Value).__name__, tuple(_State(Part) for Part in Value)
    if isinstance(Value, (float, N.floating)):
        return type(Value).__name__, N.asarray(Value).tobytes()
    return type(Value).__name__, Value

def _Call(Function, Args):
    try:
        return 'ok', _State(Function(*Args))
    except Exception as Error:
        return type(Error).__name__, str(Error)

def _Run(Source, Binary):
    Reference, Native = _Load('Iterator_Reference', Source), _Load('Iterator_Loops', Binary)
    Comparisons, Entries, Teams = 0, 0, 0
    for Name in ('Enumerated', 'Array_Enumerated', 'Zipped', 'Strict', 'Array_Zipped', 'Negative_Start', 'Shifted_Range'):
        Kinds = ('list',) if Name == 'Shifted_Range' else ('list', 'float32', 'float64')
        for Kind in Kinds:
            for Size in (0, 1, 8, 4096):
                def Arguments():
                    First = N.full(Size, 0.25, dtype='float64' if Kind == 'list' else Kind)
                    Second, Output = First.copy(), N.zeros_like(First)
                    if Kind == 'list':
                        First, Second, Output = First.tolist(), Second.tolist(), Output.tolist()
                    return (First, Output, -7) if Name.endswith('Enumerated') or Name == 'Shifted_Range' else (First, Output) if Name == 'Negative_Start' else (First, Second, Output)
                Expected, Actual = Arguments(), Arguments()
                Native._Pyceler_Dispatch_Stats(True, True)
                Left, Right = _Call(getattr(Reference, Name), Expected), _Call(getattr(Native, Name), Actual)
                assert Left == Right and _State(Expected) == _State(Actual), (Name, Kind, Size, Left, Right)
                Stats = Native._Pyceler_Dispatch_Stats().get('Totals', {})
                if Size >= 8:
                    assert Stats.get('Native_Entries', 0) > 0, (Name, Kind, Size, Stats)
                    Entries += 1
                if Size == 4096 and (Name.endswith('Enumerated') or Name == 'Shifted_Range'):
                    assert Stats.get('Maximum_Team', 0) > 1, (Name, Kind, Stats)
                    Teams += 1
                if Size and Kind == 'list':
                    Result = getattr(Native, Name)(*Actual)
                    assert Result[2] is Actual[0][-1], (Name, 'borrowed target identity')
                Comparisons += 1
    for Name in ('Zipped', 'Strict'):
        for Length in (0, 3, 10):
            Expected = ([0.25] * 8, [0.5] * Length, [0.0] * 8)
            Actual = tuple(Value.copy() for Value in Expected)
            assert _Call(getattr(Reference, Name), Expected) == _Call(getattr(Native, Name), Actual), Name
            assert Expected == Actual, Name
            Comparisons += 1
    for Name in ('Enumerated', 'Zipped'):
        Runs = []
        for Module in (Reference, Native):
            Events = []
            Canonical = enumerate if Name == 'Enumerated' else zip
            Binding = 'enumerate' if Name == 'Enumerated' else 'zip'
            def Constructor(*Args, **Keywords):
                Events.append('construct')
                for Value in Canonical(*Args, **Keywords):
                    Events.append('next')
                    yield Value
            setattr(Module, Binding, Constructor)
            Args = ([0.25] * 8, [0.0] * 8, 0) if Name == 'Enumerated' else ([0.25] * 8, [0.5] * 8, [0.0] * 8)
            Runs.append((_Call(getattr(Module, Name), Args), _State(Args), Events))
            delattr(Module, Binding)
        assert Runs[0] == Runs[1], (Name, Runs)
        Comparisons += 1
    for Position in (0, 4, 7):
        Expected = ([0.25] * 8, [0.0] * Position, 0)
        Actual = tuple(Value.copy() if isinstance(Value, list) else Value for Value in Expected)
        assert _Call(Reference.Enumerated, Expected) == _Call(Native.Enumerated, Actual)
        assert Expected == Actual
        Comparisons += 1
    Runs = []
    for Module in (Reference, Native):
        Events = []
        class Start:
            def __index__(self):
                Events.append('index')
                return 0
        Args = ([0.25] * 8, [0.0] * 8, Start())
        Runs.append((_Call(Module.Enumerated, Args), Args[1], Events))
    assert Runs[0] == Runs[1] and Runs[0][2] == ['index'], Runs
    Comparisons += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native=Entries, Parallel=Teams)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
