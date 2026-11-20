import importlib.util
import json
import math
import sys
from pathlib import Path
import numpy as Numpy
# Isolated verification for closures, class-private names and lexical scope.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from Array_Region_Probe import Observe, _Copy

def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def Main():
    Reference = Load(sys.argv[1], 'Reference')
    Native = Load(sys.argv[2], 'Nested_Scope_Cases')
    Selection = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else None
    Large = 65536 if Selection else 4096
    Comparisons, Entered = 0, 0
    def Check(Left, Right, Args, Required):
        nonlocal Comparisons, Entered
        Native._Pyceler_Dispatch_Stats(True, True)
        Expected = Observe(Left, _Copy(Args))
        Actual = Observe(Right, _Copy(Args))
        assert Expected == Actual, (Left.__qualname__, Expected[1:], Actual[1:])
        Execution = Native._Pyceler_Dispatch_Stats().get('Execution', {})
        if Required is True and Selection:
            Name = Left.__qualname__.replace('.<locals>', '')
            Item = next(Item for Item in Selection['Items'] if Item['Function'] == Name)
            Key = 'int' if Item['Kind'] in ('numeric_region', 'array_region') else next((Value.dtype.str for Value in Args if type(Value) is Numpy.ndarray), 'list_float')
            Bands = Item['Dispatch'].get(Key, ())
            Mode = next((Mode for Low, Mode in Bands if Large >= Low), 0)
            Required = True if Mode else None
        if Required is True:
            assert Execution.get('Native_Entry'), (Left.__qualname__, Execution, Native._Pyceler_Guard_Stats())
        elif Required is None:
            assert not Execution.get('Native_Entry'), (Left.__qualname__, Execution)
        Comparisons += 1
        Entered += bool(Execution.get('Native_Entry'))
    for Kind in (float, Numpy.float32, Numpy.float64):
        for Size in (0, 1, 31, Large):
            Source = [Index * 0.001 for Index in range(Size)]
            Output = [0.0] * Size
            if Kind is not float:
                Source, Output = Numpy.array(Source, dtype=Kind), Numpy.array(Output, dtype=Kind)
            Factory = 'List_Factory' if Kind is float else 'Array_Factory'
            Check(getattr(Reference, Factory)(), getattr(Native, Factory)(), (Source, Output, 2, Size), Size == Large)
            Factory = 'Captured_List' if Kind is float else 'Captured_Array'
            Left, Change_Left = getattr(Reference, Factory)(_Copy(Source), 2)
            Right, Change_Right = getattr(Native, Factory)(_Copy(Source), 2)
            Args = (Output, Size) if Kind is float else (Output,)
            Check(Left, Right, Args, Size == Large)
            Change_Left(3, math.sin)
            Change_Right(3, math.sin)
            Check(Left, Right, Args, Size == Large)
            Operation = lambda Value: Value * 0.25
            Change_Left(4, Operation)
            Change_Right(4, Operation)
            Check(Left, Right, Args, None)
    Values = [Index * 0.125 for Index in range(Large)]
    Output = [0.0] * len(Values)
    Operation = lambda Value: Value + 1.0
    Check(Reference.Shadowed_Builtin(Operation), Native.Shadowed_Builtin(Operation), (Values, Output, len(Values)), None)
    Check(Reference.Nonlocal_Counter(), Native.Nonlocal_Counter(), (Values, Output, len(Values)), None)
    for Size in (0, 1, 31):
        Args = (Values[:Size], Output[:Size], Size)
        Check(Reference.Unbound_Capture(), Native.Unbound_Capture(), Args, None)
        Check(Reference.Shadowed_Local(2), Native.Shadowed_Local(2), Args, None)
        Check(Reference.Captured_Length(), Native.Captured_Length(), Args, None)
        Check(Reference.Unbound_Math, Native.Unbound_Math, Args, None)
        Arrays = tuple(Numpy.array(Value) for Value in Args[:2])
        Check(Reference.Array_Shadowed_Local, Native.Array_Shadowed_Local, Arrays, None)
    Check(Reference.Unused_Length, Native.Unused_Length, (Values, Output, len(Values)), True)
    Check(Reference.Lambda_Default_Shadow(), Native.Lambda_Default_Shadow(), (Values, Output, len(Values)), None)
    Check(Reference.Function_Default_Shadow(), Native.Function_Default_Shadow(), (Values, Output, len(Values)), None)
    Check(Reference.Private().Kernel, Native.Private().Kernel, (Values, Output, len(Values)), True)
    print('Nested scopes:', Comparisons, 'exact comparisons;', Entered, 'native calls;', 'measured policy verified' if Selection else 'raw native capability verified', flush=True)

if __name__ == '__main__':
    Main()
