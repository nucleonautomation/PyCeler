import importlib.util
import sys
# Isolated verification for list storage and publication semantics.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], 'List_Runtime_Cases')
    Size = 131080
    Source = [1.25] * Size
    Before = sys.getrefcount(Source), sys.getrefcount(Source[0])
    Expected = Reference.Shared(Source, [None] * Size, [None] * Size, Size)
    Native._Pyceler_Dispatch_Stats(True, True)
    Actual = Native.Shared(Source, [None] * Size, [None] * Size, Size)
    assert Expected == Actual
    assert all(Left is Right for Left, Right in zip(*Actual))
    assert len({id(Value) for Value in Actual[0]}) == Size
    Execution = Native._Pyceler_Dispatch_Stats().get('Execution', {})
    assert Execution.get('Native_Entry') and Execution.get('Actual_Team', 0) > 1, Execution
    for Run in range(12):
        Values = [0.0] * Size
        Actual = Native.Nested(Source, Values, Size)
        assert Actual is Values
        assert Actual == Reference.Nested(Source, [0.0] * Size, Size)
    assert Before == (sys.getrefcount(Source), sys.getrefcount(Source[0]))
    Cases = [('Divide', Failure, (Size,), Failure > 0) for Failure in (0, 65535, 65536, Size - 1)]
    Cases.extend(('Divide_Stepped', Failure, (Size - 1, -1, -2), True) for Failure in (65535, 65537, 1))
    for Name, Failure, Tail, Required in Cases:
        Values = [1.25] * Size
        Values[Failure] = 0.0
        Outputs = []
        for Module in (Reference, Native):
            if Module is Native:
                Native._Pyceler_Dispatch_Stats(True, True)
                Before_Native = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
            Output = [None] * Size
            try:
                getattr(Module, Name)(Values, Output, *Tail)
            except ZeroDivisionError as Error:
                Outputs.append((Output, str(Error)))
            else:
                raise AssertionError('The division error disappeared')
            if Module is Native:
                Report = Native._Pyceler_Dispatch_Stats()
                Execution = Report.get('Execution', {})
                Native_Entries = Report.get('Totals', {}).get('Native_Entries', 0)
                After_Native = sum(Value()['Native_Elements'] for Key, Value in vars(Native).items() if Key.startswith('_Pyceler_Fast_') and Key.endswith('Stats'))
                assert bool(Native_Entries) is Required, (Name, Failure, Report)
                assert (After_Native > Before_Native) is Required, (Name, Failure, Report)
                assert Execution.get('Native_Entry') is False, (Name, Failure, Report)
        assert Outputs[0] == Outputs[1], Failure
    print('List runtime: large shared identities, repeated reference lifetimes, nested spans and seven forward/reverse partial errors passed', flush=True)

if __name__ == '__main__':
    Main()
