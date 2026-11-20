import importlib.util
import json
import sys
from pathlib import Path
import numpy as N
# Isolated verification for iterator construction, target bindings and strict mismatch.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], Path(sys.argv[2]).name.split('.')[0])
    Comparisons, Positive, Parallel = 0, 0, 0
    for Name in ('Both', 'Zip_Rows', 'Array_Rows', 'Enumerated_Rows'):
        for Storage in ('list', 'float32', 'float64'):
            if Name == 'Zip_Rows' and Storage != 'list':
                continue
            for Size in (0, 8, 4096):
                Native._Pyceler_Dispatch_Stats(True, True)
                Results = []
                for Module in (Reference, Native):
                    Shape = (Size,) if Name == 'Both' else (3, Size)
                    Source = N.full(Shape, 0.25, dtype='float64' if Storage == 'list' else Storage)
                    Output = N.zeros_like(Source)
                    if Storage == 'list':
                        Source, Output = Source.tolist(), Output.tolist()
                    Result = getattr(Module, Name)(Source, Output)
                    Results.append((Result is Output, N.asarray(Output).tobytes(), N.asarray(Source).tobytes()))
                assert Results[0] == Results[1], (Name, Storage, Size)
                Totals = Native._Pyceler_Dispatch_Stats().get('Totals', {})
                if Size:
                    assert Totals.get('Native_Entries', 0) > 0, (Name, Storage, Size, Totals)
                    Positive += 1
                if Size == 4096:
                    assert Totals.get('Maximum_Team', 0) > 1, (Name, Storage, Totals)
                    Parallel += 1
                Comparisons += 1
    Events = []
    for Module in (Reference, Native):
        Calls = []
        def Replaced(Left, Right):
            Calls.append('constructor')
            for First, Second in zip(Left, Right):
                Calls.append('next')
                yield First, Second
        Module.zip = Replaced
        Output = [[0.0] * 8 for Row in range(3)]
        Module.Zip_Rows([[0.25] * 8 for Row in range(3)], Output)
        Events.append((Calls, Output))
        del Module.zip
    assert Events[0] == Events[1], Events
    Observations = []
    for Module in (Reference, Native):
        Calls = []
        def Changed_Range(*Args):
            Calls.append(Args)
            return range(*Args)
        Module.range = Changed_Range
        Output = [0.0] * 8
        Module.Both([0.25] * 8, Output)
        Observations.append((Calls, Output))
        del Module.range
        assert Module.Empty_Capture()([]) == 17
        assert Module.Empty_Capture()(N.zeros(0)) == 17
    assert Observations[0] == Observations[1] and len(Observations[0][0]) == 9, Observations
    # An empty iteration must avoid the deleted capture; a nonempty one must report its exact free-name error.
    for Source in ([0.25], N.full(3, 0.25)):
        Errors = []
        for Module in (Reference, Native):
            try:
                Module.Empty_Capture()(Source)
            except Exception as Error:
                Errors.append((type(Error).__name__, Error.args, getattr(Error, 'name', None)))
        assert len(Errors) == 2 and Errors[0] == Errors[1], Errors
    print(json.dumps(dict(Comparisons=Comparisons + 6, Native=Positive, Parallel=Parallel)))

if __name__ == '__main__':
    Main()
