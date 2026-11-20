import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
# Isolated verification for generalization.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Array_Region_Probe import Snapshot, _Copy

def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Counters(Module):
    Reports = [Function() for Name, Function in vars(Module).items() if Name.startswith('_Pyceler_Fast_') and Name.endswith('Stats')]
    Execution = Module._Pyceler_Dispatch_Stats().get('Execution', {})
    Entered = Execution.get('Native_Entry', False)
    return sum(Value['Native_Elements'] for Value in Reports) + Entered, sum(Value['Parallel_Elements'] for Value in Reports) + (Entered and Execution.get('Actual_Team', 0) > 1)

def Observe(Function, Arguments):
    try:
        Result, Error = Function(*Arguments), None
    except Exception as Failure:
        Result, Error = None, (type(Failure).__name__, str(Failure))
    return Snapshot((Arguments, Result)), Error

def Arguments(Name, Size, Depth=5, Kind=float):
    if Name == 'Many_Buffers':
        return tuple([Kind((Index + Offset) % 11) for Index in range(Size)] for Offset in range(11)) + ([0.0] * Size, Size)
    if Name == 'Columns':
        Source = np.arange(Depth * Size, dtype=np.float64).reshape(Depth, Size) * -0.001
        return Source, np.zeros_like(Source), np.zeros_like(Source), Size, Depth
    Source = [Kind(Index % 9 - 4) for Index in range(Size)]
    Output = [0.0] * (max(Size, Depth) * (2 if Name == 'Interleaved' else 1))
    Other = [0.0] * max(Size, Depth)
    if Name.endswith('_Array'):
        Source, Output, Other = np.array(Source), np.array(Output), np.array(Other)
    return Source, Output, Other, Size, Depth

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], 'Generalization_Loops')
    Names = ('Nested', 'Nested_While', 'Repeated_Index', 'Conditional_Constant', 'Conditional_Expression', 'Shared_Inner', 'Integer_Absolute', 'Direct_Absolute', 'Interleaved', 'Columns', 'Dependent', 'Many_Slots_List', 'Many_Slots_Array', 'Many_Buffers')
    Report = dict(Comparisons=0, Native=0, Parallel=0, Cases=[])
    def Check(Name, Args, Positive=False, Parallel=False):
        Native._Pyceler_Dispatch_Stats(True, True)
        Before = Counters(Native)
        Left = Observe(getattr(Reference, Name), _Copy(Args))
        Right = Observe(getattr(Native, Name), _Copy(Args))
        After = Counters(Native)
        assert Left == Right, (Name, Args[-2:], Left, Right)
        if Positive:
            assert After[0] > Before[0], (Name, Args[-2:], 'No native entry', Native._Pyceler_Guard_Stats())
        if Parallel:
            assert After[1] > Before[1], (Name, Args[-2:], 'No parallel entry')
        Report['Comparisons'] += 1
        Report['Native'] += After[0] > Before[0]
        Report['Parallel'] += After[1] > Before[1]
        Report['Cases'].append(dict(Name=Name, Size=Args[-2:] if Name != 'Many_Buffers' else Args[-1], Native=After[0] - Before[0], Parallel=After[1] - Before[1]))
    for Name in Names:
        for Size in (0, 1, 2, 31, 300):
            Check(Name, Arguments(Name, Size), Size >= 31 and not Name.startswith('Conditional_'))
    for Name in ('Nested', 'Nested_While', 'Shared_Inner'):
        Check(Name, Arguments(Name, 31, 0))
    Check('Nested', Arguments('Nested', 3, 1048580), True)
    Args = list(Arguments('Direct_Absolute', 300, Kind=int))
    Args[0] = [1000 + Index for Index in range(300)]
    Check('Direct_Absolute', tuple(Args))
    Large_Source = [0.25] * 4194305
    Expected = Reference.Direct_Absolute(Large_Source, [0.0] * 3, [], 3, 0)
    Before = Counters(Native)
    Actual = Native.Direct_Absolute(Large_Source, [0.0] * 3, [], 3, 0)
    assert Snapshot(Expected) == Snapshot(Actual)
    assert len(Large_Source) == 4194305 and all(Value is Large_Source[0] for Value in Large_Source)
    assert Counters(Native)[0] > Before[0], 'Large read buffer did not enter native code'
    Report['Comparisons'] += 1
    Report['Native'] += 1
    del Large_Source
    for Name in ('Integer_Absolute', 'Many_Buffers', 'Many_Slots_List'):
        Check(Name, Arguments(Name, 300, Kind=int), True)
        for Value in (2**55, -(2**60)):
            Args = Arguments(Name, 31, Kind=int)
            Args[0][5] = Value
            Check(Name, Args)
    for Name in ('Nested', 'Repeated_Index', 'Interleaved', 'Columns', 'Many_Slots_Array'):
        Check(Name, Arguments(Name, 4096), True, Name != 'Repeated_Index')
    for Dtype in (np.float32, np.float64):
        Args = Arguments('Columns', 300)
        Check('Columns', tuple(Value.astype(Dtype) if isinstance(Value, np.ndarray) else Value for Value in Args), True)
    for Name in ('Nested', 'Interleaved'):
        for Mode in ('short', 'alias', 'nonfinite'):
            Args = list(Arguments(Name, 31))
            if Mode == 'short':
                Args[1] = Args[1][:4]
            elif Mode == 'alias':
                Args[2] = Args[1]
            else:
                Args[0][5] = float('inf')
            Check(Name, tuple(Args))
        Reference.abs = Native.abs = lambda Value: Value + 2.0
        Check(Name, Arguments(Name, 31))
        del Reference.abs, Native.abs
    Native._Pyceler_Dispatch_Stats(True, True)
    Native.abs = lambda Value: Value
    Observe(Native.Direct_Absolute, Arguments('Direct_Absolute', 31))
    del Native.abs
    assert any('Callable' in Reason or 'Source_Globals' in Reason for Counts in Native._Pyceler_Guard_Stats().values() for Reason in Counts), Native._Pyceler_Guard_Stats()
    Path(sys.argv[3]).write_text(json.dumps(Report, indent=2), encoding='utf-8')
    print(json.dumps({Name: Value for Name, Value in Report.items() if Name != 'Cases'}), flush=True)

if __name__ == '__main__':
    Main()
