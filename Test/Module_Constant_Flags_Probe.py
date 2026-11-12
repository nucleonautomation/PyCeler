import builtins
import importlib.util
import json
import sys
from pathlib import Path

def _Load(Name, File):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Run():
    Original = _Load("Reference_Module_Flags", sys.argv[2])
    Native = _Load(Path(sys.argv[1]).name.split(".")[0], sys.argv[1])
    for Module in (Original, Native):
        Module.Clear = lambda: Native._Test_Floating_Status(True)
        Module.Status = Native._Test_Floating_Status
    Statistics = next(Value for Name, Value in vars(Native).items() if Name.startswith("_Pyceler_") and Name.endswith("Module_Stats") and callable(Value))
    Comparisons = 0
    Original_Compile = builtins.compile
    def Forbidden_Compile(*Arguments, **Keywords):
        raise AssertionError("A prepared module loop compiled source during execution")
    for Round in (False, True):
        Previous = Native._Test_Rounding(Round)
        try:
            for Repeat in range(2):
                for Size in (0, 1, 9, 64):
                    Expected = Original.Run(Size)
                    Before = Statistics()
                    builtins.compile = Forbidden_Compile
                    try:
                        Actual = Native.Run(Size)
                    finally:
                        builtins.compile = Original_Compile
                    After = Statistics()
                    assert Expected == Actual, (Size, Round, Repeat, Expected, Actual)
                    assert all(all(Event[1:]) for Event in Actual[1]), Actual
                    assert Actual[2] == 0 and all(Event[0] == 0 for Event in Actual[1]), Actual
                    assert After["Fallbacks"] == Before["Fallbacks"], (Before, After)
                    assert (After["Native"] > Before["Native"]) == (Size > 0), (Size, Before, After)
                    Comparisons += 1
        finally:
            Native._Test_Restore_Rounding(Previous)
    print(json.dumps(dict(Comparisons=Comparisons, Exact_Values=True, Caller_Flags=True, Literal_Identity=True, No_Runtime_Compilation=True)))

if __name__ == "__main__":
    _Run()
