import importlib.util
import json
import sys
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Graph(Values):
    Nodes = []
    Descriptions = []
    def _Visit(Value):
        Number = len(Nodes)
        Aliases = tuple(Index for Index, Previous in enumerate(Nodes) if Value is Previous)
        Nodes.append(Value)
        Kind = type(Value).__name__
        if type(Value) in (tuple, list):
            Descriptions.append((Kind, len(Value), Aliases))
            for Child in Value:
                _Visit(Child)
        else:
            Descriptions.append((Kind, Value.hex() if type(Value) is float else Value, Aliases))
        return Number
    for Value in Values:
        _Visit(Value)
    return Descriptions

def _Outcome(Function, Inputs, Callback):
    Args = (*Inputs, []) if Callback else Inputs
    try:
        Result = Function(*Args)
    except Exception as Error:
        return "error", type(Error).__name__, Error.args, _Graph(Args)
    return "value", _Graph((*Args, Result))

def _Run():
    Source, Binary = map(Path, sys.argv[1:3])
    Original = _Load("Original_Generated", Source)
    Native = _Load(Binary.stem.split(".", 1)[0], Binary)
    Names = sorted(Name for Name in vars(Original) if Name.startswith(("Sum_", "Ordered_", "Aliases_", "Callback_")))
    Values = (int("1000"), int("-1000"), 0, 1, -1, 2**63 - 1, -(2**63), 2**80)
    Cases = [(Count, Value, Divisor) for Count in (-2, 0, 1, 7, 19, 301) for Value in Values for Divisor in (0, 1, -7, 2**50)]
    Checks = 0
    for Name in Names:
        for Inputs in Cases:
            Expected = _Outcome(getattr(Original, Name), Inputs, Name.startswith("Callback_"))
            Actual = _Outcome(getattr(Native, Name), Inputs, Name.startswith("Callback_"))
            if Actual != Expected:
                raise AssertionError((Name, Inputs, Expected, Actual))
            Checks += 1
    Original.range = Native.range = lambda *Args: [2, 7, -3]
    for Name in Names:
        Inputs = (7, int("1000"), 2**50)
        Expected = _Outcome(getattr(Original, Name), Inputs, Name.startswith("Callback_"))
        Actual = _Outcome(getattr(Native, Name), Inputs, Name.startswith("Callback_"))
        if Actual != Expected:
            raise AssertionError((Name, "custom range", Expected, Actual))
        Checks += 1
    print(json.dumps(dict(Generated_Programs=len(Names), Differential_Cases=Checks, Exact_Values_Types_Aliases_Exceptions_And_Callbacks=True)))

if __name__ == "__main__":
    _Run()
