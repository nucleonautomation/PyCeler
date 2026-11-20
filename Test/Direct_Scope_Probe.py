import importlib.util
import json
import sys

# Compare exception names/messages and intermediate state, not merely successful compilation.
def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Observe(Function, *Args):
    try:
        return 'value', Function(*Args)
    except Exception as Error:
        return 'error', type(Error).__name__, Error.args, getattr(Error, 'name', None)

def _Run(Module):
    Rows = []
    Read, Set, Delete, Increase = Module.Factory(3)
    for Function, Args in ((Read, ()), (Delete, ()), (Increase, (2,)), (Set, (10,)), (Read, ()), (Increase, (4,)), (Read, ()), (Delete, ()), (Read, ()), (Set, (None,)), (Read, ())):
        Rows.append(_Observe(Function, *Args))
    Rows.extend(_Observe(Function) for Function in (Module.Local_Delete, Module.Before_Binding))
    Rows.extend(_Observe(Module.Dead_Binding, Flag) for Flag in (True, False))
    Events = []
    Rows.append(_Observe(Module.Partial_Delete(Events)))
    Rows.append(Events)
    Inner, Read = Module.Outer_Shadow()
    Rows.extend((_Observe(Inner), _Observe(Read), _Observe(Module.Defaults()), _Observe(Module.Box().Factory())))
    Rows.extend((_Observe(Module.Late_Global), Module.Published_Result, _Observe(Module.Global_Builtin), Module.min))
    # Replacing builtins after import must be observed even when no source assignment declares the name.
    Rows.append(_Observe(Module.Read_Builtins, [3, 1]))
    Module.sum = lambda Values: ('replacement', list(Values))
    Module.enumerate = lambda Values: [(99, Values[0])]
    Rows.append(_Observe(Module.Read_Builtins, [3, 1]))
    del Module.sum, Module.enumerate
    return Rows

def Main():
    Reference = _Load('Reference', sys.argv[1])
    Native = _Load('Direct_Scope_Cases', sys.argv[2])
    Expected, Actual = _Run(Reference), _Run(Native)
    assert Expected == Actual, [(Position, Left, Right) for Position, (Left, Right) in enumerate(zip(Expected, Actual)) if Left != Right]
    print(json.dumps(dict(Comparisons=len(Expected), Exact=True)), flush=True)

if __name__ == '__main__':
    Main()
