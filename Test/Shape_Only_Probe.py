import importlib.util
import json
import sys
import numpy as N
# Isolated verification for array metadata without copying or reading object data.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Call(Function, Template, Output):
    try:
        Result = Function(Template, Output)
        assert Result is Output
        return 'ok', N.asarray(Output).tobytes()
    except Exception as Error:
        return type(Error).__name__, str(Error), N.asarray(Output).tobytes()

def _Run(Source, Binary):
    Reference, Native = _Load('Reference', Source), _Load('Shape_Only_Loops', Binary)
    Comparisons, Entries, Teams = 0, 0, 0
    for Name in ('Shape_List', 'Shape_Path', 'Shape_Array', 'Shape_Bound'):
        for Size in (0, 8, 4096):
            for Width in (0, 3):
                if Name == 'Shape_Array':
                    Template = N.full((max(Size, 1), Width), object(), dtype=object)
                    Expected, Actual = N.zeros(Size), N.zeros(Size)
                else:
                    Template = [[object()] * Width for Index in range(Size)] if Name == 'Shape_Path' else [object()] * Size
                    Expected, Actual = [0.0] * Size, [0.0] * Size
                Native._Pyceler_Dispatch_Stats(True, True)
                assert _Call(getattr(Reference, Name), Template, Expected) == _Call(getattr(Native, Name), Template, Actual), (Name, Size, Width)
                Stats = Native._Pyceler_Dispatch_Stats().get('Totals', {})
                if Size >= 8:
                    assert Stats.get('Native_Entries', 0) > 0, (Name, Size, Width, Stats)
                    Entries += 1
                if Size == 4096:
                    assert Stats.get('Maximum_Team', 0) > 1, (Name, Width, Stats)
                    Teams += 1
                Comparisons += 1
    for Name in ('Shape_List', 'Shape_Bound'):
        Expected, Actual = [0.0] * 32, [0.0] * 32
        Native._Pyceler_Dispatch_Stats(True, True)
        assert _Call(getattr(Reference, Name), Expected, Expected) == _Call(getattr(Native, Name), Actual, Actual)
        assert Native._Pyceler_Dispatch_Stats()['Totals'].get('Native_Entries', 0) > 0, Name
        Comparisons += 1
        Entries += 1
    for Template in ([[object()], [], [object(), object()]], [[object()]]):
        Expected, Actual = [0.0] * 3, [0.0] * 3
        assert _Call(Reference.Shape_Path, Template, Expected) == _Call(Native.Shape_Path, Template, Actual)
        Comparisons += 1
    for Width in (0, 3):
        Template = N.zeros((0, Width), dtype='complex128')
        Expected, Actual = N.zeros(8), N.zeros(8)
        assert _Call(Reference.Shape_Array, Template, Expected) == _Call(Native.Shape_Array, Template, Actual)
        Comparisons += 1
    Events = []
    class Template:
        def __len__(self):
            Events.append('len')
            return 3
    Expected, Actual = [0.0] * 8, [0.0] * 8
    Left = _Call(Reference.Shape_List, Template(), Expected)
    First = Events.copy()
    Events.clear()
    Right = _Call(Native.Shape_List, Template(), Actual)
    assert Left == Right and First == Events and len(Events) == 8
    Comparisons += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native=Entries, Parallel=Teams)), flush=True)

if __name__ == '__main__':
    _Run(*sys.argv[1:])
