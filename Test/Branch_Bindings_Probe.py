import importlib.util
import json
import sys
from pathlib import Path
import numpy as N

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Observe(Module, Name, Flag, Other, Kind, Size, Failure=None):
    Events = []
    class Truth:
        def __init__(self, Name, Value):
            self.Name, self.Value = Name, Value
        def __bool__(self):
            Events.append(("truth", self.Name, self.Value))
            return self.Value
    First = (N.arange(Size, dtype=N.int32) % 17).copy()
    Second = First + 7
    Output = N.full(Size, -19, dtype=N.int32)
    if Kind == "readonly_input":
        First.flags.writeable = Second.flags.writeable = False
    elif Kind == "lists":
        First, Second = First.tolist(), Second.tolist()
    elif Kind == "alias":
        Storage = N.arange(Size + 1, dtype=N.int32) % 17
        Selected_First = Flag == Other if Name == "Nested" else Flag
        if Selected_First:
            First = Storage[:-1]
        else:
            Second = Storage[:-1]
        Output = Storage[1:]
    elif Kind == "strided":
        First = N.repeat(First, 2)[::2]
        Second = N.repeat(Second, 2)[::2]
    elif Kind == "readonly_output":
        Output.flags.writeable = False
    def Callback(Source, Target, Trace):
        Phase = Trace[-1]
        Trace.append(("callback", Phase, len(Source), len(Target)))
        if Phase == Failure:
            raise LookupError("callback " + Phase)
    Function = Module.Processor().Choose if Name == "Processor.Choose" else getattr(Module, Name)
    try:
        Result = Function(Truth("flag", Flag), Truth("other", Other), First, Second, Output, Events, Callback)
        Outcome = ("return", Result is Output)
    except Exception as Error:
        Outcome = ("error", type(Error).__name__, str(Error))
    return Outcome, Output.dtype.str, Output.tobytes().hex(), Events

def _Run():
    Native = _Load("Branch_Bindings", Path(sys.argv[1]))
    Original = _Load("Reference_Branch_Bindings", Path(sys.argv[2]))
    Parallel = sys.argv[3] == "parallel"
    Stats = next(Value for Name, Value in vars(Native).items() if Name.startswith("_Pyceler_") and Name.endswith("Dispatch_Stats"))
    Checks, Entries = 0, 0
    for Name in ("Choose", "Nested", "Annotated", "Processor.Choose"):
        for Flag in (False, True):
            for Other in (False, True):
                for Kind in ("plain", "readonly_input", "lists", "alias", "strided", "readonly_output"):
                    Args = Name, Flag, Other, Kind, 32768
                    Expected = _Observe(Original, *Args)
                    Stats(True, Reset=True)
                    Actual = _Observe(Native, *Args)
                    Execution = Stats(False).get("Execution", {})
                    assert Actual == Expected, (Args, Actual, Expected)
                    if Kind in ("plain", "readonly_input"):
                        assert Execution.get("Native_Entry") is True, (Args, Execution)
                        assert Execution.get("Actual_Team") == (2 if Parallel else 1), (Args, Execution)
                        Entries += 1
                    else:
                        assert Execution.get("Native_Entry") is not True, (Args, Execution)
                    Checks += 1
                for Size, Failure in ((0, None), (11, "before"), (11, "after")):
                    Args = Name, Flag, Other, "lists", Size, Failure
                    assert _Observe(Native, *Args) == _Observe(Original, *Args), Args
                    Checks += 1
    for Name in ("Partial", "Annotation_Only", "Walrus_Only", "Returning_Branch"):
        for Flag in (False, True):
            for Size in (0, 7):
                Args = Name, Flag, False, "plain", Size
                Expected = _Observe(Original, *Args)
                Stats(True, Reset=True)
                assert _Observe(Native, *Args) == Expected, Args
                assert not Stats(False).get("Execution", {}).get("Native_Entry"), Args
                Checks += 1
    print(json.dumps(dict(Comparisons=Checks, Native_Entries=Entries, Actual_Team=2 if Parallel else 1)))

if __name__ == "__main__":
    _Run()
