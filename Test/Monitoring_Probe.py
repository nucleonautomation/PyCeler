import importlib.util
import json
import sys
import types
# Isolated verification for monitoring.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Count(Module):
    return sum(Value()['Native_Elements'] for Key, Value in vars(Module).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))

def Main():
    Reference, Native = Load(sys.argv[1], 'Reference'), Load(sys.argv[2], 'Monitoring_Cases')
    Size, Records = 64, []
    for Name in ('Apply', 'Inline'):
        Before = Count(Native)
        assert getattr(Native, Name)([0.25] * Size, [0.0] * Size) == getattr(Reference, Name)([0.25] * Size, [0.0] * Size)
        assert Count(Native) > Before, Name
    if not hasattr(sys, 'monitoring'):
        print(json.dumps(dict(Native=2, Monitoring='unavailable')))
        return
    Monitor = sys.monitoring
    Tool = next(Value for Value in range(6) if Monitor.get_tool(Value) is None)
    Monitor.use_tool_id(Tool, 'PyCeler regression')
    Calls = []
    def Callback(Code, Offset):
        if Code.co_name in ('Transform', 'Apply', 'Inline'):
            Calls.append(Code.co_name)
    Event = Monitor.events.PY_START
    Monitor.register_callback(Tool, Event, Callback)
    try:
        for Name, Mode in (('Apply', 'global'), ('Apply', 'helper'), ('Apply', 'caller'), ('Inline', 'caller')):
            Codes = [getattr(Module, 'Transform' if Mode == 'helper' else Name).__code__ for Module in (Reference, Native)]
            if Mode == 'global':
                Monitor.set_events(Tool, Event)
            else:
                for Code in Codes:
                    Monitor.set_local_events(Tool, Code, Event)
            Calls.clear()
            Expected = getattr(Reference, Name)([0.25] * Size, [0.0] * Size)
            Expected_Calls = Calls[:]
            Calls.clear()
            Before = Count(Native)
            Actual = getattr(Native, Name)([0.25] * Size, [0.0] * Size)
            assert Actual == Expected, (Name, Mode)
            assert Calls == Expected_Calls, (Name, Mode, len(Calls), len(Expected_Calls))
            assert Count(Native) == Before, (Name, Mode, Count(Native) - Before)
            if Mode in ('global', 'helper'):
                assert Calls.count('Transform') == Size, (Mode, Calls)
            Records.append(dict(Function=Name, Mode=Mode, Calls=len(Calls), Native=0))
            Monitor.set_events(Tool, 0)
            for Code in Codes:
                Monitor.set_local_events(Tool, Code, 0)
    finally:
        Monitor.set_events(Tool, 0)
        for Module in (Reference, Native):
            for Name in ('Transform', 'Apply', 'Inline'):
                Monitor.set_local_events(Tool, getattr(Module, Name).__code__, 0)
        Monitor.register_callback(Tool, Event, None)
        Monitor.free_tool_id(Tool)
    Invoked = []
    def Unexpected(*Arguments):
        Invoked.append(Arguments)
        raise AssertionError('replacement getter must not run')
    for Owner, Name, Value in ((Monitor, 'get_events', Unexpected), (Monitor, 'get_local_events', Unexpected), (sys, '_getframe', Unexpected), (sys, 'monitoring', types.ModuleType('replacement'))):
        Saved = getattr(Owner, Name)
        try:
            setattr(Owner, Name, Value)
            Before = Count(Native)
            assert Native.Apply([0.25] * Size, [0.0] * Size) == Reference.Apply([0.25] * Size, [0.0] * Size)
            assert Count(Native) == Before, Name
            assert not Invoked, (Name, Invoked)
        finally:
            setattr(Owner, Name, Saved)
    Before = Count(Native)
    Native.Apply([0.25] * Size, [0.0] * Size)
    assert Count(Native) > Before
    print(json.dumps(dict(Native=3, Monitoring=Records, Replacement_Guards=4)))

if __name__ == '__main__':
    Main()
