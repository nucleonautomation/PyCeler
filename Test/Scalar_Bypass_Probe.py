import importlib.util
import json
import sys
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Hook(Module, Suffix):
    return next((Value for Name, Value in vars(Module).items() if Name.startswith('_Pyceler_') and Name.endswith(Suffix) and callable(Value)), None)

def _Call(Module, Size, Step, Failure=None, Header=False, Shadow=False):
    Events = []
    Statistics, Dispatch = _Hook(Module, 'Region_Stats'), _Hook(Module, 'Dispatch_Stats')
    Before = Statistics() if Statistics is not None else (0, 0)
    if Dispatch is not None:
        Dispatch(True, Reset=True)
    def Callback(Index, Total, Stride):
        Events.append(('callback', Index, Total, Stride))
        Module.range = lambda *Arguments: (_ for _ in ()).throw(AssertionError('range was evaluated again'))
        if Failure == 'raise':
            raise RuntimeError('controlled callback failure')
        if Failure == 'unpack':
            return (Total,)
        return Total + 1, 'bad' if Failure == 'stride' else -Stride
    class Header_Value:
        def __init__(self, Value, Name):
            self.Value, self.Name = Value, Name
        def __index__(self):
            Events.append(('index', self.Name, self.Value))
            return self.Value
    if Shadow:
        def Custom_Range(*Arguments):
            Events.append(('custom range', Arguments))
            return [0, 3, 6]
        Module.range = Custom_Range
    Arguments = [0, Size * Step, Step]
    if Header:
        Arguments[:2] = [Header_Value(Value, Name) for Value, Name in zip(Arguments[:2], ('begin', 'end'))]
    try:
        Outcome = ('return', Module.Mixed(*Arguments, 17, Events, Callback))
    except Exception as Error:
        Outcome = ('raise', type(Error).__name__, Error.args)
    finally:
        vars(Module).pop('range', None)
    After = Statistics() if Statistics is not None else Before
    Execution = Dispatch() if Dispatch is not None else {}
    if Dispatch is not None:
        Dispatch(False)
    return (Outcome, Events), (After[0] - Before[0], After[1] - Before[1]), Execution

def _Expected(Size, Step):
    if Size < 256:
        return 0, 0, False
    Spans, Pending = [], 0
    for Index in range(0, Size * Step, Step):
        Pending += 1
        if Index % 4096 == 0:
            Spans.append(Pending)
            Pending = 0
    if Pending:
        Spans.append(Pending)
    Native = sum(Size >= 256 for Size in Spans)
    return Native, len(Spans) - Native, bool(Spans and Spans[-1] >= 256)

def _Run():
    Source, Binary = map(Path, sys.argv[1:])
    Reference = _Load('Bypass_Reference', Source)
    Native = _Load(Binary.stem.split('.')[0], Binary)
    Comparisons, Native_Calls, Bypass_Calls = 0, 0, 0
    for Step in (1, -1, 2, -3):
        for Size in (0, 1, 63, 64, 255, 256, 4096, 8193):
            Expected, Ignored, Ignored_Trace = _Call(Reference, Size, Step)
            Actual, Counters, Trace = _Call(Native, Size, Step)
            assert Actual == Expected, (Size, Step, Actual, Expected)
            Attempts, Declined, Last_Native = _Expected(Size, Step)
            assert Counters == (Attempts, Declined), (Size, Step, Counters, Attempts, Declined)
            if Size < 256:
                assert Trace == {}, (Size, Step, Trace)
                Bypass_Calls += 1
            elif Last_Native:
                assert Trace['Execution'] == dict(Reason='native_serial', Actual_Team=1, Native_Entry=True), Trace
            Native_Calls += bool(Attempts)
            Comparisons += 1
        for Failure in ('raise', 'unpack', 'stride'):
            Expected, Ignored, Ignored_Trace = _Call(Reference, 64, Step, Failure=Failure)
            Actual, Counters, Trace = _Call(Native, 64, Step, Failure=Failure)
            assert Actual == Expected and Counters == (0, 0) and Trace == {}, (Step, Failure, Actual, Expected, Counters, Trace)
            Comparisons += 1
        for Size in (0, 64, 4096):
            Expected, Ignored, Ignored_Trace = _Call(Reference, Size, Step, Header=True)
            Actual, Counters, Trace = _Call(Native, Size, Step, Header=True)
            assert Actual == Expected and Counters == _Expected(Size, Step)[:2], (Step, Size, Actual, Expected, Counters)
            assert sum(Event[0] == 'index' for Event in Actual[1]) == 2
            Comparisons += 1
    for Failure in (None, 'raise', 'stride'):
        Expected, Ignored, Ignored_Trace = _Call(Reference, 64, 1, Failure=Failure, Shadow=True)
        Actual, Counters, Trace = _Call(Native, 64, 1, Failure=Failure, Shadow=True)
        assert Actual == Expected and Counters == (0, 1), (Failure, Actual, Expected, Counters)
        Comparisons += 1
    print(json.dumps(dict(Comparisons=Comparisons, Native_Calls=Native_Calls, Bypass_Calls=Bypass_Calls, Controlled_Policy=True)))

if __name__ == '__main__':
    _Run()
