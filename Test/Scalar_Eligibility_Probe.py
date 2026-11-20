import importlib.util
import json
import sys
from pathlib import Path
# Isolated verification for integer operators, freshness and native admission.
def _Load(File, Name):
    Spec = importlib.util.spec_from_file_location(Name, File)
    Module = importlib.util.module_from_spec(Spec)
    Spec.loader.exec_module(Module)
    return Module

def _Observe(Function, Arguments):
    try:
        Value = Function(*Arguments)
    except Exception as Error:
        return "error", type(Error).__name__, str(Error)
    Leaves = []
    def _Visit(Value):
        if type(Value) in (tuple, list):
            return type(Value).__name__, tuple(_Visit(Item) for Item in Value)
        Leaves.append(Value)
        return type(Value).__name__, Value
    Shape = _Visit(Value)
    Objects = Leaves + list(Arguments)
    Identity = tuple(Left is Right for Left in Objects for Right in Objects)
    return "value", Shape, Identity

def Main():
    Source, Binary, Destination = map(Path, sys.argv[1:4])
    Original, Native = _Load(Source, "Original"), _Load(Binary, Binary.stem)
    assert Original.Module_Results == Native.Module_Results
    Module_Stats = Native._Pyceler_Module_Stats()
    assert Module_Stats["Native"] == 40 and Module_Stats["Fallbacks"] == 0, Module_Stats
    Cases = [(17, 19, 2), (17, -(2**40), 1), (0, 2**70, 2), (1, -(2**63), 0), (5, 2**63 - 1, 2), (4, 2**70, 2), (3, 11, -1), (3, 11, 0), (2, True, 1), (3, 5.5, 2), (2, 17, 64)]
    Names = sorted(Name for Name in vars(Original) if Name.startswith("Compute_"))
    Comparisons, Native_Cases = 0, 0
    for Name in Names:
        for Position, Arguments in enumerate(Cases):
            Before = Native._Pyceler_Region_Stats()
            Native._Pyceler_Dispatch_Stats(True, Reset=True)
            Expected = _Observe(getattr(Original, Name), Arguments)
            Actual = _Observe(getattr(Native, Name), Arguments)
            assert Actual == Expected, (Name, Arguments, Actual, Expected)
            After = Native._Pyceler_Region_Stats()
            if Position in (0, 1):
                if "_Whole_" in Name:
                    Observation = Native._Pyceler_Dispatch_Stats()["Execution"]
                    assert Observation.get("Native_Entry"), (Name, Observation)
                else:
                    assert After[0] > Before[0] and After[1] == Before[1], (Name, Before, After)
                Native_Cases += 1
            Comparisons += 1
    Report = dict(Functions=len(Names), Comparisons=Comparisons, Positive_Native_Cases=Native_Cases, Module_Statistics=Module_Stats)
    Destination.write_text(json.dumps(Report, indent=2), encoding="utf-8")
    print(json.dumps(Report), flush=True)

if __name__ == "__main__":
    Main()
