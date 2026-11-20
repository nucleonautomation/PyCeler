import importlib.util
import json
import sys
from pathlib import Path
# Isolated verification for scalar data flow and equivalent source rewrites.
def Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    sys.modules[Name] = Module
    Spec.loader.exec_module(Module)
    return Module

def Observe(Function, Arguments):
    try:
        return ("value", Function(*Arguments))
    except Exception as Error:
        return ("error", type(Error).__name__, str(Error))

def Main():
    Source, Binary = map(Path, sys.argv[1:3])
    Original = Load(Source, "Reference")
    Native = Load(Binary, Binary.stem)
    assert Original.Module_Results == Native.Module_Results
    Module_Stats = Native._Pyceler_Module_Stats()
    assert Module_Stats["Native"] == 12 and Module_Stats["Fallbacks"] == 0, Module_Stats
    Names = sorted(Name for Name in vars(Original) if Name.startswith("Compute_"))
    Cases = [(-3, 257, 2, 7, 999983, True), (257, -3, -3, 7, -999983, False), (0, 0, 1, 17, 999983, True), (0, 5, 1, 2**70, 999983, False), (0, 5, 1, 2**63 - 1, 999983, True), (0, 5, 1, 7, 0, False), (0, 5, 0, 7, 999983, True), (0, 5, 1, 7, 999983, False)]
    Comparisons, Entries = 0, 0
    for Name in Names:
        for Position, Arguments in enumerate(Cases):
            Before = Native._Pyceler_Region_Stats()
            Expected = Observe(getattr(Original, Name), Arguments)
            Actual = Observe(getattr(Native, Name), Arguments)
            After = Native._Pyceler_Region_Stats()
            assert Actual == Expected, (Name, Arguments, Actual, Expected)
            if Position in (0, 1, 7):
                assert After[0] > Before[0] and After[1] == Before[1], (Name, Arguments, Before, After)
                Entries += After[0] - Before[0]
            Comparisons += 1
    print(json.dumps(dict(Functions=len(Names), Comparisons=Comparisons, Confirmed_Native_Entries=Entries, Module_Statistics=Module_Stats, Function_Statistics=Native._Pyceler_Region_Stats())), flush=True)

if __name__ == "__main__":
    Main()
